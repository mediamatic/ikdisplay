# -*- test-case-name: ikdisplay.test.test_xmpp -*-

from zope.interface import Attribute, Interface
from twisted.internet import reactor, task
from twisted.python import log
from twisted.words.protocols.jabber import error
from twisted.words.protocols.jabber.jid import internJID as JID
from twisted.words.protocols.jabber.xmlstream import IQ, TimeoutError
from twisted.words.xish import domish

from wokkel.client import XMPPClient
from wokkel.ping import PingClientProtocol
from wokkel.pubsub import Item, PubSubClient
from wokkel.xmppim import MessageProtocol, PresenceProtocol

from axiom import item, attributes

NS_NOTIFICATION = 'http://mediamatic.nl/ns/ikdisplay/2009/notification'
NS_X_DELAY='jabber:x:delay'
NS_DELAY='urn:xmpp:delay'

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

# Allow this new attribute to be found when reading a store from disk.
attributes.JIDAttribute = JIDAttribute



def getPubSubService(uri):
    from urlparse import urlparse
    hostname = urlparse(uri)[1]
    if hostname[:4] == "www.":
        hostname = hostname[4:]
    if hostname[-6:] != '.local' and hostname.find('.test.') < 0:
        hostname = 'pubsub.' + hostname
    return JID(hostname)



class PubSubSubscription(item.Item):

    service = JIDAttribute("""The entity holding the node""",
                           )
    nodeIdentifier = attributes.text("""The node identifier""",
                                     default=u'')
    state = attributes.text("""Subscription state.""")



class IPubSubEventProcessor(Interface):
    subscription = Attribute("""Reference to subscription""")

    def itemsReceived(event):
        """Called when an items event is available for processing."""


    def installOnSubscription(other):
        """Register this processor to a subscription."""


    def uninstallFromSubscription(other):
        """Register this processor to a subscription."""


    def getNode():
        """Return the pubsub node to subscribe to."""



class PubSubDispatcher(PubSubClient):
    """
    Publish-subscribe client that renders to notifications for aggregation.
    """

    def __init__(self, store):
        self.store = store

        self._initialized = False


    def connectionInitialized(self):
        """
        Called when the XMPP connection has been established.

        Subscribe to all the nodes with the JID we connected with.
        """
        PubSubClient.connectionInitialized(self)

        self._initialized = True

        subscriptions = self.store.query(PubSubSubscription)
        for subscription in subscriptions:
            self.subscribe(subscription.service, subscription.nodeIdentifier,
                           self.parent.jid)


    def connectionLost(self, reason):
        self._initialized = False


    def addObserver(self, observer):
        """
        Add an observer for a subscription.

        This records an observer for a particular subscription, to be notified
        of new events for that subscription come in. If there is no such
        subscription yet and there is a valid connection, it will be requested.
        If there is no connection, when the connection is established, all
        subscriptions will be requested.
        """
        service, nodeIdentifier = observer.getNode()
        subscription = self.store.findOrCreate(PubSubSubscription,
                                               service=service,
                                               nodeIdentifier=nodeIdentifier)
        observer.installOnSubscription(subscription)

        def setSubscriptionState(result, subscription):
            subscription.state = result.state

        if self._initialized and subscription.state is None:
            d = self.subscribe(subscription.service,
                               subscription.nodeIdentifier,
                               self.parent.jid)
            d.addCallback(setSubscriptionState, subscription)
            d.addErrback(log.err)


    def removeObserver(self, observer):
        """
        Remove an observer for a subscription.

        If this is the last observer, unsubscribe.
        """

        subscription = observer.subscription
        if not subscription:
            return

        observer.uninstallFromSubscription(subscription)

        def clearSubscriptionState(result, subscription):
            subscription.state = None

        powerups = subscription.powerupsFor(IPubSubEventProcessor)
        try:
            powerups.next()
        except StopIteration:
            if self._initialized:
                d = self.unsubscribe(subscription.service,
                                     subscription.nodeIdentifier,
                                     self.parent.jid)
                d.addCallback(clearSubscriptionState, subscription)
                d.addErrback(log.err)


    def itemsReceived(self, event):
        """
        Called when items have been received.

        When items are received, an attempt is made to render them into
        notifications, and passed to the aggregator. The instance variable
        L{nods} keeps some information for each subscribed-to node, as a
        dictionary. The formatters are determined by the C{'type'} key in that
        dictionary.

        E.g. if the formatter is named C{'vote'}, the method C{format_vote}
        will be called with two arguments: the item payload as a
        L{domish.Element} and the node information dictionary.

        If items are received from unknown nodes, the subscription is
        cancelled.
        """
        if event.recipient != self.parent.jid:
            # This was not for us.
            return

        try:
            subscription = self.store.findUnique(PubSubSubscription,
                    attributes.AND(
                        PubSubSubscription.service==event.sender,
                        PubSubSubscription.nodeIdentifier==event.nodeIdentifier
                        )
                    )
        except KeyError:
            log.msg("Got event from %r, node %r. Unsubscribing." % (
                event.sender, event.nodeIdentifier))
            self.unsubscribe(event.sender, event.nodeIdentifier,
                             event.recipient)
            return

        for observer in subscription.powerupsFor(IPubSubEventProcessor):
            try:
                observer.itemsReceived(event)
            except Exception, e:
                log.err(e)


    def publishNotifications(self, service, nodeIdentifier, notifications):
        items = []
        for notification in notifications:
            payload = domish.Element((NS_NOTIFICATION, 'notification'))

            for key, value in notification.iteritems():
                payload.addElement(key, content=value)

            items.append(Item(payload=payload))

        def trapNotFound(failure):
            """
            If the node does not exist, create it and retry publish.
            """
            failure.trap(error.StanzaError)
            exc = failure.value
            if exc.condition != 'item-not-found':
                return failure
            else:
                d = self.createNode(service, nodeIdentifier)
                d.addCallback(lambda _: self.publish(service, nodeIdentifier,
                                                     items))

        def eb(failure):
            log.err(failure)

        d = self.publish(service, nodeIdentifier, items)
        d.addErrback(trapNotFound)
        d.addErrback(eb)



