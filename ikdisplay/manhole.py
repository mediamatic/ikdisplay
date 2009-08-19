from twisted.application import strports
from twisted.cred import portal, checkers
from twisted.conch import manhole, manhole_ssh

def getManholeFactory(namespace, **passwords):
    def getManHole(_):
        m = manhole.Manhole(namespace)
        m.namespace['manhole'] = m
        return m

    realm = manhole_ssh.TerminalRealm()
    realm.chainedProtocolFactory.protocolFactory = getManHole
    p = portal.Portal(realm)
    p.registerChecker(
            checkers.InMemoryUsernamePasswordDatabaseDontUse(**passwords))
    f = manhole_ssh.ConchFactory(p)
    return f


def makeService(config, namespace):
    f = getManholeFactory(namespace, admin='admin')
    manholeService = strports.service(config['manhole-port'], f)
    return manholeService
