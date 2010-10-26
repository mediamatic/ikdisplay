from zope.interface import implements

from twisted.application import strports
from twisted.internet import defer, reactor
from twisted.python.filepath import FilePath

from nevow import inevow, vhost
from nevow.appserver import NevowSite
from nevow.athena import LivePage, LiveElement
from nevow.loaders import xmlfile
from nevow.static import File

commonPath = FilePath(__file__).sibling('common')

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

    def __init__(self, controller, style):
        LivePage.__init__(self)
        self.controller = controller

        self.element = None
        self.queue = defer.DeferredQueue()

        jsPath = commonPath.child('js')
        self.jsModules.mapping.update({
            u'Notifier': jsPath.child('notifier.js').path,
            u'JQuery': jsPath.child('jquery.combined.min.js').path,
            u'Back2Channel': jsPath.child('backchannel.js').path,
            })

        self.pagePath = commonPath.child('livestream_%s.html' % style)
        self.docFactory = xmlfile(self.pagePath.path)

        if hasattr(controller, 'getHistory'):
            def cb(notifications):
                for notification in notifications:
                    self.gotNotification(notification)

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


    def gotNotification(self, notification):
        notification = dict(((unicode(key), unicode(value))
                             for key, value in notification.iteritems()))
        self.queue.put(notification)


    def showNotification(self):
        d = self.queue.get()
        d.addCallback(lambda notification:
                self.element.callRemote('renderNotification', notification))
        d.addCallback(lambda _: self.showNotification())



class NotifierController(LivePage):
    """
    Top-level resource for managing notifier pages.

    This keeps the set of listening pages to send notifications to.

    LivePages can only be rendered once, as they have a one-on-one connection
    to the browser that made the request. This resource will create a new
    instance of NotifierParentPage for each page request.
    """

    producer = None

    # Make sure that we are a directory-like resource
    addSlash = True


    def __init__(self, style):
        LivePage.__init__(self)
        self.style = style
        self.pages = set()


    def child_(self, ctx):
        """
        Return new page instance for each request, instead of self.
        """
        return NotifierParentPage(self, self.style)


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



class VhostFakeRoot:
    """
    I am a wrapper to be used at site root when you want to combine
    vhost.VHostMonsterResource with nevow.guard. If you are using guard, you
    will pass me a guard.SessionWrapper resource.
    Also can hide generic resources
    """
    implements(inevow.IResource)
    def __init__(self, wrapped):
        self.wrapped = wrapped

    def renderHTTP(self, ctx):
        return self.wrapped.renderHTTP(ctx)

    def locateChild(self, ctx, segments):
        """Returns a VHostMonster if the first segment is "vhost". Otherwise
        delegates to the wrapped resource."""
        if segments[0] == "vhost":
            return vhost.VHostMonsterResource(), segments[1:]
        else:
            return self.wrapped.locateChild(ctx, segments)


def makeResource(config, controller):
    root = controller

    root.child_static = File(commonPath.child('static').path)

    proxyPath = config.get('proxyPath', None)
    if proxyPath:
        oldRoot = root
        if oldRoot.children is None:
            oldRoot.children = {}
        oldRoot.children[proxyPath] = oldRoot

        root = VhostFakeRoot(oldRoot)

    return root


def makeService(config, controller):
    root = makeResource(config, controller)
    site = NevowSite(root)

    notifierService = strports.service(config['webport'], site)
    notifierService.setName('notifier')

    return notifierService
