"""
ikDisplay Live Stream service.
"""

from twisted.application import strports, service
from twisted.python import usage
from twisted.words.protocols.jabber.jid import internJID as JID

from anymeta import manhole

from ikdisplay import xmpp
from ikdisplay.client import notifier

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
            ('gui', None, 'Provide GTK gui (use --reactor gtk2)')
    ]

    def postOptions(self):
        self['service'] = JID(self['service'])
        self['jid'] = JID(self['jid'])

        if self['style'] not in STYLES:
            raise usage.UsageError("Style should be one of %r" % STYLES)



def makeService(config):

    s = service.MultiService()

    title = "ikDisplay Live Stream"

    controller = notifier.NotifierController(config['style'])

    #
    # Set up display web service
    #

    ns = notifier.makeService(config, controller)
    ns.setServiceParent(s)

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
    # Set up GUI for accessing the page.
    #
    if config['gui']:
        from ikdisplay.client import gui
        url = 'http://localhost:%d/' % int(config['webport'])
        g = gui.DisplayGUI(title, url, controller, pc)
        g.setServiceParent(s)

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
