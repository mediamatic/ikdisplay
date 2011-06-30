backChannel = 
{
    connection: null,
    start_time: null,
    show_raw: 0,
    theQueue: $({}),

    options: {
        itemAmount: 13,
        itemList:   '.list-ikdisplay-backchannel'
    },
    
    addMessage: function(message, callback)
    {
        var clone = function()
        {
            backChannel.cloneMessage(message, callback);
        };

        if($('.item').length >= backChannel.options.itemAmount)
        {
            backChannel.removeMessage($('.item:last'), clone);
        }
        else
        {
            clone();
        }
    },
    
    cloneMessage: function(message, callback)
    {
        var clonedItem = $('.clone-item').clone().show().css({opacity: 0}).appendTo($('.tmp')).removeClass('clone-item');
        backChannel.fillClone(clonedItem, message);
        clonedItemHeight = $('.list-ikdisplay-backchannel-wrap', clonedItem).height();
        clonedItem  
                .removeClass('clone-item')
                .addClass('item')
                .css({opacity: 0, height: 0})
                .animate({height: clonedItemHeight}, 600, function() 
                {
                    $(this).animate({opacity: 1}, 300, function() {
                        $(this).css('height', 'auto');
                        callback();
                        });
                })
                .prependTo($(backChannel.options.itemList));
    },
    
    fillClone: function(clone, message)
    {
        $('.list-ikdisplay-backchannel-title', clone).text(message.title);
        $('.list-ikdisplay-backchannel-status', clone).text(message.text);
        $('.list-ikdisplay-backchannel-meta', clone).text(message.meta);

        if (message.picture)
        {
            $('.list-ikdisplay-backchannel-icon-wrap img', clone).remove();
            $('.list-ikdisplay-backchannel-picture img', clone).attr('src', message.picture);
        } else {
            $('.list-ikdisplay-backchannel-picture', clone).remove();

            if (message.icon)
            {
                $('.list-ikdisplay-backchannel-icon-wrap img', clone).attr('src', message.icon);
            } else {
                $('.list-ikdisplay-backchannel-icon-wrap', clone).remove();
                $('.list-ikdisplay-backchannel-wrap', clone).css('min-height', '0px');
            }
        }
    },
    
    removeMessage: function(removeObj, callback)
    {
        removeObj.remove();
        callback();                 
    },

    log: function (msg) {
        if ( window.console && window.console.log && window.console.assert )
        {
            console.log(msg);
        }
    },

    // show the raw XMPP information coming in
    raw_input: function (data) {
        if (backChannel.show_raw) {
            backChannel.log('RECV: ' + data);
        }
    },

    // show the raw XMPP information going out
    raw_output: function (data) {
        if (backChannel.show_raw) {
            backChannel.log('SENT: ' + data);
        }
    },

    /*
     * Parse an item into an array with fields for display.
     */
    parseNotification: function (item) {
        // Extract notification fields.
        var notification = {};
        notification.id = $(item).attr('id');
        $(item).find('notification').children().each(function () {
            notification[this.localName] = this.textContent;
            });
        notification.text = notification.subtitle;
        return notification;
    },

    /*
     * Queue display of an item.
     */
    notify: function(item) {
        $('.list-ikdisplay-backchannel').queue(function () {
            var self = this;
            backChannel.addMessage(backChannel.parseNotification(item), function () {
                $(self).dequeue();
                })
            });
    },

    on_event: function (message) {
        backChannel.log("Received event.");

        var item = $(message).find('item')[0];

        // Queue notification for display
        backChannel.notify(item);

        return true;
    },

    on_subscribe: function (sub) {
        backChannel.log("Subscribed to the node.");
    },

    on_items: function (items) {
        backChannel.log("Got items");
        $(items).find('item').each(function () {
            backChannel.notify(this);
        });
    }
}

$(document).ready(function () {
    $(document).trigger('connect', {
                    jid: 'bosh.mediamatic.nl',
                    password: ''
                });
});

$(document).bind('connect', function (ev, data) {
    var conn = new Strophe.Connection(
        "http://www.mediamatic.nl/http-bind/");

    backChannel.connection = conn;
    backChannel.connection.rawInput = backChannel.raw_input;
    backChannel.connection.rawOutput = backChannel.raw_output;

    conn.connect(data.jid, data.password, function (status) {
        if (status === Strophe.Status.CONNECTED) {
            $(document).trigger('connected');
        } else if (status === Strophe.Status.DISCONNECTED) {
            $(document).trigger('disconnected');
        }
    });

});

$(document).bind('connected', function () {
    // inform the user
    backChannel.log("Connection established.");

    backChannel.connection.send($pres().c('priority').t('-1'));
    backChannel.connection.pubsub.subscribe(
        backChannel.connection.jid,
        'feeds.mediamatic.nl',
        'mediamatic',
        [],
        backChannel.on_event,
        backChannel.on_subscribe
      );

    var pub = $iq({from: backChannel.connection.jid,
                   to: 'feeds.mediamatic.nl',
                   type:'get'})

    pub.c('pubsub',
    { xmlns:Strophe.NS.PUBSUB }).c('items', {node: 'mediamatic',
                                             max_items: '13'
                                             });

    backChannel.connection.sendIQ(pub.tree(), backChannel.on_items, null);

});

$(document).bind('disconnected', function () {
    backChannel.log("Connection terminated.");

    // remove dead connection object
    backChannel.connection = null;
});
