from twisted.application import service, strports
from twisted.web import resource, static, server, http

from ikdisplay.aggregator import Feed, Site, Thing
from ikdisplay import source
import json
from axiom import store, item, attributes


class ProtectedResource(resource.Resource):

    def render(self, request):
        request.setHeader('WWW-Authenticate', 'Basic realm="Test realm"')
        if request.getUser() != "admin" or request.getPassword() != "admin":
            request.setResponseCode(http.UNAUTHORIZED)
            request.setHeader('WWW-Authenticate', 'Basic realm="Test realm"')
            return static.Data("<body><h1>Unauthorized</h1></body>", "text/html").render(request)
        return resource.Resource.render(self, request)


class Encoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, store.ItemQuery):
            return list(obj)
        if isinstance(obj, item.Item):
            schema = obj.__class__.getSchema()
            val = dict([('_id', obj.storeID), ('_class', str(obj.__class__.__name__))] + [(k, getattr(obj, k)) for k, _ in schema])
            if source.ISource.providedBy(obj):
                val['_title'] = obj.renderTitle()
                val['_type'] = obj.title
            if isinstance(obj, Feed):
                val['_uri'] = obj.getURI()
            return val
        return json.JSONEncoder.default(self, obj)


class NotFound(Exception):
    pass

class APIError(Exception):
    pass


class APIMethod(ProtectedResource):

    def __init__(self, fun):
        ProtectedResource.__init__(self)
        self.fun = fun


    def render_GET(self, request):
        if 'help' in request.args:
            return self.fun.__doc__.strip()
        request.setHeader("Content-Type", "application/json")
        try:
            return json.dumps(self.fun(request), cls=Encoder)
        except KeyError, e:
            request.setResponseCode(http.BAD_REQUEST)
            return "Missing argument %s\n" % str(e)
        except NotFound, e:
            request.setResponseCode(http.NOT_FOUND)
            return "%s not found\n" % str(e)
        except APIError, e:
            request.setResponseCode(http.BAD_REQUEST)
            return str(e)+"\n"


    def render_POST(self, request):
        return self.render_GET(request)



class APIResource(resource.Resource):

    def __init__(self, store):
        resource.Resource.__init__(self)
        self.store = store


    def getChild(self, path, req):
        method = 'api_%s' % (path.replace('.', '_'))
        if hasattr(self, method):
            return APIMethod(getattr(self, method))
        return resource.NoResource()


    def api_sites(self, request):
        """ Get the list of all sites. """
        return self.store.query(Site)


    def api_feeds(self, request):
        """ Get the list of all feeds. """
        return self.store.query(Feed)


    def api_feed(self, request):
        """ Get a feed and its sources by {id}. """
        id = int(request.args["id"][0])
        try:
            feed = self.store.getItemByID(id)
        except KeyError:
            raise NotFound(id)
        result = Encoder().default(feed)
        result['sources'] = feed.getSources()
        result['allSources'] = [(i, source.allSources[i].title) for i in range(len(source.allSources))]
        return result


    def api_getItem(self, request):
        """ Given an {id}, get the corresponding item from the database. """
        id = int(request.args["id"][0])
        try:
            return self.store.getItemByID(id)
        except KeyError:
            raise NotFound(id)


    def api_updateItem(self, request):
        """ Edit the contents of an item. {id} is the id of the item; other args are treated as updates to the item. """
        item = self.api_getItem(request)
        args = dict(request.args)
        del args['id']
        schema = dict(item.__class__.getSchema())
        for k in args.keys():
            if k not in schema:
                raise APIError("Invalid update attribute: " + k)
            value = unicode(args[k][0])
            if isinstance(schema[k], attributes.textlist):
                value = [s.strip() for s in value.strip().split("\n") if s.strip() != ""]
            setattr(item, k, value)
        return item


    def api_removeItem(self, request):
        """ Removes the item {id} from the database. """
        item = self.api_getItem(request)
        item.deleteFromStore(True)
        return {"status": "deleted"}


    def api_addSource(self, request):
        """ Adds the {n}th source to the feed specified by {id}. Returns the new source. """
        feed = self.api_getItem(request)
        cls = source.allSources[int(request.args["idx"][0])]
        src = cls(store=self.store)
        src.installOn(feed)
        return src


    def api_addFeed(self, request):
        """ Adds a new, unnamed feed. Returns the feed item. """
        feed = Feed(store=self.store, title=u"Untitled feed", handle=u"handle", language=u"en")
        return feed


    def api_addSite(self, request):
        """ Adds a new, unnamed site. Returns the feed item. """
        site = Site(store=self.store, title=u"Untitled site", uri=u"http://...")
        return site


st = store.Store("/tmp/foo")

class Index(ProtectedResource):
    def render_GET(self, request):
        return static.File("ikdisplay/web/index.html").render_GET(request)


print Index()

rootResource = resource.Resource()
rootResource.putChild('', Index())
rootResource.putChild('static', static.File("ikdisplay/web/static"))
rootResource.putChild('api', APIResource(st))

application = service.Application("Feeds configuration")
strports.service("8080", server.Site(rootResource)).setServiceParent(application)
