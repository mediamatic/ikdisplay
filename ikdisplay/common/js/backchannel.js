backChannel = 
{
	options: {
		itemAmount: 8,
		itemList:	'.list-ikdisplay-backchannel'
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
					$(this).animate({opacity: 1}, 300, callback);
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
	}
}
