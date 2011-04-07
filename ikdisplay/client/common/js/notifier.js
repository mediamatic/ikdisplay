// import Nevow.Athena
// import Divmod.Runtime
// import Divmod.Defer
// import JQuery
// import Back2Channel

backChannel.options.itemAmount = 13;

Notifier.NotifierPage = (
    Nevow.Athena.PageWidget.subclass("Notifier.NotifierPage"));

Notifier.NotifierPage.methods(
    function reconnect(self) {
        Divmod.Runtime.DelayedCall(3 * 1000, function() {
            var d = Divmod.Runtime.theRuntime.getPage(
                "./?__athena_reconnect__=1&timestamp=" + new Date().getTime()
                );
            d[1].addCallback(function (result) {
                if (result.response == "") {
                    reconnect();
                } else {
                    window.location.reload();
                }
            });
        });
    },
    function connectionLost(self, reason) {
        self.reconnect();
    }
);

Notifier.Notifier = Nevow.Athena.Widget.subclass("Notifier.Notifier");

Notifier.Notifier.methods(
    function renderNotification(self, notification) {
        notification.text = notification.subtitle
        d = Divmod.Defer.Deferred()
        backChannel.addMessage(notification, function() {d.callback(null);});
        return d;
    },
    function reload(self) {
        setTimeout(function(){window.location.reload();}, 1000);
    }
);
