"""
Tests for L{ikdisplay.xmpp}.
"""

from twisted.internet import defer
from twisted.trial import unittest
from twisted.words.protocols.jabber.jid import JID
from twisted.words.xish import domish, utility

from wokkel import pubsub
from ikdisplay import xmpp

class TestAggregator(object):
    """
    A notifier that stores all notification in sequence.
    """

    def __init__(self):
        self.notifications = []


    def processNotification(self, notification):
        self.notifications.append(notification)


class PubSubClientFromAggregatorTest(unittest.TestCase):

    def setUp(self):
        self.jid = JID('user@example.org/Home')
        self.serviceJID = JID('pubsub.example.org')
        self.nodeIdentifier = 'test'

        xmlstream = utility.EventDispatcher()
        self.client = xmpp.PubSubClientFromAggregator()
        self.client.parent = self
        self.client.makeConnection(xmlstream)

        payload = domish.Element(('', 'rsp'))
        payload.addElement('status', content='test')
        person = payload.addElement('person')
        person.addElement('title', content="Test User")
        item = pubsub.Item(payload=payload)
        self.event = pubsub.ItemsEvent(self.serviceJID, self.jid,
                                       self.nodeIdentifier, [item], None)


    def test_addObserver(self):
        def observer(event):
            pass

        def subscribe(service, nodeIdentifier, subscriber, options=None):
            subscribeCalled.append(None)
            return defer.succeed(None)

        subscribeCalled = []
        self.client.subscribe = subscribe
        self.client.connectionInitialized()

        self.client.addObserver(observer, self.serviceJID,
                                          self.nodeIdentifier)

        self.assertEquals(1, len(subscribeCalled))


    def test_addObserverTwice(self):
        def observer(event):
            pass

        def observer2(event):
            pass

        def subscribe(service, nodeIdentifier, subscriber, options=None):
            subscribeCalled.append(None)
            return defer.succeed(None)

        subscribeCalled = []
        self.client.subscribe = subscribe
        self.client.connectionInitialized()

        self.client.addObserver(observer, self.serviceJID,
                                          self.nodeIdentifier)
        self.assertEquals(1, len(subscribeCalled))

        self.client.addObserver(observer2, self.serviceJID,
                                          self.nodeIdentifier)
        self.assertEquals(1, len(subscribeCalled))


    def test_addObserverNotConnected(self):
        def observer(event):
            pass

        def subscribe(service, nodeIdentifier, subscriber, options=None):
            subscribeCalled.append(None)
            return defer.succeed(None)

        subscribeCalled = []
        self.client.subscribe = subscribe
        self.client.addObserver(observer, self.serviceJID,
                                          self.nodeIdentifier)

        self.assertEquals(0, len(subscribeCalled))
        self.client.connectionInitialized()
        self.assertEquals(1, len(subscribeCalled))


    def test_addObserverNotConnectedTwice(self):
        def observer(event):
            pass

        def observer2(event):
            pass

        def subscribe(service, nodeIdentifier, subscriber, options=None):
            subscribeCalled.append(None)
            return defer.succeed(None)

        subscribeCalled = []
        self.client.subscribe = subscribe
        self.client.addObserver(observer, self.serviceJID,
                                          self.nodeIdentifier)
        self.client.addObserver(observer2, self.serviceJID,
                                           self.nodeIdentifier)

        self.assertEquals(0, len(subscribeCalled))
        self.client.connectionInitialized()
        self.assertEquals(1, len(subscribeCalled))


    def test_removeObserver(self):
        def observer(event):
            pass

        def subscribe(service, nodeIdentifier, subscriber, options=None,
                               sender=None):
            subscribeCalled.append(None)
            return defer.succeed(None)

        def unsubscribe(service, nodeIdentifier, subscriber,
                                 subscriptionIdentifier=None, sender=None):
            unsubscribeCalled.append(None)
            return defer.succeed(None)

        subscribeCalled = []
        unsubscribeCalled = []
        self.client.subscribe = subscribe
        self.client.unsubscribe = unsubscribe
        self.client.connectionInitialized()

        self.client.addObserver(observer, self.serviceJID,
                                          self.nodeIdentifier)
        self.client.removeObserver(observer, self.serviceJID,
                                          self.nodeIdentifier)

        self.assertEquals(1, len(unsubscribeCalled))


    def test_removeObserverAddAgain(self):
        def observer(event):
            pass

        def subscribe(service, nodeIdentifier, subscriber, options=None,
                               sender=None):
            subscribeCalled.append(None)
            return defer.succeed(None)

        def unsubscribe(service, nodeIdentifier, subscriber,
                                 subscriptionIdentifier=None, sender=None):
            unsubscribeCalled.append(None)
            return defer.succeed(None)

        subscribeCalled = []
        unsubscribeCalled = []
        self.client.subscribe = subscribe
        self.client.unsubscribe = unsubscribe
        self.client.connectionInitialized()

        self.client.addObserver(observer, self.serviceJID,
                                          self.nodeIdentifier)
        self.client.removeObserver(observer, self.serviceJID,
                                          self.nodeIdentifier)
        self.client.addObserver(observer, self.serviceJID,
                                          self.nodeIdentifier)
        self.assertEquals(2, len(subscribeCalled))


    def test_itemsReceivedNotify(self):
        """
        Received items result in notifications being generated and notified.
        """
        self.client.itemsReceived(self.event)
        self.assertEquals(1, len(self.aggregator.notifications))
        notification = self.aggregator.notifications[-1]
        self.assertEquals(u'Test User', notification[u'title'])

    test_itemsReceivedNotify.skip = True


    def test_itemsReceivedNotifyUnknownUnsubscribe(self):
        """
        Items received from unknown nodes cause unsubscription.
        """
        unsubscribed = []

        def unsubscribe(sender, nodeIdentifier, recipient):
            unsubscribed.append(None)
        self.client.unsubscribe = unsubscribe
        self.event.nodeIdentifier = 'unknown'

        self.client.itemsReceived(self.event)
        self.assertEquals(0, len(self.aggregator.notifications))
        self.assertEquals(1, len(unsubscribed))

    test_itemsReceivedNotifyUnknownUnsubscribe.skip = True


    def test_itemsReceivedNotifyOtherResource(self):
        """
        Notifications sent to another JID are ignored.
        """
        unsubscribed = []

        def unsubscribe(sender, nodeIdentifier, recipient):
            unsubscribed.append(None)
        self.client.unsubscribe = unsubscribe
        self.event.recipient = JID('user@example.org/Other')

        self.client.itemsReceived(self.event)
        self.assertEquals(0, len(self.aggregator.notifications))
        self.assertEquals(0, len(unsubscribed))

    test_itemsReceivedNotifyOtherResource.skip = True


