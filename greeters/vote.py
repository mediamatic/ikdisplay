from twisted.internet import reactor
from twisted.words.protocols.jabber import error
from wokkel.pubsub import PubSubClient
from wokkel.client import XMPPClient

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


def makeService(config):
    xmppService = XMPPClient(config['jid'], config['secret'])
    if config['verbose']:
        xmppService.logTraffic = True
    xmppService.send('<presence><priority>-1</priority></presence>')

    pc = PubSubClientFromController(config['controller'],
                                    config['service'],
                                    config['nodeIdentifiers'])
    pc.setHandlerParent(xmppService)

    return xmppService
