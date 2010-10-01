dojo.require("dojo.hash");

dojo.ready(function()
{
    var template = {
        _cache: {},
        get: function(tpl) {
            if (typeof template._cache[tpl] != "undefined") {
                var d = new dojo.Deferred();
                d.callback(template._cache[tpl]);
                return d;
            }
            return dojo.xhrGet({url: "/static/" + tpl})
                .then(function(contents) {
                          template._cache[tpl] = jsontemplate.Template(contents);
                          return template._cache[tpl];
                      });
        }
    };

    var api = function(method, data) {
        return dojo.xhrPost({url: "/api/" + method, postData: dojo.objectToQuery(data), handleAs: "json"});
    };


    var renderTemplateWithData = function(tplfile, apicall, data) {
        var tpl = "";
        var d = template.get(tplfile)
            .then(function(t) {
                   tpl = t;
                   return api(apicall, data);
               })
            .then(function(result) {
                   dojo.byId("contents").innerHTML = tpl.expand(result);
               });
        return d;
    };


    /*
     * The page controllers
     */
    var controller = {
        feed: function(id) {
            renderTemplateWithData("feed.tpl", "feed", {id: id});
        },

        feeds: function() {
            renderTemplateWithData("feeds.tpl", "feeds");
        },

        source: function(id) {
            renderTemplateWithData("source.tpl", "getItem", {id: id});
        }

    };

    var dispatch = function() {
        var parts = dojo.hash().split("/");
        var base = parts.shift();
        var dispatch = controller[base];
        if (!dispatch) {
            dojo.hash("#feeds", true);
            return;
        }
        dispatch.apply(this, parts);
    };
    dojo.subscribe("/dojo/hashchange", null, dispatch);
    dispatch();
});
