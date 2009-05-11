from twisted.application import strports
from twisted.internet import defer, reactor

from nevow.appserver import NevowSite
from nevow.athena import LivePage, LiveElement
from nevow.loaders import xmlfile
from nevow.static import File

class NotifierElement(LiveElement):
    """
    A "live" notifier.
    """

    jsClass = u"Notifier.Notifier"

    def __init__(self, pagePath):
        self.docFactory = xmlfile(pagePath.path, 'NotifierPattern')



class NotifierParentPage(LivePage):
    """
    A "live" container page for L{NotifierElement}.
    """

    def __init__(self, controller, jsPath, pagePath):
        LivePage.__init__(self)
        self.controller = controller
        self.jsPath = jsPath
        self.pagePath = pagePath

        self.element = None
        self.queue = defer.DeferredQueue()
        self.jsModules.mapping[u'Notifier'] = jsPath.child('notifier.js').path
        self.jsModules.mapping[u'jQuery'] = jsPath.child('jquery.min.js').path
        self.docFactory = xmlfile(self.pagePath.path)


    def beforeRender(self, ctx):
        d = self.notifyOnDisconnect()
        d.addErrback(self.onDisconnect)


    def onDisconnect(self, reason):
        """
        We will be called back when the client disconnects
        """
        self.controller.pages.remove(self)


    def render_notifier(self, ctx, data):
        """
        Replace the tag with a new L{NotifierElement}.
        """
        self.element = NotifierElement(self.pagePath)
        self.element.setFragmentParent(self)
        self.controller.pages.add(self)
        reactor.callLater(0, self.showNotification)
        return self.element


    def child_(self, ctx):
        return NotifierParentPage(self.controller, self.jsPath, self.pagePath)


    def gotNotification(self, notification):
        self.queue.put(notification)


    def showNotification(self):
        d = self.queue.get()
        d.addCallback(lambda notification: self.element.callRemote('renderNotification', notification))
        d.addCallback(lambda _: self.showNotification())


def makeService(config):
    rootDir = config['root']

    root = NotifierParentPage(config['controller'],
                              config['js'], rootDir.child(config['page']))
    root.child_static = File(rootDir.child('static').path)

    site = NevowSite(root)
    webService = strports.service(config['webport'], site)

    return webService
