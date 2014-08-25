import re
import simplejson as json

from twisted.internet import defer, reactor
from twisted.python import log
from twisted.web import client
from twisted.words.xish import domish

from wokkel import pubsub

from twittytwister import streaming

NS_TWITTER = 'http://mediamatic.nl/ns/ikdisplay/2009/twitter'

class VerboseTwitterStream(streaming.TwitterStream):
    """
    More verbose Twitter protocol.
    """

    def timeoutConnection(self):
        streaming.TwitterStream.timeoutConnection(self)
        log.msg("Twitter connection timed out.")


    def keepAliveReceived(self):
        log.msg("Twitter keep-alive")



class TwitterLogger(object):
    """
    Logging Twitter consumer.
    """

    def onEntry(self, entry):
        log.msg((u"%s: %s" % (entry.user.screen_name,
                              entry.text)).encode('utf-8'))



def propertyToDomish(prop):
    element = domish.Element((NS_TWITTER, prop.tag_name))

    for propName in prop.SIMPLE_PROPS:
        if hasattr(prop, propName):
            value = getattr(prop, propName)
            element.addElement(propName, content=value)

    for propName in prop.COMPLEX_PROPS:
        if hasattr(prop, propName):
            child = propertyToDomish(getattr(prop, propName))
            element.addChild(child)

    return element



class TwitterPubSubClient(pubsub.PubSubClient):

    def __init__(self, service, nodeIdentifier):
        self.service = service
        self.nodeIdentifier = nodeIdentifier
        self.queue = defer.DeferredQueue()
        self._initialized = False


    def connectionInitialized(self):
        pubsub.PubSubClient.connectionInitialized(self)
        self._initialized = True
        self.processQueue()


    def connectionLost(self, reason):
        self._initialized = False


    def processQueue(self):
        def publishItem(item):
            def publishFailed(failure):
                log.err(failure)
                log.msg("Requeueing")
                self.queue.put(item)

            d = self.publish(self.service, self.nodeIdentifier, [item])
            d.addErrback(publishFailed)
            return d

        if not self._initialized:
            return

        d = self.queue.get()
        d.addCallback(publishItem)
        d.addCallback(lambda _: reactor.callLater(0, self.processQueue))


    def onEntry(self, entry):
        payload = propertyToDomish(entry)
        item = pubsub.Item(entry.id, payload)
        self.queue.put(item)



class TwitterDispatcher(object):
    """
    Dispatches statuses to enabled observers.

    Observers are enabled L{TwitterSource} items. The terms to track and
    userIDs to follow are collected from the observers and their unions are
    used to pass as the filter for Twitter's Streaming API. Incoming statuses
    are passed to all observers, who can then filter out the desired statuses
    themselves.

    Call C{refreshFilters} after adding, removing, or changing observers to
    recalculate the filter and reconnect.
    """

    def __init__(self, store, monitor, embedder):
        self.store = store
        self.monitor = monitor
        self.embedder = embedder
        self.setFilters()


    def _getEnabledSources(self):
        from ikdisplay.source import TwitterSource
        return self.store.query(TwitterSource, TwitterSource.enabled==True)


    def collectFilters(self):
        terms = set()
        userIDs = set()

        for source in self._getEnabledSources():
            terms.update(source.terms)
            userIDs.update(source.userIDs)

        return terms, userIDs


    def setFilters(self):
        terms, userIDs = self.collectFilters()
        self.terms = terms
        self.userIDs = userIDs
        self.monitor.args = {}
        if self.terms:
            self.monitor.args['track'] = ','.join((term.strip('"')
                                                   for term in self.terms))
        if self.userIDs:
            self.monitor.args['follow'] = ','.join(self.userIDs)

        if self.monitor.args:
            self.monitor.delegate = self.onEntry
        else:
            self.monitor.delegate = None


    def refreshFilters(self):
        oldArgs = self.monitor.args or {}
        self.setFilters()
        if oldArgs != self.monitor.args:
            self.monitor.connect(forceReconnect=True)


    def onEntry(self, entry):
        def deliver(entry):
            for source in self._getEnabledSources():
                source.onEntry(entry)

        log.msg("Tweet by %s: %s" % (entry.user.screen_name.encode('utf-8'),
                                     entry.text.encode('utf-8')))
        d = self.embedder.augmentStatusWithImage(entry)
        d.addCallback(deliver)
        d.addErrback(log.err)



