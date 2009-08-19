// import Nevow.Athena
// import Divmod.Runtime
// import Divmod.Defer
// import jQuery


(function(jQuery)
{
    jQuery.extend({         
        noticeAdd: function(options, callback)
        {   
            var defaults = {
                inEffect:           {opacity: 'show'},  // in effect
                inEffectDuration:   600,                // in effect duration in miliseconds
                stayTime:           3000,               // time in miliseconds before the item has to disappear
                text:               '',                 // content of the item
                stay:               false,              // should the notice item stay or not?
                type:               'notice'            // could also be error, succes
            }
            
            // declare varaibles
            var options, noticeWrapAll, noticeItemOuter, noticeItemInner, noticeItemClose, noticeItemBody, colors;
            colors = ['#0098d4', '#1fa4da', '#3db0df', '#5cbce4', '#7ecaea', '#9ed7f0', '#bce3f5', '#d6edfa', '#e7f4fd'];
                                
            options         = jQuery.extend({}, defaults, options);
            noticeWrapAll   = (!jQuery('.notice-wrap').length) ? jQuery('<div></div>').addClass('notice-wrap').appendTo('body') : jQuery('.notice-wrap');
            noticeItemOuter = jQuery('<div></div>').addClass('notice-item-wrapper');
            noticeItemBody = '<div class="notice-body"><span class="title">'+options.notification.title+'</span>'
            if (options.notification.subtitle) {
                noticeItemBody += '<span class="subtitle"> – '+options.notification.subtitle+'</span>';
            }
            noticeItemBody += '</div>'

            noticeItemInner = jQuery('<div></div>')
                        .hide()
                        .addClass('notice-item ' + options.type)
                        .prependTo(noticeWrapAll)
                        .html(noticeItemBody)
                        .css({opacity: 0})
                        .animate({height: 'show'}, 200, function() {
                            if ($('.notice-body', this).height() <=
                                parseInt($(this).css('line-height')))
                            {
                                $(this).addClass('oneline');
                            }
                            $('.notice-item').each(function(index) {
                                $(this).css({backgroundColor: colors[index]});
                            });
                            $(this).animate({opacity: 1}, 200, callback);
                        })
                        .wrap(noticeItemOuter);
            noticeItemClose = jQuery('<div></div>').addClass('notice-item-close').prependTo(noticeItemInner).html('x').click(function() { jQuery.noticeRemove(noticeItemInner) });
            
            // hmmmz, zucht
            if(navigator.userAgent.match(/MSIE 6/i)) 
            {
                noticeWrapAll.css({top: document.documentElement.scrollTop});
            }
            
            if(!options.stay)
            {
                setTimeout(function()
                {
                    jQuery.noticeRemove(noticeItemInner);
                },
                options.stayTime);
            }
        },
        
        noticeRemove: function(obj, func)
        {
      obj.animate({height: 0, opacity: 0}, 200, function() {
        $(this).remove();
        func()
      });
        }
    });
})(jQuery);

Notifier.Notifier = Nevow.Athena.Widget.subclass("Notifier.Notifier");
Notifier.Notifier.methods(
    function renderNotification(self, notification) {
        d = Divmod.Defer.Deferred()
        var func = function() { $.noticeAdd({notification: notification, stay: true}, 
                                            function() {d.callback(null);}); };

        if ( $('.notice').length >= 9) {
            $.noticeRemove($('.notice-item-wrapper:last'), func);
        } else {
            func();
        }

        return d;
    }
);
