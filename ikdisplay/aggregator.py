import copy

from twisted.application import service
from twisted.python import log

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
