"""
Tests for L{ikdisplay.aggregator}.
"""

from twisted.application import service
from twisted.trial import unittest
from axiom.store import Store
from ikdisplay import aggregator

class TestAggregator(service.Service):
    """
    Aggregator for testing, saving all notifications per handle in order.

    @ivar notifications: Notifications in the order received, per handle.
    @type notifications: C{dict}
    """

    def __init__(self):
        self.notifications = {}


    def processNotifications(self, feed, notifications):
        self.notifications.setdefault(feed, []).extend(notifications)



class FeedTest(unittest.TestCase):
    """
    Tests for L{ikdisplay.Feed}.
    """

    def testProcessNotifications(self):
        """
        Set up a global aggregator and check that it gets the notification.
        """
        store = Store()
        feed = aggregator.Feed(store=store, handle=u'mediamatic',
                                            title=u'Mediamatic main feed')
        agg = TestAggregator()
        agg.setName('aggregator')
        agg.setServiceParent(service.IService(store))

        notification = {'title': u'Arjan Scherpenisse',
                        'subtitle': u'roze koeken ftw'}
        feed.processNotifications([notification])

        self.assertEquals(notification,
                          agg.notifications[u'mediamatic'][-1])
