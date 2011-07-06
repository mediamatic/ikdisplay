"""
Tests for L{ikdisplay.xmpp}.
"""

from zope.interface import implements

from twisted.internet import defer, task
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

        self.calls = []
        self.clock = task.Clock()

        xmlstream = utility.EventDispatcher()
        self.store = store.Store()
        self.client = xmpp.PubSubDispatcher(self.store, reactor=self.clock)
        self.client.subscribe = self.subscribe
        self.client.unsubscribe = self.unsubscribe
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


    def tearDown(self):
        self.assertEquals([], self.clock.calls)


    def _wrapCall(func):
        def call(self, *args, **kwargs):
            def cb(result):
                self.calls.append((func.__name__, 'end'))
                return result

            self.calls.append((func.__name__, 'start'))
            d = func(self, *args, **kwargs)
            d.addBoth(cb)
            return d

        return call

    @_wrapCall
    def subscribe(self, service, nodeIdentifier, subscriber,
                        options=None, sender=None):
        subscription = pubsub.Subscription(nodeIdentifier, subscriber,
                                           u'subscribed', options)
        d = defer.Deferred()
        self.clock.callLater(5, d.callback, subscription)
        return d

    @_wrapCall
    def unsubscribe(self, service, nodeIdentifier, subscriber,
                          subscriptionIdentifier=None, sender=None):
        d = defer.Deferred()
        self.clock.callLater(5, d.callback, None)
        return d


    def test_addObserver(self):
        """
        When adding an observer for the first time, subscribe to the node.
        """
        self.client.connectionInitialized()
        self.client.addObserver(self.observer)

        self.clock.advance(0)
        self.assertEquals([('subscribe', 'start')], self.calls)
        self.clock.advance(5)
        self.assertEquals([('subscribe', 'start'),
                           ('subscribe', 'end')], self.calls)


    def test_addObserverTwice(self):
        """
        When adding an observer for a second time, don't subscribe again.
        """
        observer2 = TestObserver(store=self.store,
                                 service=self.serviceJID,
                                 nodeIdentifier=self.nodeIdentifier)

        self.client.connectionInitialized()
        self.client.addObserver(self.observer)
        self.clock.advance(5)
        self.assertEquals([('subscribe', 'start'),
                           ('subscribe', 'end')], self.calls)

        self.client.addObserver(observer2)
        self.clock.advance(5)
        self.assertEquals([('subscribe', 'start'),
                           ('subscribe', 'end')], self.calls)


    def test_addObserverNotConnected(self):
        """
        Subscription requests can only go out after being connected.
        """
        self.client.addObserver(self.observer)
        self.clock.advance(5)
        self.assertEquals([], self.calls)

        self.client.connectionInitialized()
        self.assertEquals([('subscribe', 'start')], self.calls)
        self.clock.advance(5)
        self.assertEquals([('subscribe', 'start'),
                           ('subscribe', 'end')], self.calls)


    def test_addObserverNotConnectedTwice(self):
        """
        Two observers while not connected yield one subscription on connect.
        """
        observer2 = TestObserver(store=self.store,
                                 service=self.serviceJID,
                                 nodeIdentifier=self.nodeIdentifier)

        self.client.addObserver(self.observer)
        self.client.addObserver(observer2)

        self.assertEquals([], self.calls)
        self.client.connectionInitialized()
        self.clock.advance(0)
        self.assertEquals([('subscribe', 'start')], self.calls)
        self.clock.advance(5)
        self.assertEquals([('subscribe', 'start'),
                           ('subscribe', 'end')], self.calls)


    def test_removeObserver(self):
        """
        Removing the last observer subscribes from the node.
        """
        self.client.connectionInitialized()
        self.client.addObserver(self.observer)
        self.clock.advance(5)
        self.client.removeObserver(self.observer)
        self.clock.advance(5)

        self.assertEquals([('subscribe', 'start'),
                           ('subscribe', 'end'),
                           ('unsubscribe', 'start'),
                           ('unsubscribe', 'end')], self.calls)


    def test_removeObserverBeforeSubscribed(self):
        """
        Wait for subscription request response before unsubscribing.
        """
        self.client.connectionInitialized()
        self.client.addObserver(self.observer)
        self.clock.advance(0)
        self.client.removeObserver(self.observer)
        self.clock.advance(3)
        self.clock.advance(2)
        self.clock.advance(5)

        self.assertEquals([('subscribe', 'start'),
                           ('subscribe', 'end'),
                           ('unsubscribe', 'start'),
                           ('unsubscribe', 'end')], self.calls)


    def test_removeObserverAddAgain(self):
        """
        Requests are sequential when re-adding observer.
        """
        self.client.connectionInitialized()
        self.client.addObserver(self.observer)
        self.clock.advance(5)
        self.client.removeObserver(self.observer)
        self.clock.advance(5)
        self.client.addObserver(self.observer)
        self.clock.advance(5)

        self.assertEquals([('subscribe', 'start'),
                           ('subscribe', 'end'),
                           ('unsubscribe', 'start'),
                           ('unsubscribe', 'end'),
                           ('subscribe', 'start'),
                           ('subscribe', 'end')], self.calls)


    def test_removeObserverAddAgainBeforeUnsubscribed(self):
        """
        Requests are sequential when re-adding observer, even if impatient.

        This is similar to L{test_removeObserverAddAgain}, except for the
        timing, here the observer is re-added before the unsubscription
        request is finished.
        """
        self.client.connectionInitialized()
        self.client.addObserver(self.observer)
        self.clock.advance(5)
        self.client.removeObserver(self.observer)
        self.clock.advance(2)
        self.client.addObserver(self.observer)
        self.clock.advance(3)
        self.clock.advance(5)

        self.assertEquals([('subscribe', 'start'),
                           ('subscribe', 'end'),
                           ('unsubscribe', 'start'),
                           ('unsubscribe', 'end'),
                           ('subscribe', 'start'),
                           ('subscribe', 'end')], self.calls)


    def test_itemsReceivedNotify(self):
        """
        Received items result in notifications being generated and notified.
        """
        self.client.addObserver(self.observer)
        self.clock.advance(5)
        self.client.itemsReceived(self.event)
        self.assertEquals(1, len(self.observer.events))


    def test_itemsReceivedNotifyUnknownUnsubscribe(self):
        """
        Items received from unknown nodes cause unsubscription.
        """
        self.event.nodeIdentifier = u'unknown'
        self.client.addObserver(self.observer)
        self.clock.advance(5)
        self.calls = []
        self.client.itemsReceived(self.event)
        self.assertEquals(0, len(self.observer.events))
        self.assertEquals([('unsubscribe', 'start')], self.calls)
        self.clock.advance(5)


    def test_itemsReceivedNotifyOtherResource(self):
        """
        Notifications sent to another JID are ignored.
        """
        self.event.recipient = JID('user@example.org/Other')
        self.client.addObserver(self.observer)
        self.calls = []
        self.client.itemsReceived(self.event)
        self.assertEquals(0, len(self.observer.events))
        self.assertEquals([], self.calls)




class TestNotifier(object):
    """
    A notifier that stores all notification in sequence.
    """

    def __init__(self):
        self.notifications = []


    def notify(self, notification):
        self.notifications.append(notification)
