# -*- test-case-name: ikdisplay.test.test_xmpp -*-

from zope.interface import Attribute, Interface
from twisted.internet import defer, reactor, task
from twisted.python import log
from twisted.words.protocols.jabber import error
from twisted.words.protocols.jabber.jid import internJID as JID
from twisted.words.protocols.jabber.xmlstream import IQ
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
    hostname = urlparse(uri).hostname
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

    def __init__(self, entity):
        self.entity = entity
        self.lc = task.LoopingCall(self.doPing)


    def connectionInitialized(self):
        self.lc.start(60)


    def connectionLost(self, reason):
        if self.lc.running:
            self.lc.stop()


    def doPing(self):
        if self.verbose:
            log.msg("*** PING ***")

        def cb(result):
            if self.verbose:
                log.msg("*** PONG ***")

        def eb(failure):
            failure.trap(error.StanzaError)
            exc = failure.value

            if exc.condition != 'remote-server-not-found':
                return failure

            log.msg("Remote server not found, restarting stream.")
            reactor.callLater(5, self.send, '</stream:stream>')

        d = self.ping(self.entity)
        d.addCallbacks(cb, eb)
        d.addErrback(log.err)
        return d



class PubSubClientFromNotifier(PubSubClient):
    """
    Publish-subscribe client that receives notifications for display.

    @ivar notifier: The notifier service.
    @ivar service: The publish-subscribe service
    @type service: L{JID}.
    @ivar nodeIdentifier: The publish-subscribe node.
    @type nodeIdentifier: L{unicode}.
    """

    maxHistory = 13

    def __init__(self, notifier, service, nodeIdentifier):
        PubSubClient.__init__(self)
        self.notifier = notifier
        self.service = service
        self.nodeIdentifier = nodeIdentifier

        self._subscribed = False
        self._gotHistory = False
        self._pendingHistory = set()
        self.history = []


    def connectionInitialized(self):
        """
        Called when the XMPP connection has been established.

        Subscribe to all the nodes with the JID we connected with.
        """
        PubSubClient.connectionInitialized(self)
        self.setupSubscription()


    def setupSubscription(self):
        clientJID = self.parent.jid

        # Subscribe to the node we want to track
        if not self._subscribed:
            def cb(result):
                self._subscribed = True

            d = self.subscribe(self.service, self.nodeIdentifier, clientJID)
            d.addCallbacks(cb, log.err)

        # Retrieve history from the node
        if not self._gotHistory:
            def eb(failure):
                log.err(failure)
                return []

            def processHistory(notifications):
                self._gotHistory = True
                self.history = list(notifications)
                pending = self._pendingHistory
                self._pendingHistory = set()
                for d in pending:
                    reactor.callLater(0, d.callback, self.history)

            d = self.items(self.service, self.nodeIdentifier,
                                         maxItems=self.maxHistory)
            d.addErrback(eb)
            d.addCallback(reversed)
            d.addCallback(self._notificationsFromItems)
            d.addCallback(processHistory)


    def refreshSubscription(self, service, nodeIdentifier):
        if service == self.service and nodeIdentifier == self.nodeIdentifier:
            return

        def cb(_):
            self._subscribed = False
            self._gotHistory = False
            self.history = []
            self.service = service
            self.nodeIdentifier = nodeIdentifier
            self.setupSubscription()

        clientJID = self.parent.jid

        if self._subscribed:
            d = self.unsubscribe(self.service, self.nodeIdentifier, clientJID)
        else:
            d = defer.succeed(None)

        d.addErrback(log.err)
        d.addCallback(cb)
        d.addErrback(log.err)


    def _notificationsFromItems(self, items):
        for item in items:
            try:
                payload = item.elements().next()
            except:
                continue

            if (payload.uri, payload.name) != (NS_NOTIFICATION,
                                               'notification'):
                continue

            notification = {}
            for element in payload.elements():
                notification[element.name] = unicode(element)

            yield notification


    def itemsReceived(self, event):
        """
        Called when items have been received.

        Items are notifications for display. Items received for other JIDs
        (including different resources of the JID we connect with) are dropped.
        If items are received from unknown nodes, the subscription is
        cancelled.

        @param event: The publish-subscribe event containing the items.
        @type event: L{pubsub.ItemsEvent}.
        """
        if event.recipient != self.parent.jid:
            # This was not for us.
            return
        elif (event.sender != self.service or
              event.nodeIdentifier != self.nodeIdentifier):
            log.msg("Got event from %r, node %r. Unsubscribing." % (
                event.sender, event.nodeIdentifier))
            self.unsubscribe(event.sender, event.nodeIdentifier,
                             event.recipient)
        else:
            for notification in self._notificationsFromItems(event.items):
                self.notifier.notify(notification)
                self.history.append(notification)
            self.history = self.history[-self.maxHistory:]


    def getHistory(self):
        if self._gotHistory:
            return defer.succeed(self.history)
        else:
            d = defer.Deferred()
            self._pendingHistory.add(d)
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
