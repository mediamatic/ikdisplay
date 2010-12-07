"""
ikDisplay Aggregator service.
"""

from twisted.application import service, strports
from twisted.python import usage
from twisted.web import resource, server, static
from twisted.words.protocols.jabber import jid

from axiom.store import Store

from anymeta import manhole

from ikdisplay import aggregator, twitter, xmpp
from ikdisplay.web import Index, APIResource

class Options(usage.Options):
    optParameters = [
            ('dbdir', 'd', 'ikdisplay.axiom',
                'Path to the aggregator database store'),

            ('admin-secret', None, 'admin',
                'Admin password'),

            ('jid', None, None,
                'XMPP client JID'),
            ('secret', None, None,
                'XMPP client password'),
            ('xmpp-host', None, None,
                'XMPP host to connect to (instead of using SRV)'),
            ('xmpp-port', None, 5222,
                'XMPP port to connect to (instead of using SRV)',
                usage.portCoerce),
            ('service', None, None,
                'Publish-subscribe service'),

            ('twitter-user', None, None,
                'Twitter account'),
            ('twitter-password', None, None,
                'Twitter password'),

            ('web-port', None, 'tcp:8080',
                'Web service port'),

            ('manhole-port', None, 'tcp:2227:interface=127.0.0.1',
                'Manhole SSH service port'),
            ]

    optFlags = [
            ('verbose', 'v', 'Log traffic'),
            ]

    def postOptions(self):
        if not self['jid']:
            raise usage.UsageError("Missing client JID")
        else:
            try:
                self['jid'] = jid.internJID(self['jid'])
            except jid.invalidFormat:
                raise usage.UsageError("Invalid client JID")

        if self['secret'] is None:
            raise usage.UsageError("Missing client secret")

        if not self['service']:
            raise usage.UsageError("Missing publish-subscribe service JID")
        else:
            try:
                self['service'] = jid.internJID(self['service'])
            except jid.invalidFormat:
                raise usage.UsageError("Invalid publish-subscribe service JID")

        if not self['twitter-user'] or not self['twitter-password']:
            raise usage.UsageError("Missing twitter credentials")



def makeService(config):
    s = service.MultiService()

    #
    # The Store
    #
    store = Store(config['dbdir'], debug=False)
    service.IService(store).setServiceParent(s)

    # The Admin Secret
    pw = config['admin-secret']


    #
    # The XMPP
    #
    xmppService = xmpp.makeService(config)
    xmppService.setServiceParent(s)

    # Set up PubSubClient for receiving notifications.
    pc = xmpp.PubSubDispatcher(store)
    pc.setHandlerParent(xmppService)


    #
    # The Twitter
    #
    tm = twitter.TwitterMonitor(config['twitter-user'],
                                config['twitter-password'])
    tm.setName('twitter')
    td = twitter.TwitterDispatcher(store, tm)
    tm.consumer = td
    tm.setServiceParent(store)


    #
    # The Aggregator
    #
    agg = aggregator.PubSubAggregator(config['service'])
    agg.pubsubHandler = pc
    agg.setName('aggregator')
    agg.setServiceParent(service.IService(store))


    #
    # The Web
    #
    rootResource = resource.Resource()
    rootResource.putChild('', Index(pw))
    rootResource.putChild('static', static.File("ikdisplay/web/static"))
    rootResource.putChild('api', APIResource(store, pc, td, pw))

    ws = strports.service(config['web-port'], server.Site(rootResource))
    ws.setServiceParent(s)

    #
    # The Manhole.
    #
    namespace = {
        'aggregator': agg,
        'pubsub': pc,
        'root': rootResource,
        'store': store,
        'twitter': tm,
        'web': ws,
        }

    manholeFactory = manhole.getFactory(namespace, admin=pw)
    manholeService = strports.service(config['manhole-port'], manholeFactory)
    manholeService.setServiceParent(s)

    return s