class PresenceHandler(PresenceProtocol):

    def connectionInitialized(self):
        PresenceProtocol.connectionInitialized(self)
        self.available(priority=-1)



class GroupChatHandler(MessageProtocol):

    def __init__(self, aggregator, occupantJID):
        self.aggregator = aggregator
        self.occupantJID = occupantJID
        self.presenceHandler = None


    def connectionInitialized(self):
        MessageProtocol.connectionInitialized(self)

        if self.presenceHandler is None:
            # Look for a presence handler
            for handler in self.parent:
                if isinstance(handler, PresenceProtocol):
                    self.presenceHandler = handler
                    break

        # Send presence to the room to join
        if self.presenceHandler is not None:
            self.presenceHandler.available(recipient=self.occupantJID)
        else:
            log.msg("No presence handler available for this connection!")


    def onMessage(self, message):
        sender = JID(message['from'])

        if (sender.userhost() == self.occupantJID.userhost() and
            message['type'] == 'groupchat' and
            message.body and
            sender.resource and
            (not message.x or message.x.uri not in (NS_X_DELAY, NS_X_DELAY))):

            notification = {
                    u'title': sender.resource or u'*',
                    u'subtitle': unicode(message.body),
                    }
            self.aggregator.processNotification(notification)



class Pinger(PingClientProtocol):
    verbose = False
    pingInterval = 30
    reconnectCount = 2

    def __init__(self, entity):
        self.entity = entity
        self.lc = task.LoopingCall(self.doPing)


    def connectionInitialized(self):
        self.lc.start(self.pingInterval)
        self.timeoutCount = 0


    def connectionLost(self, reason):
        if self.lc.running:
            self.lc.stop()


    def doPing(self):
        if self.verbose:
            log.msg("*** PING ***")

        def cb(result):
            self.timeoutCount = 0
            if self.verbose:
                log.msg("*** PONG ***")

        def trapRemoteServerNotFound(failure):
            failure.trap(error.StanzaError)
            exc = failure.value

            if exc.condition != 'remote-server-not-found':
                return failure

            log.msg("Remote server not found, restarting stream.")
            exc = error.StreamError('connection-timeout')
            reactor.callLater(1, self.xmlstream.sendStreamError, exc)

        def trapTimeout(failure):
            failure.trap(TimeoutError)
            self.timeoutCount += 1
            if self.timeoutCount >= self.reconnectCount:
                log.msg("Remote server not responding, restarting stream.")
                exc = error.StreamError('connection-timeout')
                reactor.callLater(1, self.xmlstream.sendStreamError, exc)


        d = self.ping(self.entity)
        d.addCallback(cb)
        d.addErrback(trapRemoteServerNotFound)
        d.addErrback(trapTimeout)
        d.addErrback(log.err)
        return d



def makeService(config):
    if IQ.timeout is None:
        IQ.timeout = 30

    xmppService = XMPPClient(config['jid'], config['secret'],
                             config.get('xmpp-host'),
                             config.get('xmpp-port', 5222))
    if config['verbose']:
        xmppService.logTraffic = True

    presenceHandler = PresenceHandler()
    presenceHandler.setHandlerParent(xmppService)

    pinger = Pinger(config['service'])
    pinger.setHandlerParent(xmppService)
    pinger.verbose = config['verbose']

    return xmppService
