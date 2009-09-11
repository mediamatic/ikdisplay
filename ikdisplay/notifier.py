from twisted.application import service, strports
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

    TRANSPORT_IDLE_TIMEOUT = 60

    def __init__(self, controller, jsPath, pagePath):
        LivePage.__init__(self)
        self.controller = controller
        self.jsPath = jsPath
        self.pagePath = pagePath

        self.element = None
        self.queue = defer.DeferredQueue()
        self.jsModules.mapping[u'Notifier'] = jsPath.child('notifier.js').path
        self.jsModules.mapping[u'JQuery'] = jsPath.child('jquery.combined.min.js').path
        self.jsModules.mapping[u'BackChannel'] = jsPath.child('backchannel.js').path
        self.docFactory = xmlfile(self.pagePath.path)

        if hasattr(controller, 'getHistory'):
            def cb(notifications):
                for notification in notifications:
                    self.queue.put(notification)

            d = controller.getHistory()
            d.addCallback(cb)


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



class NotifierController(object):
    """
    Base class for page controllers.

    This keeps the set of listening pages to send notifications to.
    """

    producer = None

    def __init__(self):
        self.pages = set()


    def notify(self, notification):
        """
        Send notification to all listening pages.
        """

        for page in self.pages:
            page.gotNotification(notification)


    def getHistory(self):
        if self.producer is not None:
            return self.producer.getHistory()
        else:
            return defer.succeed([])



def makeService(config, title, controller):
    s = service.MultiService()

    # Set up web service.
    root = NotifierParentPage(controller, config['js'], config['page'])
    root.child_static = File(config['static'].path)

    site = NevowSite(root)

    notifierService = strports.service(config['webport'], site)
    notifierService.setName('notifier')
    notifierService.setServiceParent(s)

    # Set up GUI for accessing the page.

    if config['gui']:
        from ikdisplay import gui

        url = 'http://localhost:%d/' % int(config['webport'])
        g = gui.DisplayGUI(title, url)
        g.setServiceParent(s)

    return s
