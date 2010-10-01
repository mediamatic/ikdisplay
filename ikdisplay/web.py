from twisted.application import service, strports
from nevow import appserver, loaders, rend, tags as T
from formless import webform 

from ikdisplay.aggregator import Feed, Site, Thing
from ikdisplay import source


class ConfigurationPage (rend.Page):
    docFactory = loaders.xmlfile("ikdisplay/web/static/base.html")

    def __init__(self, store):
        rend.Page.__init__(self)
        self.store = store

    def render_pageTitle(self, ctx):
        return ""

    def render_pageContents(self, ctx):
        return "fixme"


class FeedsPage (ConfigurationPage):
    """
    Pages overview
    """

    def render_pageTitle(self, ctx):
        return "Feeds list"

    def render_pageContents(self, ctx):
        return loaders.xmlfile("ikdisplay/web/static/feeds.part.html")

    def data_feeds(self, ctx, r):
        return self.store.query(Feed)

    def render_feedlink(self, feed):
        return T.a(href="/feed/%d" % feed.storeID)[ feed.title ]


class FindPage (ConfigurationPage):
    """
    Page for /feed/:id
    """

    def __init__(self, store, pagecls):
        ConfigurationPage.__init__(self, store)
        self.pagecls = pagecls

    def locateChild(self, ctx, segments):
        if len(segments) != 1:
            return rend.NotFound

        # lookup feed id in self.store
        print self.store
        if segments[0] == 'add':
            item = None
        else:
            r = list(self.store.query(self.pagecls.itemcls, self.pagecls.itemcls.storeID == segments[0]))
            if len(r) == 0:
                return rend.NotFound
            item = r[0]

        page = self.pagecls(self.store, item)
        return page, ()


class FeedPage (ConfigurationPage):
    itemcls = Feed

    def __init__(self, store, item):
        ConfigurationPage.__init__(self, store)
        self.item = item

    def render_pageTitle(self, ctx):
        return "Feed " + self.item.title

    def render_pageContents(self, ctx):
        return loaders.xmlfile("ikdisplay/web/static/feed.part.html")

    def data_sources(self, ctx, r):
        return self.item.powerupsFor(source.ISource)

    def render_sourceForm(self, source):
        return source.getForm()



from axiom.store import Store
store = Store("/tmp/foo")

rootResource = FeedsPage(store)
rootResource.putChild('feed', FindPage(store, FeedPage))

application = service.Application("Feeds configuration")
strports.service("8080", appserver.NevowSite(rootResource)).setServiceParent(application)
