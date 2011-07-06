"""
Tests for L{ikdisplay.xmpp}.
"""

from zope.interface import implements

from twisted.internet import defer
from twisted.trial import unittest
from twisted.words.protocols.jabber.jid import JID
from twisted.words.xish import domish, utility

from axiom import attributes, item, store

from wokkel import pubsub
from ikdisplay import source, xmpp

class GetPubSubServiceTest(unittest.TestCase):

    def test_bare(self):
        hostname = 'http://mediamatic.nl/'
        self.assertEquals(JID('pubsub.mediamatic.nl'),
                          xmpp.getPubSubService(hostname))


    def test_withWWW(self):
        hostname = 'http://www.mediamatic.nl/'
        self.assertEquals(JID('pubsub.mediamatic.nl'),
                          xmpp.getPubSubService(hostname))


    def test_mdnsLocal(self):
        hostname = 'http://dwaal.local/'
        self.assertEquals(JID('dwaal.local'),
                          xmpp.getPubSubService(hostname))


    def test_testSite(self):
        hostname = 'http://mml03.test.mediamatic.nl/'
        self.assertEquals(JID('mml03.test.mediamatic.nl'),
                          xmpp.getPubSubService(hostname))



class TestAggregator(object):
    """
    A notifier that stores all notification in sequence.
    """

    def __init__(self):
        self.notifications = []


    def processNotification(self, notification):
        self.notifications.append(notification)


class TestObserver(source.PubSubSourceMixin, item.Item):
    """
    A publish-subscribe observer that stores all events in sequence.
    """

    implements(xmpp.IPubSubEventProcessor)
    subscription = attributes.reference()
    service = attributes.inmemory()
    nodeIdentifier = attributes.inmemory()
    events = attributes.inmemory()

    def activate(self):
        self.events = []


    def itemsReceived(self, event):
        self.events.append(event)



    def getNode(self):
        return (self.service, self.nodeIdentifier)



class PubSubDispatcherTest(unittest.TestCase):

    def setUp(self):
        self.jid = JID('user@example.org/Home')
        self.serviceJID = JID('pubsub.example.org')
        self.nodeIdentifier = u'test'

        self.subscribeCalled = []
        self.unsubscribeCalled = []

        def subscribe(service, nodeIdentifier, subscriber,
                      options=None, sender=None):
            subscription = pubsub.Subscription(nodeIdentifier, subscriber,
                                               u'subscribed', options)
            self.subscribeCalled.append(None)
            return defer.succeed(subscription)

        def unsubscribe(service, nodeIdentifier, subscriber,
                        subscriptionIdentifier=None, sender=None):
            self.unsubscribeCalled.append(None)
            return defer.succeed(None)

        xmlstream = utility.EventDispatcher()
        self.store = store.Store()
        self.client = xmpp.PubSubDispatcher(self.store)
        self.client.subscribe = subscribe
        self.client.unsubscribe = unsubscribe
        self.client.parent = self
        self.client.makeConnection(xmlstream)

        self.observer = TestObserver(store=self.store,
                                     service=self.serviceJID,
                                     nodeIdentifier=self.nodeIdentifier)

        payload = domish.Element(('', 'rsp'))
        payload.addElement('status', content='test')
        person = payload.addElement('person')
        person.addElement('title', content="Test User")
        item = pubsub.Item(payload=payload)
        self.event = pubsub.ItemsEvent(self.serviceJID, self.jid,
                                       self.nodeIdentifier, [item], None)


    def test_addObserver(self):
        self.client.connectionInitialized()
        self.client.addObserver(self.observer)

        self.assertEquals(1, len(self.subscribeCalled))


    def test_addObserverTwice(self):
        observer2 = TestObserver(store=self.store,
                                 service=self.serviceJID,
                                 nodeIdentifier=self.nodeIdentifier)

        self.client.connectionInitialized()
        self.client.addObserver(self.observer)
        self.assertEquals(1, len(self.subscribeCalled))

        self.client.addObserver(observer2)
        self.assertEquals(1, len(self.subscribeCalled))


    def test_addObserverNotConnected(self):
        self.client.addObserver(self.observer)

        self.assertEquals(0, len(self.subscribeCalled))
        self.client.connectionInitialized()
        self.assertEquals(1, len(self.subscribeCalled))


    def test_addObserverNotConnectedTwice(self):
        observer2 = TestObserver(store=self.store,
                                 service=self.serviceJID,
                                 nodeIdentifier=self.nodeIdentifier)

        self.client.addObserver(self.observer)
        self.client.addObserver(observer2)

        self.assertEquals(0, len(self.subscribeCalled))
        self.client.connectionInitialized()
        self.assertEquals(1, len(self.subscribeCalled))


    def test_removeObserver(self):
        self.client.connectionInitialized()
        self.client.addObserver(self.observer)
        self.client.removeObserver(self.observer)

        self.assertEquals(1, len(self.unsubscribeCalled))


    def test_removeObserverAddAgain(self):
        self.client.connectionInitialized()
        self.client.addObserver(self.observer)
        self.client.removeObserver(self.observer)
        self.client.addObserver(self.observer)
        self.assertEquals(2, len(self.subscribeCalled))


    def test_itemsReceivedNotify(self):
        """
        Received items result in notifications being generated and notified.
        """
        self.client.addObserver(self.observer)
        self.client.itemsReceived(self.event)
        self.assertEquals(1, len(self.observer.events))


    def test_itemsReceivedNotifyUnknownUnsubscribe(self):
        """
        Items received from unknown nodes cause unsubscription.
        """
        self.event.nodeIdentifier = u'unknown'
        self.client.addObserver(self.observer)
        self.client.itemsReceived(self.event)
        self.assertEquals(0, len(self.observer.events))
        self.assertEquals(1, len(self.unsubscribeCalled))


    def test_itemsReceivedNotifyOtherResource(self):
        """
        Notifications sent to another JID are ignored.
        """
        self.event.recipient = JID('user@example.org/Other')
        self.client.addObserver(self.observer)
        self.client.itemsReceived(self.event)
        self.assertEquals(0, len(self.observer.events))
        self.assertEquals(0, len(self.unsubscribeCalled))



class TestNotifier(object):
    """
    A notifier that stores all notification in sequence.
    """

    def __init__(self):
        self.notifications = []


    def notify(self, notification):
        self.notifications.append(notification)
