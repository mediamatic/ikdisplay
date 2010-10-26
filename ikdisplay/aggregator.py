from twisted.application import service
from twisted.internet import defer
from twisted.python import log

from axiom import item, attributes

from ikdisplay.source import ISource

class Feed(item.Item):
    """
    A feed represents the aggregate stream of items of its sources.

    To pass notifications onto an aggregator, a Service named C{'aggregator'}
    must have been added as a subservice of the store the feed is stored in:

        >>> agg = LoggingAggregator()
        >>> agg.setName('aggregator')
        >>> agg.setServiceParent(service.IService(store))
    """

    typeName = 'Feed'

    handle = attributes.text(allowNone=False)
    title = attributes.text()
    language = attributes.text(default=u'en')

    def processNotifications(self, notifications):
        """
        Send on notifications to the aggregator.

        This finds the globally available aggregator service and passes it
        the notifications using this feed's handle.
        """
        aggregator = service.IService(self.store).getServiceNamed('aggregator')
        aggregator.processNotifications(self.handle, notifications)


    def getSources(self):
        """ The list of sources for this feed. """
        return list(self.powerupsFor(ISource))


    def getURI(self):
        return "xmpp:feeds.mediamatic.nl?node=" + self.handle



class LoggingAggregator(service.Service):

    def processNotifications(self, feed, notifications):
        for notification in notifications:
            log.msg("%s: %s" % (feed, notification))



class PubSubAggregator(service.Service):
    pubsubService = None

    def __init__(self, service):
        service.Service.__init__(self)
        self.service = service


    def processNotifications(self, feed, notifications):
        self.pubsubHandler.publishNotifications(self.service, feed,
                                                notifications)



class AggregatorFromNotifier(service.Service):

    maxHistory = 13

    def __init__(self, notifier):
        self.notifier = notifier
        self.history = []


    def processNotifications(self, feed, notifications):
        map(self.notifier.notify, notifications)
        self.history.extend(notifications)
        self.history = self.history[-self.maxHistory:]


    def getHistory(self):
        return defer.succeed(self.history)
