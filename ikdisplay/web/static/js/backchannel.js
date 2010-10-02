dojo.require("dojo.hash");
dojo.require("dijit.Dialog");
dojo.require("dijit.form.Form");
dojo.require("dijit.form.Button");
dojo.require("dijit.form.Textarea");
dojo.require("dijit.form.TextBox");

dojo.ready(function()
{
    window.BackChannel = function() 
    {
        var self = this;

        /*
         * Simple static template fetching and in-memory caching.
         */
        self.template = {
            _cache: {},
            get: function(tpl) {
                if (typeof self.template._cache[tpl] != "undefined") {
                    var d = new dojo.Deferred();
                    d.callback(self.template._cache[tpl]);
                    return d;
                }
                return dojo.xhrGet({url: "/static/" + tpl, preventCache: true})
                    .then(function(contents) {
                              self.template._cache[tpl] = jsontemplate.Template(contents);
                              return self.template._cache[tpl];
                          });
            }
        };
        
        /*
         * API controller. Posts requests to /api/:method and returns JSON.
         */
        self.doAPI = function(method, data) {
            return dojo.xhrPost({url: "/api/" + method, postData: dojo.objectToQuery(data), handleAs: "json"});
        };


        /**
         * Helper fun to render a template with the data from an API call.
         */
        var renderTemplateWithData = function(tplfile, apicall, data) {
            var tpl = "";
            var d = self.template.get(tplfile)
                .then(function(t) {
                          tpl = t;
                          return self.doAPI(apicall, data);
                      })
                .then(function(result) {
                          dojo.byId("contents").innerHTML = tpl.expand(result);
                      });
            return d;
        };


        /*
         * The page controllers
         */
        self.controller = {
            feed: function(id) {
                return renderTemplateWithData("feed.tpl", "feed", {id: id});
            },

            feeds: function() {
                return renderTemplateWithData("feeds.tpl", "feeds");
            }
        };


        /*
         * Function for initiating actions on the backchannel.
         */
        self.actions = {
            addSource: function(feedId, idx) {
                if (idx == "") return;
                self.doAPI("addSource", {id: feedId, idx: idx})
                    .then(function(r) {
                              // Refresh
                              self.reload();
                          });
            },
            addFeed: function() {
                self.doAPI("addFeed")
                    .then(function(r) {
                              // Go to feed
                              self.dispatch("feed/" + r._id)
                                  .then(function() {
                                            self.actions.editItem(r._id, 'Edit feed', 'Feed');
                                        });
                          });
            },
            removeItem: function(id) {
                if (!confirm('Are you sure?')) return;
                self.doAPI("removeItem", {id: id})
                    .then(function(r) {
                              // Refresh
                              self.reload();
                          });
            },
            editItem: function(id, title, cls) {
                var template = null;
                self.template.get("form" + (cls ? "." + cls : "") + ".tpl")
                    .then(
                        function(tpl) {
                            template = tpl;
                            return self.doAPI("getItem", {id:id});
                    }).then(
                        function(data) {
                            self.dialog = new dijit.Dialog({title: title});
                            self.dialog.attr("content", template.expand(data));
                            self.dialog.show();
                        });
            },
            updateItem: function(id, button) {
                var form = dijit.getEnclosingWidget(button.domNode.parentNode);
                var args = form.attr("value");
                args.id = id;
                self.doAPI("updateItem", args).then(function(r) {
                                                        self.dialog.hide();
                                                        self.reload();
                                                    });
            }
        };


        self.dispatch = function(location) {
            if (!location) {
                location = dojo.hash();
            } else {
                dojo.hash(location);
            }
            var parts = location.split("/");
            var base = parts.shift();
            var dispatch = self.controller[base];
            if (!dispatch) {
                dispatch = self.controller.feeds;
            }
            self.dispatch.last = [dispatch, parts];
            return dispatch.apply(this, parts);
        };
        self.reload = function() {
            return self.dispatch.last[0].apply(this, self.dispatch.last[1]);
        };

        dojo.subscribe("/dojo/hashchange", null, dispatch);
        dispatch();
        
        return self;
    }();

});