class Embedder(object):
    """
    Media embedder.

    Given a URL, try to find an associated URL for enclosed media for
    embedding in Twitter statuses.
    """

    extractors = [
        # native
        ('http://twitpic\.com/.+', 'twitpic'),
        ('http://moby\.to/.+', 'mobyPicture'),
        ('http://www\.mobypicture\.com/user/[^/]+/view/.+', 'mobyPicture'),
        ('http://www\.flickr\.com/photos/.+', 'flickr'),
        ('http://instagr.am/p/.+', 'instagram'),
        ('http://instagram.com/p/.+', 'instagram'),

        # literal links
        ('http://i\d+\.tinypic\.com/.+\.(png|jpg)$', 'literal'),

        # using embed.ly oembed proxy:
        ('http://tweetphoto\.com/.+', 'embedly'),
        ('http://twitgoo\.com/.+', 'embedly'),
        ('http://pikchur\.com/.+', 'embedly'),
        ('http://imgur\.com/.+', 'embedly'),
        ('http://post\.ly/.+', 'embedly'),
        ('http://img\.ly/.+', 'embedly'),
        ('http://plixi\.com/.+', 'embedly'),
        ('https?://path.com/p/.+', 'embedly'),
        ('http://yfrog\.com/.+', 'embedly'),
        ]

    def __init__(self, config):
        self.config = config


    def augmentStatusWithImage(self, entry):
        """
        Discover images linked from the entry and include the image's URL.

        This tries to detect images from URLs embedded in the entry and
        includes the first one in the entry's C{image_url} attribute.

        @type entry: L{streaming.Status}

        @rtype: L{defer.Deferred}
        """

        def getFirstImage(r):
            for success, result in r:
                if success and result:
                    entry.image_url = result
                    break
            return entry

        entry.image_url = None

        if hasattr(entry.entities, 'media') and entry.entities.media:
            entry.image_url = entry.entities.media[0].media_url
            return defer.succeed(entry)
        elif hasattr(entry.entities, 'urls') and entry.entities.urls:
            ds = []
            for urlentry in entry.entities.urls:
                url = getattr(urlentry, 'expanded_url', urlentry.url)
                if url:
                    if (not url.startswith('http://') and
                        not url.startswith('https://')):
                        url = 'http://' + url
                    ds.append(self.extractImage(url.encode('utf-8')))
            d = defer.DeferredList(ds)
            d.addCallback(getFirstImage)
            return d
        else:
            # No urls in tweet.
            return defer.succeed(entry)


    def extractImage(self, url):
        """
        Match the URL to extractor regexes and retrieve image URL.
        """
        for regex, name in self.extractors:
            method = getattr(self, '_extract_' + name)
            if re.match(regex, url):
                return method(url)
        return defer.succeed(None)


    def _extract_literal(self, url):
        return defer.succeed(url)


    def _extract_twitpic(self, url):
        id = url.split("/")[-1]
        return defer.succeed("http://twitpic.com/show/large/" + id)


    def _extract_mobyPicture(self, url):
        return self._oEmbed(
            "http://api.mobypicture.com/oEmbed?url=%s&format=json" % url)


    def _extract_flickr(self, url):
        return self._oEmbed(
            "http://www.flickr.com/services/oembed/?url=%s&format=json" % url)


    def _extract_embedly(self, url):
        embedlyURL = 'http://api.embed.ly/1/oembed?'
        if self.config.get('embedly-key'):
            embedlyURL += 'key=%s&' % self.config['embedly-key']
        embedlyURL += 'url=%s' % url
        return self._oEmbed(embedlyURL)


    def _extract_instagram(self, url):
        return defer.succeed(url + "media?size=l")


    def _oEmbed(self, url):
        d = client.getPage(url)
        def parse(page):
            result = json.loads(page)
            if result.get('type') != 'photo':
                # Ignore non-photos
                return None
            return result.get('url')
        d.addCallback(parse)
        d.addErrback(log.err, "Failed to retrieve %r" % url)
        return d
