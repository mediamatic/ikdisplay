import copy

from twisted.application import service
from twisted.python import log
from twisted.web import client

from axiom import item, attributes

from ikdisplay.source import ISource

class Feed(item.Item):
    """
    A feed represents the aggregate stream of items of its sources.
    """

    typeName = 'Feed'

    handle = attributes.text(allowNone=False)
    title = attributes.text()
    language = attributes.text(default=u'en')

    def processNotifications(self, notifications):
        pass

    def getSources(self):
        """ The list of sources for this feed. """
        return list(self.powerupsFor(ISource))

    def getURI(self):
        return "xmpp:feeds.mediamatic.nl?node=" + self.handle



class Site(item.Item):
    title = attributes.text()
    uri = attributes.text(allowNone=False)


    def getPubSubDomain(self):
        from urlparse import urlparse
        hostname = urlparse(self.uri).hostname
        if hostname[:4] == "www.":
            hostname = hostname[4:]
        return "pubsub." + hostname



class Thing(item.Item):
    title = attributes.text()
    uri = attributes.text(allowNone=False)


    def discoverCreate(cls, store, uri):
        """ Perform discovery on the URL to get the title, and then create a thing. """
        d = client.getPage(uri)
        def parsePage(content):
            from lxml.html.soupparser import fromstring
            tree = fromstring(content)
            h1 = tree.find(".//h1")
            title = unicode((h1 is not None and h1.text) or "?")
            slf = tree.find(".//link[@rel=\"self\"]")
            newuri = unicode((slf is not None and slf.attrib["href"]) or uri)
            return Thing(store=store, uri=newuri, title=title)
        d.addCallback(parsePage)
        return d
    discoverCreate = classmethod(discoverCreate)


    def getID(self):
        """
        Return the id of this thing.
        """
        return int(self.uri.split("/")[-1])



class BaseAggregator(service.MultiService):

    feeds = None

    def __init__(self, factory):
        service.MultiService.__init__(self)
        self.factory = factory

    def addSource(self, feed, sourceConfig):
        config = copy.copy(self.feeds[feed])
        del config['sources']

        callback = lambda notifications: \
            self.processNotifications(feed, notifications)

        config.update(sourceConfig)

        formatter = self.factory.buildFormatter(config, callback)
        formatter.setServiceParent(self)

    def startService(self):
        service.MultiService.startService(self)

        for feed, config in self.feeds.iteritems():
            for sourceConfig in config['sources']:
                self.addSource(feed, sourceConfig)



class LoggingAggregator(BaseAggregator):

    def processNotifications(self, feed, notifications):
        for notification in notifications:
            log.msg("%s: %s" % (feed, notification))


class PubSubAggregator(BaseAggregator):
    pubsubService = None

    def __init__(self, factory, service):
        BaseAggregator.__init__(self, factory)
        self.service = service


    def processNotifications(self, feed, notifications):
        self.pubsubHandler.publishNotifications(self.service, feed,
                                                notifications)
