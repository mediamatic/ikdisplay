from twisted.internet import reactor, task
from twisted.words.protocols.jabber import error
from wokkel.pubsub import PubSubClient
from wokkel.client import XMPPClient
from wokkel.disco import DiscoClientProtocol
from twisted.words.protocols.jabber.xmlstream import IQ

class PubSubClientFromController(PubSubClient):

    def __init__(self, controller, service, nodeIdentifiers):
        self.controller = controller
        self.service = service
        self.nodeIdentifiers = nodeIdentifiers

    def connectionInitialized(self):
        PubSubClient.connectionInitialized(self)

        clientJID = self.parent.factory.authenticator.jid
        for nodeIdentifier in self.nodeIdentifiers:
            def eb(failure):
                failure.trap(error.StanzaError)
                exc = failure.value
                if exc.condition != 'remote-server-not-found':
                    return failure
                reactor.callLater(5, self.send, '</stream:stream>')

            d = self.subscribe(self.service, nodeIdentifier,
                               clientJID)
            d.addErrback(eb)

    def itemsReceived(self, event):
        vote = event.items[0].rsp
        if vote:
            self.controller.gotVote(vote)



class Pinger(DiscoClientProtocol):

    def __init__(self, domain):
        self.domain = domain
        self.lc = task.LoopingCall(self.ping)


    def connectionInitialized(self):
        self.lc.start(60)


    def connectionLost(self, reason):
        self.lc.stop()


    def ping(self):
        d = self.requestInfo(self.domain)
        d.addBoth(lambda _: None)
        return d


def makeService(config):
    if IQ.timeout is None:
        IQ.timeout = 30

    xmppService = XMPPClient(config['jid'], config['secret'])
    if config['verbose']:
        xmppService.logTraffic = True
    xmppService.send('<presence><priority>-1</priority></presence>')

    pc = PubSubClientFromController(config['controller'],
                                    config['service'],
                                    config['nodeIdentifiers'])
    pc.setHandlerParent(xmppService)

    pinger = Pinger(config['service'])
    pinger.setHandlerParent(xmppService)

    return xmppService
