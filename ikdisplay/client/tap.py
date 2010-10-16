"""
ikDisplay Live Stream service.
"""

from twisted.application import strports, service
from twisted.python import usage
from twisted.python.filepath import FilePath
from twisted.words.protocols.jabber.jid import internJID as JID

from anymeta import manhole

from ikdisplay import xmpp
from ikdisplay.client import notifier, gui

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
            ('verbose', 'v', 'Log traffic')
    ]

    def postOptions(self):
        self['service'] = JID(self['service'])
        self['jid'] = JID(self['jid'])

        if self['style'] not in STYLES:
            raise usage.UsageError("Style should be one of %r" % STYLES)




class ClientService (service.MultiService):

    title = "ikDisplay Live Stream"

    controller = None
    notifier = None
    xmppClient = None
    pubsubClient = None
    

    def __init__(self, config):
        service.MultiService.__init__(self)
        self.config = config

        self.commonPath = FilePath(notifier.__file__).sibling('common')
        self.config['js'] = self.commonPath.child('js')
        self.config['static'] = self.commonPath.child('static')

        # Set up XMPP service.
        self.xmppService = xmpp.makeService(config)
        self.xmppService.setServiceParent(self)

        # The controller
        self.controller = notifier.NotifierController()


    def startStream(self, service, node, style):

        self.service = service
        self.node = node
        self.style = style

        self.controller.reloadAll()

        def start():
            # Set up display web service
            pagePath = self.commonPath.child('livestream_%s.html' % style)
            self.notifier = notifier.makeService(self.config, self.title, self.controller, pagePath)
            self.notifier.setServiceParent(self)

            # Set up PubSubClient for receiving notifications.
            self.pubsubClient = xmpp.PubSubClientFromNotifier(self.controller, service, node)
            self.pubsubClient.setHandlerParent(self.xmppService)

            # Tie together
            self.controller.producer = self.pubsubClient


        if self.notifier:
            # Service has been started already; stop first
            self.pubsubClient.disownHandlerParent(self.xmppService)
            d = self.notifier.disownServiceParent()
            if d:
                d.addCallback(lambda _: start())
            else:
                start()
        else:
            start()




def makeService(config):

    s = ClientService(config)

    s.startStream(config['service'], config['node'], config['style'])

    #
    # Set up GUI for accessing the page.
    #
    url = 'http://localhost:%d/' % int(config['webport'])
    g = gui.DisplayGUI(s.title, url)
    g.setServiceParent(s)

    #
    # Set up Manhole.
    #

    namespace = {
        'controller': s.controller,
        'notifier': s.getServiceNamed('notifier'),
        'xmpp': s.xmppService,
        }

    manholeFactory = manhole.getFactory(namespace, admin='admin')
    manholeService = strports.service(config['manhole-port'], manholeFactory)
    manholeService.setServiceParent(s)

    return s
