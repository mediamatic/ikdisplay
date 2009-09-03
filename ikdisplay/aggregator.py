from twisted.python import log

class LoggingAggregator(object):

    def processNotification(self, notification):
        log.msg(notification)


class PubSubAggregator(object):
    pubsubService = None

    def __init__(self, service, nodeIdentifier):
        self.service = service
        self.nodeIdentifier = nodeIdentifier


    def processNotification(self, notification):
        self.pubsubService.publishNotification(self.service,
                                               self.nodeIdentifier,
                                               notification)
