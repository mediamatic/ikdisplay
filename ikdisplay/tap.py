"""
ikDisplay Live Stream service.
"""

from twisted.application import strports
from twisted.python import usage
from twisted.python.filepath import FilePath
from twisted.words.protocols.jabber.jid import internJID as JID

from anymeta import manhole

from ikdisplay import notifier, xmpp

STYLES = ('beamer', 'beamer_all', 'screen', 'screen_ikcam')

class Options(usage.Options):

    optParameters = [
        ('service', None, None,
            'Publish-subscribe service'),
        ('node', None, None,
            'Publish-subscribe node'),
        ('style', None, 'beamer',
            'Display style'),
        ('webport', None, '8082',
            'Port of the web display site'),
        ('jid', None, None,
            'JID used to login and subscribe to notifications'),
        ('secret', None, None,
            'Login password'),
        ('manhole-port', None, '2226',
            'Manhole SSH service port'),
        ('xmpp-host', None, None,
            'XMPP host to connect to (instead of using SRV)'),
        ('xmpp-port', None, 5222,
            'XMPP port to connect to (instead of using SRV)',
            usage.portCoerce),
    ]

    optFlags = [
            ('verbose', 'v', 'Log traffic'),
            ('gui', None, 'Show GTK dialog'),
    ]

    def postOptions(self):
        self['service'] = JID(self['service'])
        self['jid'] = JID(self['jid'])

        if self['style'] not in STYLES:
            raise usage.UsageError("Style should be one of %r" % STYLES)



def makeService(config):

    title = "ikDisplay Live Stream"

    commonPath = FilePath(notifier.__file__).sibling('common')
    config['page'] = commonPath.child('livestream_%s.html' % config['style'])
    config['js'] = commonPath.child('js')
    config['static'] =commonPath.child('static')

    controller = notifier.NotifierController()

    #
    # Set up display web service
    #

    s = notifier.makeService(config, title, controller)

    #
    #
    # Set up XMPP service.
    #

    xmppService = xmpp.makeService(config)
    xmppService.setServiceParent(s)

    # Set up PubSubClient for receiving notifications.
    pc = xmpp.PubSubClientFromNotifier(controller, config['service'],
                                                   config['node'])
    pc.setHandlerParent(xmppService)

    controller.producer = pc


    #
    # Set up Manhole.
    #

    namespace = {
        'controller': controller,
        'notifier': s.getServiceNamed('notifier'),
        'xmpp': xmppService,
        }

    manholeFactory = manhole.getFactory(namespace, admin='admin')
    manholeService = strports.service(config['manhole-port'], manholeFactory)
    manholeService.setServiceParent(s)

    return s
