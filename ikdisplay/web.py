from twisted.application import service, strports

from nevow import appserver, loaders, rend, tags as T, inevow
from formless import webform 
from twisted.web.util import redirectTo

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

    def render_storeIDinput(self, item):
        return T.input(type="hidden", name="storeID", value=unicode(item.storeID))

    def data_currentItem(self, ctx, r):
        return self.item


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
    Page for /xx/:id
    """

    def __init__(self, store, pagecls):
        ConfigurationPage.__init__(self, store)
        self.pagecls = pagecls

    def locateChild(self, ctx, segments):
        if len(segments) != 1:
            return rend.NotFound

        # lookup feed id in self.store
        if segments[0] == 'add':
            item = None
        else:
            r = list(self.store.query(self.pagecls.itemcls, self.pagecls.itemcls.storeID == segments[0]))
            if len(r) == 0:
                return rend.NotFound
            item = r[0]

        page = self.pagecls(self.store, item)
        return page, ()


class FeedFindPage (ConfigurationPage):
    """
    Page for /feed/:feed and /feed/:feed/:source
    """

    def __init__(self, store, pagecls):
        ConfigurationPage.__init__(self, store)
        self.pagecls = pagecls

    def locateChild(self, ctx, segments):
        if len(segments) < 1 or len(segments) > 2:
            return rend.NotFound

        if len(segments) == 1 and segments[0] == 'add':
            return FeedPage(self.store, None), ()

        r = list(self.store.query(self.pagecls.itemcls, self.pagecls.itemcls.storeID == segments[0]))
        if len(r) == 0:
            return rend.NotFound
        item = r[0]
        if len(segments) == 1:
            return FeedPage(self.store, item), ()

        # feed + source (index)
        index = int(segments[1])
        src = item.getSources()[index]
        return SourcePage(self.store, src), ()


class FeedPage (ConfigurationPage):
    itemcls = Feed

    def __init__(self, store, item):
        ConfigurationPage.__init__(self, store)
        self.item = item
        self.sources = list(self.item.powerupsFor(source.ISource))

    def render_pageTitle(self, ctx):
        return "Feed " + self.item.title

    def render_pageContents(self, ctx):
        return loaders.xmlfile("ikdisplay/web/static/feed.part.html")

    def data_sources(self, ctx, r):
        return self.sources

    def render_sourceLink(self, source):
        idx = self.sources.index(source)
        return T.a(href="/feed/%d/%d" % (self.item.storeID, idx))[ source.renderTitle() ]

    def render_sourceTypesOptions(self, ctx):
        opts = [s.title for s in source.allSources]
        return [
            T.option(value=opts.index(o))[o]
            for o in opts
            ]


class SourcePage (ConfigurationPage):

    def __init__(self, store, item):
        ConfigurationPage.__init__(self, store)
        self.item = item

    def render_pageTitle(self, ctx):
        if not self.item:
            return "New source"
        return self.item.renderTitle()

    def render_pageContents(self, ctx):
        return loaders.xmlfile("ikdisplay/web/static/source.part.html")

    def render_sourceForm(self, ctx):
        return self.item.getForm()



class AddSourceHandler (rend.Page) :

    def __init__(self, store):
        rend.Page.__init__(self)
        self.store = store

    def renderHTTP(self, r):
        feed = self.store.getItemByID(int(r.arg("storeID")))
        cls = source.allSources[int(r.arg("sourceIndex"))]
        src = cls(store=self.store)
        src.installOn(feed)

        idx = feed.getSources().index(src)
        url = "/feed/%s/%d" % (r.arg("storeID"), idx)
        return redirectTo(url, inevow.IRequest(r))



from axiom.store import Store
store = Store("/tmp/foo")

rootResource = FeedsPage(store)
rootResource.putChild('feed', FeedFindPage(store, FeedPage))
#rootResource.putChild('source', FindPage(store, SourcePage))
rootResource.putChild('addSource', AddSourceHandler(store))

application = service.Application("Feeds configuration")
strports.service("8080", appserver.NevowSite(rootResource)).setServiceParent(application)
