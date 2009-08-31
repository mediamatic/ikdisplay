from twisted.internet import reactor, task
from twisted.python import log
from twisted.words.protocols.jabber import error
from twisted.words.protocols.jabber.jid import internJID as JID
from twisted.words.protocols.jabber.xmlstream import IQ

from wokkel.client import XMPPClient
from wokkel.ping import PingClientProtocol
from wokkel.pubsub import PubSubClient
from wokkel.xmppim import AvailabilityPresence, MessageProtocol

class PubSubClientFromController(PubSubClient):

    def __init__(self, controller, nodes):
        self.controller = controller
        self.nodes = nodes

    def connectionInitialized(self):
        PubSubClient.connectionInitialized(self)

        clientJID = self.parent.factory.authenticator.jid
        for service, nodeIdentifier in self.nodes:
            self.subscribe(service, nodeIdentifier, clientJID)


    def itemsReceived(self, event):
        try:
            nodeInfo = self.nodes[event.sender, event.nodeIdentifier]
        except KeyError:
            log.msg("Got event from %r, node %r. Unsubscribing." % (
                event.sender, event.nodeIdentifier))
            self.unsubscribe(event.sender, event.nodeIdentifier,
                             event.recipient)
        else:
            self.controller.gotEvent(event, nodeInfo)


class GroupChatHandler(MessageProtocol):

    def __init__(self, controller, occupantJID):
        self.controller = controller
        self.occupantJID = occupantJID


    def connectionInitialized(self):
        MessageProtocol.connectionInitialized(self)
        presence = AvailabilityPresence(self.occupantJID)
        self.send(presence.toElement())


    def onMessage(self, message):
        sender = JID(message['from'])

        if (sender.userhost() == self.occupantJID.userhost() and
            message['type'] == 'groupchat' and
            message.body):
            body = unicode(message.body)
            self.controller.gotGroupChatMessage(sender.resource, body)



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



def makeService(config, controller):
    if IQ.timeout is None:
        IQ.timeout = 30

    xmppService = XMPPClient(config['jid'], config['secret'])
    if config['verbose']:
        xmppService.logTraffic = True
    xmppService.send('<presence><priority>-1</priority></presence>')

    pc = PubSubClientFromController(controller,
                                    config['nodes'])
    pc.setHandlerParent(xmppService)

    pinger = Pinger(config['service'])
    pinger.setHandlerParent(xmppService)

    return xmppService
