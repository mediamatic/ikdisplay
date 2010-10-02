import copy

from twisted.application import service
from twisted.python import log

from twisted.words.protocols.jabber.jid import JID

from axiom import item, attributes

from ikdisplay.source import ISource

class JIDAttribute(attributes.text):
    """
    An in-database representation of a JID.

    This translates between a L{JID} instance and its C{unicode} string
    representation.
    """

    def infilter(self, pyval, oself, store):
        if pyval is None:
            return None

        return attributes.text.infilter(self, pyval.full(), oself, store)

    def outfilter(self, dbval, oself):
        if dbval is None:
            return None

        return JID(dbval)



class PubSubSubscription(item.Item):

    service = JIDAttribute("""The entity holding the node""",
                           )
    nodeIdentifier = attributes.text("""The node identifier""",
                                     default=u'')



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


class Thing(item.Item):
    title = attributes.text()
    uri = attributes.text(allowNone=False)



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