class TestNotifier(object):
    """
    A notifier that stores all notification in sequence.
    """

    def __init__(self):
        self.notifications = []


    def notify(self, notification):
        self.notifications.append(notification)



class PubSubClientFromNotifierTest(unittest.TestCase):
    """
    Tests for L{ikdisplay.xmpp.PubSubClientFromNotifier}.
    """

    def setUp(self):
        self.jid = JID('user@example.org/Home')
        serviceJID = JID('pubsub.example.org')
        nodeIdentifier = 'test'

        self.notifier = TestNotifier()
        self.client = xmpp.PubSubClientFromNotifier(self.notifier,
                                                    serviceJID,
                                                    nodeIdentifier)
        self.client.parent = self

        payload = domish.Element((xmpp.NS_NOTIFICATION, 'notification'))
        payload.addElement('title', content='test')
        item = pubsub.Item(payload=payload)
        self.event = pubsub.ItemsEvent(serviceJID, self.jid,
                                       nodeIdentifier, [item], None)


    def test_itemsReceivedNotify(self):
        """
        Received items result in notifications being generated and notified.
        """
        self.client.itemsReceived(self.event)
        self.assertEquals(1, len(self.notifier.notifications))
        notification = self.notifier.notifications[-1]
        self.assertEquals(u'test', notification[u'title'])


    def test_itemsReceivedNotifyUnknownUnsubscribe(self):
        """
        Items received from unknown nodes cause unsubscription.
        """
        unsubscribed = []

        def unsubscribe(sender, nodeIdentifier, recipient):
            unsubscribed.append(None)
        self.client.unsubscribe = unsubscribe
        self.event.nodeIdentifier = 'unknown'

        self.client.itemsReceived(self.event)
        self.assertEquals(0, len(self.notifier.notifications))
        self.assertEquals(1, len(unsubscribed))


    def test_itemsReceivedNotifyOtherResource(self):
        """
        Notifications sent to another JID are ignored.
        """
        unsubscribed = []

        def unsubscribe(sender, nodeIdentifier, recipient):
            unsubscribed.append(None)
        self.client.unsubscribe = unsubscribe
        self.event.recipient = JID('user@example.org/Other')

        self.client.itemsReceived(self.event)
        self.assertEquals(0, len(self.notifier.notifications))
        self.assertEquals(0, len(unsubscribed))


    def test_itemsReceivedHistory(self):
        """
        When an item has been received, it is added to the history.
        """
        self.client.itemsReceived(self.event)
        self.assertEquals(1, len(self.client.history))


    def test_itemsReceivedMaxHistory(self):
        """
        History is capped at maxHistory.
        """
        for count in xrange(0, self.client.maxHistory+1):
            self.client.itemsReceived(self.event)

        self.assertEquals(self.client.maxHistory, len(self.client.history))
