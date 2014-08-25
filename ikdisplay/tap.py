"""
ikDisplay Aggregator service.
"""

from oauth.oauth import OAuthConsumer, OAuthToken

from twisted.application import service, strports
from twisted.cred import portal, checkers
from twisted.conch import manhole, manhole_ssh
from twisted.conch.insults import insults
from twisted.python import usage
from twisted.web import resource, server, static
from twisted.words.protocols.jabber import jid

from axiom.store import Store

from twittytwister.twitter import TwitterFeed, TwitterMonitor

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
            ('twitter-oauth-consumer-key', None, None,
                'Twitter OAuth consumer key'),
            ('twitter-oauth-consumer-secret', None, None,
                'Twitter OAuth consumer secret'),
            ('twitter-oauth-token-key', None, None,
                'Twitter OAuth token key'),
            ('twitter-oauth-token-secret', None, None,
                'Twitter OAuth token secret'),

            ('embedly-key', None, None,
                'embed.ly API key'),

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

        try:
            self['twitter-oauth-consumer'] = OAuthConsumer(
                key=self['twitter-oauth-consumer-key'],
                secret=self['twitter-oauth-consumer-secret'])
            self['twitter-oauth-token'] = OAuthToken(
                key=self['twitter-oauth-token-key'],
                secret=self['twitter-oauth-token-secret'])
        except KeyError:
            self['twitter-oauth-consumer'] = None
            self['twitter-oauth-token'] = None
            if not self['twitter-user'] or not self['twitter-password']:
                raise usage.UsageError("Missing twitter credentials")



def getManholeFactory(namespace, **passwords):
    """
    Return a protocol factory to set up an ssh manhole.

    @param namespace: The initial global variables accessible in the
        interactive shell.
    @param passwords: This allows for providing username and password
        combinations as keyword arguments.
    """

    def chainedProtocolFactory():
        return insults.ServerProtocol(manhole.ColoredManhole,
                                      namespace)

    checker = checkers.InMemoryUsernamePasswordDatabaseDontUse(**passwords)
    sshRealm = manhole_ssh.TerminalRealm()
    sshRealm.chainedProtocolFactory = chainedProtocolFactory

    sshPortal = portal.Portal(sshRealm, [checker])
    return manhole_ssh.ConchFactory(sshPortal)



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
    twitterFeed = TwitterFeed(user=config.get('twitter-user'),
                              passwd=config.get('twitter-password'),
                              consumer=config.get('twitter-oauth-consumer'),
                              token=config.get('twitter-oauth-token'))
    twitterFeed.protocol = twitter.VerboseTwitterStream
    tm = TwitterMonitor(api=twitterFeed.filter, delegate=None, args=None)
    tm.setName('twitter')
    tm.setServiceParent(store)

    embedder = twitter.Embedder(config)
    td = twitter.TwitterDispatcher(store, tm, embedder)

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
        'embedder': embedder,
        'pubsub': pc,
        'root': rootResource,
        'store': store,
        'twitter': tm,
        'web': ws,
        }

    manholeFactory = getManholeFactory(namespace, admin=pw)
    manholeService = strports.service(config['manhole-port'], manholeFactory)
    manholeService.setServiceParent(s)

    return s
