from twisted.internet import reactor, task
from twisted.python import log
from twisted.words.protocols.jabber import error
from twisted.words.protocols.jabber.jid import internJID as JID
from twisted.words.protocols.jabber.xmlstream import IQ
from twisted.words.xish import domish

from wokkel.client import XMPPClient
from wokkel.ping import PingClientProtocol
from wokkel.pubsub import Item, PubSubClient
from wokkel.xmppim import AvailabilityPresence, MessageProtocol

NS_NOTIFICATION = 'http://mediamatic.nl/ns/ikdisplay/2009/notification'
NS_X_DELAY='jabber:x:delay'
NS_DELAY='urn:xmpp:delay'

class PubSubClientFromAggregator(PubSubClient):
    """
    Publish-subscribe client that renders to notifications for aggregation.
    """

    def __init__(self, aggregator, nodes):
        self.aggregator = aggregator
        self.nodes = nodes

    def connectionInitialized(self):
        """
        Called when the XMPP connection has been established.

        Subscribe to all the nodes with the JID we connected with.
        """
        PubSubClient.connectionInitialized(self)

        clientJID = self.parent.jid
        for service, nodeIdentifier in self.nodes:
            self.subscribe(service, nodeIdentifier, clientJID)


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
        try:
            nodeInfo = self.nodes[event.sender, event.nodeIdentifier]
        except KeyError:
            msg = "Got event from %r, node %r." % (event.sender,
                                                   event.nodeIdentifier)
            if event.recipient == self.parent.jid:
                msg += " Unsubscribing."
                self.unsubscribe(event.sender, event.nodeIdentifier,
                                 event.recipient)
            else:
                msg += " Dropping."
            log.msg(msg)
        else:
            for item in event.items:
                try:
                    element = item.elements().next()
                except (StopIteration):
                    continue

                nodeType = nodeInfo['type']
                method = getattr(self, 'format_' + nodeType)

                if method:
                    notification = method(element)
                    self.aggregator.processNotification(notification)
                else:
                    log.msg("No formatter has been defined for "
                            "%r at %r (%s). Dropping." %
                            (event.nodeIdentifier, event.sender, nodeType))


    def publishNotification(self, service, nodeIdentifier, notification):
        payload = domish.Element((NS_NOTIFICATION, 'notification'))

        for key, value in notification.iteritems():
            payload.addElement(key, content=value)

        def cb(result):
            log.msg("Joepie: %r" % result)

        def eb(failure):
            log.err(failure)

        d = self.publish(service, nodeIdentifier, [Item(payload=payload)])
        d.addCallback(cb)
        d.addErrback(eb)

class GroupChatHandler(MessageProtocol):

    def __init__(self, aggregator, occupantJID):
        self.aggregator = aggregator
        self.occupantJID = occupantJID


    def connectionInitialized(self):
        MessageProtocol.connectionInitialized(self)
        presence = AvailabilityPresence(self.occupantJID)
        self.send(presence.toElement())


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

    def __init__(self, entity):
        self.entity = entity
        self.lc = task.LoopingCall(self.doPing)


    def connectionInitialized(self):
        self.lc.start(60)


    def connectionLost(self, reason):
        self.lc.stop()


    def doPing(self):
        log.msg("*** PING ***")

        def cb(result):
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

    def __init__(self, notifier, service, nodeIdentifier):
        PubSubClient.__init__(self)
        self.notifier = notifier
        self.service = service
        self.nodeIdentifier = nodeIdentifier

        self._subscribed = False

    def connectionInitialized(self):
        """
        Called when the XMPP connection has been established.

        Subscribe to all the nodes with the JID we connected with.
        """
        PubSubClient.connectionInitialized(self)

        clientJID = self.parent.factory.authenticator.jid

        if not self._subscribed:
            def cb(result):
                self._subscribed = True

            d = self.subscribe(self.service, self.nodeIdentifier, clientJID)
            d.addCallbacks(cb, log.err)


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

        Items are notifications for display.

        If items are received from unknown nodes, the subscription is
        cancelled.
        """
        if (event.sender != self.service or
            event.nodeIdentifier != self.nodeIdentifier):
            log.msg("Got event from %r, node %r. Unsubscribing." % (
                event.sender, event.nodeIdentifier))
            self.unsubscribe(event.sender, event.nodeIdentifier,
                             event.recipient)
        else:
            for notification in self._notificationsFromItems(event.items):
                self.notifier.notify(notification)


    def getHistory(self, maxItems):
        def eb(failure):
            log.err(failure)
            return []

        d = self.items(self.service, self.nodeIdentifier, maxItems=maxItems)
        d.addErrback(eb)
        d.addCallback(reversed)
        d.addCallback(self._notificationsFromItems)
        return d


def makeService(config):
    if IQ.timeout is None:
        IQ.timeout = 30

    xmppService = XMPPClient(config['jid'], config['secret'])
    if config['verbose']:
        xmppService.logTraffic = True
    xmppService.send('<presence><priority>-1</priority></presence>')

    pinger = Pinger(config['service'])
    pinger.setHandlerParent(xmppService)

    return xmppService