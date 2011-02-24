import re
import simplejson as json

from twisted.application import service
from twisted.internet import defer, error, reactor
from twisted.python import log
from twisted.web import client
from twisted.web import error as http_error
from twisted.words.xish import domish

from wokkel import pubsub

from twittytwister import streaming, twitter

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



class TwitterMonitor(service.Service):
    """
    Reconnecting Twitter monitor service.

    @ivar terms: Terms to track as an iterable of C{unicode}.
    @ivar userIDs: IDs of users to follow as an iterable of C{unicode}.
    """

    initialDelay = 5
    delay = 5
    maxDelay = 5
    continueTrying = True
    errorState = None
    consumer = None
    protocol = None

    terms = None
    userIDs = None

    def __init__(self, username, password, consumer=None):
        self.controller = twitter.TwitterFeed(username, password)
        self.controller.protocol = VerboseTwitterStream
        self.consumer = consumer


    def startService(self):
        service.Service.startService(self)
        self.continueTrying = True
        self.doConnect()


    def stopService(self):
        service.Service.stopService(self)
        self.continueTrying = False

        if self.protocol:
            self.protocol.transport.stopProducing()


    def doConnect(self):

        def forgetProtocol(result):
            self.protocol = None
            return result

        def connectionClosed(_):
            log.msg("Connection closed cleanly.")
            self.errorState = None
            self.delay = self.initialDelay

        def cb(protocol):
            self.protocol = protocol
            protocol.deferred.addBoth(forgetProtocol)
            protocol.deferred.addCallback(connectionClosed)
            return protocol.deferred

        def trapConnectError(failure):
            failure.trap(error.ConnectError,
                         error.TimeoutError,
                         error.ConnectionClosed)
            log.err(failure)
            if self.errorState != 'connect':
                self.errorState = 'connect'
                self.delay = 0.25
                self.maxDelay = 16
            else:
                self.delay = min(self.maxDelay, self.delay * 2)


        def trapHTTPError(failure):
            failure.trap(http_error.Error)
            log.err(failure, "HTTP error")

            if self.errorState != 'http':
                self.errorState = 'http'
                self.delay = 10
                self.maxDelay = 240
            else:
                self.delay = min(self.maxDelay, self.delay * 2)

        def trapOtherErrors(failure):
            log.err(failure)
            self.errorState = 'other'
            self.continueTrying = False

        def retry(_):
            if self.continueTrying:
                if self.delay == 0:
                    when = "now"
                else:
                    when = "in %0.2f seconds" % (self.delay,)
                log.msg("Reconnecting %s." % (when,))
                reactor.callLater(self.delay, self.doConnect)
            else:
                log.msg("Abandoning reconnect.")

        if not self.terms and not self.userIDs:
            log.msg("No Twitter terms or users to filter on. Not connecting.")
            return False

        self.continueTrying = True

        args = {}
        if self.terms:
            args['track'] = ','.join(self.terms)
        if self.userIDs:
            args['follow'] = ','.join(self.userIDs)

        if self.consumer is None:
            log.msg("No Twitter consumer set. Not connecting.")
            return False

        d = self.controller.filter(self.onEntry, args)
        d.addCallback(cb)
        d.addErrback(trapConnectError)
        d.addErrback(trapHTTPError)
        d.addErrback(trapOtherErrors)
        d.addCallback(retry)

        return True


    def onEntry(self, entry):
        entry.image_url = None

        fulltweet = entry.raw
        if 'entities' not in fulltweet or 'urls' not in fulltweet['entities'] or not fulltweet['entities']['urls']:
            # No urls in tweet.
            self.consumer.onEntry(entry)
            return

        ds = []
        for urlentry in fulltweet['entities']['urls']:
            ds.append(extractImage(urlentry["url"]))
        d = defer.DeferredList(ds)
        def getFirstImage(r):
            image = None
            for success, result in r:
                if success and result:
                    image = result
                    break
            entry.image_url = image
            return entry
        d.addCallback(getFirstImage)
        d.addCallback(lambda e: self.consumer.onEntry(e))


    def setFilters(self, terms, userIDs):
        """
        Set the terms to track and users to follow and (re)connect.

        @param terms: Terms to track as an iterable of C{unicode}.
        @param userIDs: IDs of users to follow as an iterable of C{unicode}.
        """
        self.terms = terms
        self.userIDs = userIDs

        if self.protocol:
            # If connected, lose connection to automatically reconnect.
            self.protocol.transport.stopProducing()
        elif self.running and self.controller:
            # Start connecting.
            self.doConnect()



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

    def __init__(self, store, monitor):
        self.store = store
        self.monitor = monitor
        self.refreshFilters()


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


    def refreshFilters(self):
        self.monitor.setFilters(*self.collectFilters())


    def onEntry(self, entry):
        for source in self._getEnabledSources():
            source.onEntry(entry)



def extractImage(url):
    extracters = [
        # native
        ('http://twitpic\.com/.+', _extractTwitpic),
        ('http://moby\.to/.+', _extractMobyPicture),
        ('http://www\.mobypicture\.com/user/[^/]+/view/.+', _extractMobyPicture),
        ('http://yfrog\.com/.+', _extractYFrog),
        ('http://www\.flickr\.com/photos/.+', _extractFlickr),

        # literal links
        ('http://i\d+\.tinypic\.com/.+\.(png|jpg)$', _extractLiteral),


        # using embed.ly oembed proxy:
        ('http://tweetphoto\.com/.+', _extractEmbedly),
        ('http://twitgoo\.com/.+', _extractEmbedly),
        ('http://pikchur\.com/.+', _extractEmbedly),
        ('http://imgur\.com/.+', _extractEmbedly),
        ('http://post\.ly/.+', _extractEmbedly),
        ('http://img\.ly/.+', _extractEmbedly),
        ('http://plixi\.com/.+', _extractEmbedly),
        ]
    for regex, cb in extracters:
        if re.match(regex, url):
            return cb(url)
    return defer.succeed(None)


def _extractLiteral(url):
    return defer.succeed(url)


def _extractTwitpic(url):
    id = url.split("/")[-1]
    return defer.succeed("http://twitpic.com/show/large/" + id)


def _extractYFrog(url):
    return _oEmbed("http://www.yfrog.com/api/oembed?url="+url)


def _extractMobyPicture(url):
    return _oEmbed("http://api.mobypicture.com/oEmbed?url=%s&format=json" % url)


def _extractFlickr(url):
    return _oEmbed("http://www.flickr.com/services/oembed/?url=%s&format=json" % url)


def _extractEmbedly(url):
    return _oEmbed("http://api.embed.ly/1/oembed?url="+url)


def _oEmbed(url):
    d = client.getPage(url)
    def parse(page):
        result = json.loads(page)
        if result['type'] not in ('photo', 'image'): # 'image' is not according to spec, but yfrog returns it
            return None
        return result['url']
    d.addCallback(parse)
    return d
