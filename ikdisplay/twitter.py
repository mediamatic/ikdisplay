from twisted.application import service
from twisted.internet import defer, error, reactor
from twisted.python import log
from twisted.web import error as http_error
from twisted.web.client import HTTPDownloader, _parse
from twisted.words.xish import domish

from wokkel import pubsub

from twittytwister import twitter, txml

NS_TWITTER = 'http://mediamatic.nl/ns/ikdisplay/2009/twitter'

def downloadPageWithFactory(url, file, contextFactory=None, *args, **kwargs):
    """
    Download a web page to a file and return the request factory.

    @param file: path to file on filesystem, or file-like object.

    See HTTPDownloader to see what extra args can be passed.
    """
    class HTTPDownloaderSavingProtocol(HTTPDownloader):
        def buildProtocol(self, addr):
            p = HTTPDownloader.buildProtocol(self, addr)
            self.lastProtocol = p
            return p

    scheme, host, port, path = _parse(url)
    factory = HTTPDownloaderSavingProtocol(url, file, *args, **kwargs)
    reactor.connectTCP(host, port, factory)
    return factory


class TwitterFeedWithFactory(twitter.TwitterFeed):
    """
    Twitter Feed returning factories.

    Where L{TwitterFeed}'s methods return the deferred that fires for requests,
    this class returns the whole request factory. This enables manual
    disconnects.
    """

    def _rtfeed(self, url, delegate, args):
        if args:
            url += '?' + self._urlencode(args)
        print 'Fetching', url
        return downloadPageWithFactory(url,
                                       txml.HoseFeed(delegate),
                                       agent=self.agent,
                                       headers=self._makeAuthHeader())


class TwitterMonitor(service.Service):
    initialDelay = 5
    delay = 5
    maxDelay = 5
    continueTrying = True
    errorState = None
    consumer = None

    def __init__(self, username, password, terms):
        self.controller = TwitterFeedWithFactory(username, password)
        self.terms = terms

    def startService(self):
        self.continueTrying = True
        self.doConnect()


    def stopService(self):
        self.continueTrying = False

    def doConnect(self):
        def cb(_):
            log.msg("Connection closed cleanly.")
            self.errorState = None
            self.delay = self.initialDelay

        def trapConnectError(failure):
            failure.trap(error.ConnectError,
                         error.TimeoutError,
                         error.ConnectionClosed)
            log.err(failure)
            if self.errorState != 'connect':
                self.errorState = 'connect'
                self.delay = 0.25
                self.maxDelay = 16
            else:
                self.delay = min(self.maxDelay, self.delay * 2)


        def trapHTTPError(failure):
            failure.trap(http_error.Error)
            log.err(failure, "HTTP error")

            if self.errorState != 'http':
                self.errorState = 'http'
                self.delay = 10
                self.maxDelay = 240
            else:
                self.delay = min(self.maxDelay, self.delay * 2)

        def trapOtherErrors(failure):
            log.err(failure)
            self.errorState = 'other'
            self.continueTrying = False


        def retry(_):
            if self.continueTrying:
                if self.delay == 0:
                    when = "now"
                else:
                    when = "in %0.2f seconds" % (self.delay,)
                log.msg("Reconnecting %s." % (when,))
                reactor.callLater(self.delay, self.doConnect)
            else:
                log.msg("Abandoning reconnect.")


        self.factory = self.controller.track(self.onEntry, self.terms)
        d = self.factory.deferred
        d.addCallback(cb)
        d.addErrback(trapConnectError)
        d.addErrback(trapHTTPError)
        d.addErrback(trapOtherErrors)
        d.addCallback(retry)


    def onEntry(self, entry):
        if self.consumer:
            self.consumer.processEntry(entry)



class TwitterLogger(TwitterMonitor):

    def processEntry(self, entry):
        print (u"%s: %s" % (entry.user.screen_name, entry.text)).encode('utf-8')


def propertyToDomish(prop):
    element = domish.Element((NS_TWITTER, prop.tag_name))

    for propName in prop.SIMPLE_PROPS:
        if hasattr(prop, propName):
            value = getattr(prop, propName)
            element.addElement(propName, content=value)

    for propName in prop.COMPLEX_PROPS:
        if hasattr(prop, propName):
            child = propertyToDomish(getattr(prop, propName))
            element.addChild(child)

    return element


class TwitterPubSubClient(pubsub.PubSubClient):

    def __init__(self, service, nodeIdentifier):
        self.service = service
        self.nodeIdentifier = nodeIdentifier
        self.queue = defer.DeferredQueue()
        self._initialized = False


    def connectionInitialized(self):
        pubsub.PubSubClient.connectionInitialized(self)
        self._initialized = True
        self.processQueue()


    def connectionLost(self, reason):
        self._initialized = False


    def processQueue(self):
        def publishItem(item):
            def publishFailed(failure):
                log.err(failure)
                log.msg("Requeueing")
                self.queue.put(item)

            d = self.publish(self.service, self.nodeIdentifier, [item])
            d.addErrback(publishFailed)
            return d

        if not self._initialized:
            return

        d = self.queue.get()
        d.addCallback(publishItem)
        d.addCallback(lambda _: reactor.callLater(0, self.processQueue))


    def processEntry(self, entry):
        payload = propertyToDomish(entry)
        item = pubsub.Item(entry.id, payload)
        self.queue.put(item)
