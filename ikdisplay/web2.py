from twisted.application import service, strports
from twisted.web import resource, static, server

from ikdisplay.aggregator import Feed, Site, Thing
from ikdisplay import source
import json
from axiom import store, item

class Encoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, store.ItemQuery):
            return list(obj)
        if isinstance(obj, item.Item):
            schema = obj.__class__.getSchema()
            val = dict([('_id', obj.storeID), ('_class', str(obj.__class__.__name__))] + [(k, getattr(obj, k)) for k, _ in schema])
            if source.ISource.providedBy(obj):
                val['_title'] = obj.renderTitle()
            return val
        return json.JSONEncoder.default(self, obj)


class NotFound(Exception):
    pass

class APIError(Exception):
    pass


class APIMethod(resource.Resource):
    def __init__(self, fun):
        resource.Resource.__init__(self)
        self.fun = fun

    def render(self, request):
        if 'help' in request.args:
            return self.fun.__doc__.strip()
        request.setHeader("Content-Type", "application/json")
        try:
            return json.dumps(self.fun(request), cls=Encoder)
        except KeyError, e:
            request.setResponseCode(400)
            return "Missing argument %s\n" % str(e)
        except NotFound, e:
            request.setResponseCode(404)
            return "%s not found\n" % str(e)
        except APIError, e:
            request.setResponseCode(400)
            return str(e)+"\n"


class APIResource(resource.Resource):

    def __init__(self, store):
        resource.Resource.__init__(self)
        self.store = store


    def getChild(self, path, req):
        method = 'api_%s' % (path.replace('.', '_'))
        if hasattr(self, method):
            return APIMethod(getattr(self, method))
        return resource.NoResource()


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
            setattr(item, k, unicode(args[k][0]))
        return item


st = store.Store("/tmp/foo")

rootResource = resource.Resource()
rootResource.putChild('', static.File("ikdisplay/web/index.html"))
rootResource.putChild('static', static.File("ikdisplay/web/static"))
rootResource.putChild('api', APIResource(st))

application = service.Application("Feeds configuration")
strports.service("8080", server.Site(rootResource)).setServiceParent(application)
