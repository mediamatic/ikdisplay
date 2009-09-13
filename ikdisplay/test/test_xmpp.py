"""
Tests for L{ikdisplay.xmpp}.
"""

from twisted.trial import unittest
from twisted.words.protocols.jabber.jid import JID
from twisted.words.xish import domish

from wokkel import pubsub
from ikdisplay import xmpp

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
        self.clientJID = JID('user@example.org/Home')
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
        self.event = pubsub.ItemsEvent(serviceJID, self.clientJID,
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
