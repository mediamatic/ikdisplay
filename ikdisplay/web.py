# Copyright 2010 Mediamatic Lab
# See LICENSE for details

import simplejson as json

from twisted.web import resource, static, http
from twisted.internet import defer
from twisted.python import failure, log
from axiom import store, item, attributes
from twisted.web.server import NOT_DONE_YET

from ikdisplay.aggregator import Feed
from ikdisplay import source


class ProtectedResource(resource.Resource):

    def __init__(self, password):
        resource.Resource.__init__(self)
        self.password = password


    def render(self, request):
        request.setHeader('WWW-Authenticate', 'Basic realm="Test realm"')
        if request.getUser() != "admin" or request.getPassword() != self.password:
            request.setResponseCode(http.UNAUTHORIZED)
            request.setHeader('WWW-Authenticate', 'Basic realm="Test realm"')
            return static.Data("<body><h1>Unauthorized</h1></body>\n", "text/html").render(request)
        return resource.Resource.render(self, request)


class Encoder(json.JSONEncoder):
    def default(self, obj):
        if hasattr(obj, 'full'):
            return unicode(obj)
        if isinstance(obj, store.ItemQuery):
            return list(obj)
        if isinstance(obj, item.Item):
            schema = obj.__class__.getSchema()
            val = dict([(k, getattr(obj, k)) for k, _ in schema])
            val['_id'] = obj.storeID
            val['_class'] = str(obj.__class__.__name__)
            if source.ISource.providedBy(obj):
                val['_title'] = obj.renderTitle()
                val['_type'] = obj.title
            return val
        return json.JSONEncoder.default(self, obj)


class NotFound(Exception):
    pass


class APIMethod(ProtectedResource):

    def __init__(self, fun, pw):
        ProtectedResource.__init__(self, pw)
        self.fun = fun


    def render_GET(self, request):
        if 'help' in request.args:
            return self.fun.__doc__.strip()+"\n"
        request.setHeader("Content-Type", "application/json")

        result = defer.maybeDeferred(self.fun, request)
        result.addCallback(lambda r: json.dumps(r, cls=Encoder))

        def missingArgument(f):
            f.trap(KeyError)
            request.setResponseCode(http.BAD_REQUEST)
            return "Missing argument %s\n" % str(f.value)
        result.addErrback(missingArgument)

        def notFound(f):
            f.trap(NotFound)
            request.setResponseCode(http.NOT_FOUND)
            return "%s not found\n" % str(f.value)
        result.addErrback(notFound)

        def genericError(f):
            request.setResponseCode(http.BAD_REQUEST)
            log.err(f)
            return str(f.value)+"\n"
        result.addErrback(genericError)

        def finish(r):
            request.write(r)
            request.finish()
        result.addCallback(finish)

        return NOT_DONE_YET


    def render_POST(self, request):
        return self.render_GET(request)



class APIResource(resource.Resource):

    def __init__(self, store, pubsubDispatcher, twitterDispatcher, password):
        resource.Resource.__init__(self)
        self.store = store
        self.password = password
        self.pubsubDispatcher = pubsubDispatcher
        self.twitterDispatcher = twitterDispatcher


    def getChild(self, path, req):
        method = 'api_%s' % (path.replace('.', '_'))
        if hasattr(self, method):
            return APIMethod(getattr(self, method), self.password)
        return resource.NoResource()


    def api_sites(self, request):
        """ Get the list of all sites. """
        return self.store.query(source.Site)


    def api_feeds(self, request):
        """ Get the list of all feeds. """
        return self.store.query(Feed)


    def api_things(self, request):
        """ Get the list of all things. """
        return self.store.query(source.Thing)


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

        if source.IPubSubEventProcessor.providedBy(item):
            oldNode = item.getNode()
            oldEnabled = item.enabled

        # Map the update attributes
        for k in args.keys():
            if k not in schema:
                raise Exception("Invalid update attribute: " + k)
            value = unicode(args[k][0])
            if isinstance(schema[k], attributes.boolean):
                value = value == "true"
            if isinstance(schema[k], attributes.textlist):
                value = [s.strip() for s in value.strip().split("\n") if s.strip() != ""]
            if isinstance(schema[k], attributes.reference):
                if not value:
                    value = None
                else:
                    value = self.store.getItemByID(int(value))
            setattr(item, k, value)

        # Update the item
        if (source.IPubSubEventProcessor.providedBy(item) and
            (oldNode != item.getNode or oldEnabled != item.enabled)):
            # Call the pubsub service to fix stuff.
            if oldEnabled:
                self.pubsubDispatcher.removeObserver(item)
            if item.enabled:
                self.pubsubDispatcher.addObserver(item)

        if hasattr(item, 'terms') and hasattr(item, 'userIDs'):
            self.twitterDispatcher.refreshFilters()

        return item


    def api_removeItem(self, request):
        """ Removes the item {id} from the database. """

        item = self.api_getItem(request)

        # Cleanup
        if (source.IPubSubEventProcessor.providedBy(item)):
            self.pubsubDispatcher.removeObserver(item)

        if hasattr(item, 'terms') and hasattr(item, 'userIDs'):
            self.twitterDispatcher.refreshFilters()

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
        r = request.args
        feed = Feed(store=self.store, title=unicode(r["title"][0]),
                    handle=unicode(r["handle"][0]), language=unicode(r["language"][0]))
        return feed


    def api_addSite(self, request):
        """ Adds a new, unnamed site. Returns the feed item. """
        site = source.Site(store=self.store, title=u"Untitled site", uri=u"http://...")
        return site


    def api_selectSites(self, request):
        """ Returns all the sites as a JSON object which can be used in a dojo.data.ItemReadFileStore. """
        sites = self.api_sites(request)
        items = [{"id": s.storeID, "title": s.title} for s in sites]
        return {"identifier": "id", "items": items}


    def api_selectThings(self, request):
        """ Returns all the things as a JSON object which can be used in a dojo.data.ItemReadFileStore. """
        things = self.api_things(request)
        items = [{"id": s.storeID, "title": s.title} for s in things]
        return {"identifier": "id", "items": items}


    def api_addThing(self, request):
        """ Adds a new thing with a {uri}. Returns the thing item. """
        uri = request.args["uri"][0]
        return source.Thing.discoverCreate(self.store, uri)



class Index(ProtectedResource):
    def render_GET(self, request):
        return static.File("ikdisplay/web/index.html").render_GET(request)
