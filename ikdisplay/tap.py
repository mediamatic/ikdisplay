"""
ikDisplay Live Stream service.
"""

from twisted.application import service, strports
from twisted.web import resource, server, static

from axiom.store import Store

from anymeta import manhole

from ikdisplay import aggregator, twitter, xmpp
from ikdisplay.xmpp import PubSubSubscription
from ikdisplay.web import Index, APIResource


def makeService(config):
    s = service.MultiService()

    #
    # The store
    #
    store = Store(config['store-path'], debug=False)
    service.IService(store).setServiceParent(s)

    #
    # The aggregator
    #
    agg = aggregator.LoggingAggregator()
    agg.setName('aggregator')
    agg.setServiceParent(service.IService(store))

    #
    # Set up XMPP service.
    #
    xmppService = xmpp.makeService(config)
    xmppService.setServiceParent(s)

    #
    # Tie services to the store.
    #

    # Set up PubSubClient for receiving notifications.
    pc = xmpp.PubSubDispatcher(store)
    pc.setHandlerParent(xmppService)

    # Set up Twitter monitor
    tm = twitter.TwitterMonitor(config['twitter-user'], config['twitter-password'])
    tm.setName('twitter')
    td = twitter.TwitterDispatcher(store, tm)
    tm.consumer = td
    tm.setServiceParent(store)

    #
    # Web
    #
    pw = config.get('admin-password', 'admin')

    rootResource = resource.Resource()
    rootResource.putChild('', Index(pw))
    rootResource.putChild('static', static.File("ikdisplay/web/static"))
    rootResource.putChild('api', APIResource(store, pc, td, pw))

    ws = strports.service(config['web-port'], server.Site(rootResource))
    ws.setServiceParent(s)

    #
    # Set up Manhole.
    #
    namespace = {
        'PubSubSubscription': PubSubSubscription,
        'store': store,
        'twitter': tm,
        'root': rootResource,
        'web': ws,
        }

    manholeFactory = manhole.getFactory(namespace, admin=pw)
    manholeService = strports.service(config['manhole-port'], manholeFactory)
    manholeService.setServiceParent(s)

    return s
