"""
Tests for L{ikdisplay.source}.
"""

from zope.interface import verify

from twisted.trial import unittest

from wokkel.generic import parseXml
from wokkel import pubsub

from ikdisplay import aggregator, source, xmpp

class PubSubSourceMixinTest(unittest.TestCase):

    def test_receiveItems(self):
        a = []

        class TestFeed(object):
            language = 'en'
            handle = 'test'
            processNotifications = a.append


        src = source.PubSubSourceMixin()
        src.feed = TestFeed()

        items = []
        event = pubsub.ItemsEvent(None, None, 'vote/160225', items, None)

        src.itemsReceived(event)

        self.assertEquals(1, len(a))

    def test_format(self):
        src = source.PubSubSourceMixin()
        items = []
        event = pubsub.ItemsEvent(None, None, 'vote/160225', items, None)

        notifications = src.format(event)
        self.assertEquals(0, len(notifications))


def formatPayload(src, xml):
    """
    Hook up a newly created source to a feed and call format_payload.
    """
    payload = parseXml(xml)

    feed = aggregator.Feed(handle=u'mediamatic', language=u'en')
    src.activate()
    src.feed = feed

    return src.format_payload(payload)


class PubSubSourceTests(object):

    def test_interfaceISource(self):
        """
        Does this source provide L{source.ISource}?
        """
        verify.verifyObject(source.ISource, self.source)


    def test_interfaceIPubSubEventProcessor(self):
        """
        Does this source provide L{xmpp.IPubSubEventProcessor}?
        """
        verify.verifyObject(xmpp.IPubSubEventProcessor, self.source)



class GetThingIDTest(unittest.TestCase):

    def test_good(self):
        uri = u'http://mediamatic.nl/id/1'
        self.assertEquals(u'1', source.getThingID(uri))



class SimpleSourceTest(unittest.TestCase, PubSubSourceTests):
    """
    Tests for L{ikdisplay.source.SimpleSource}.
    """

    def setUp(self):
        self.source = source.SimpleSource()



class VoteSourceTest(unittest.TestCase, PubSubSourceTests):
    """
    Tests for L{ikdisplay.source.VoteSource}.
    """

    def setUp(self):
        thing = source.Thing(uri=u'http://www.mediamatic.net/id/160225')
        self.source = source.VoteSource(question=thing)


    def test_formatPayload(self):
        xml = """
<rsp>
  <vote>
    <id>173603</id>
    <reader_serial>A3S280TD</reader_serial>
    <reader_id_ref>82984</reader_id_ref>
    <rfid_tag>urn:rfid:7E6FD7A0</rfid_tag>
    <user_id_ref>124445</user_id_ref>
    <user_session_id/>
    <answer_id_ref>160252</answer_id_ref>
    <question_id_ref>160225</question_id_ref>
    <reader_location_id_ref/>
    <timestamp>2010-09-09 15:21:29</timestamp>
    <source/>
    <poll_session_id/>
  </vote>
  <person>
    <title>Fred Pook</title>
    <image>http://fast.mediamatic.nl/f/sjnh/image/411/124445-480-480-crop.jpg</image>
    <works_for/>
  </person>
  <question>
    <title>Publieks-poll voor de DOEN pitch</title>
    <id>160225</id>
    <answers>
      <item>
        <answer_id>160252</answer_id>
        <title>Shadow Search Platform</title>
        <count>1</count>
        <percentage>33.3333333333</percentage>
      </item>
    </answers>
    <total_votes>3</total_votes>
  </question>
</rsp>
        """

        notification = formatPayload(self.source, xml)

        self.assertEquals(u'Fred Pook',
                          notification['title'])
        self.assertEquals(u'voted for Shadow Search Platform',
                          notification['subtitle'])



class PresenceSourceTest(unittest.TestCase, PubSubSourceTests):
    """
    Tests for L{ikdisplay.source.PresenceSource}.
    """

    def setUp(self):
        thing = source.Thing(uri=u'http://www.mediamatic.net/id/160225')
        self.source = source.PresenceSource(question=thing)


    def test_formatPayload(self):
        xml = """
<rsp>
  <vote>
    <id>173603</id>
    <reader_serial>A3S280TD</reader_serial>
    <reader_id_ref>82984</reader_id_ref>
    <rfid_tag>urn:rfid:7E6FD7A0</rfid_tag>
    <user_id_ref>124445</user_id_ref>
    <user_session_id/>
    <answer_id_ref>160252</answer_id_ref>
    <question_id_ref>160225</question_id_ref>
    <reader_location_id_ref/>
    <timestamp>2010-09-09 15:21:29</timestamp>
    <source/>
    <poll_session_id/>
  </vote>
  <person>
    <title>Fred Pook</title>
    <image>http://fast.mediamatic.nl/f/sjnh/image/411/124445-480-480-crop.jpg</image>
    <works_for/>
  </person>
  <question>
    <title>Publieks-poll voor de DOEN pitch</title>
    <id>160225</id>
    <answers>
      <item>
        <answer_id>160252</answer_id>
        <title>Shadow Search Platform</title>
        <count>1</count>
        <percentage>33.3333333333</percentage>
      </item>
    </answers>
    <total_votes>3</total_votes>
  </question>
</rsp>
        """

        notification = formatPayload(self.source, xml)

        self.assertEquals(u'Fred Pook',
                          notification['title'])
        self.assertEquals(u'was at the entrance',
                          notification['subtitle'])



class IkMicSourceTest(unittest.TestCase, PubSubSourceTests):
    """
    Tests for L{ikdisplay.source.IkMicSource}.
    """

    def setUp(self):
        thing = source.Thing(uri=u'http://www.mediamatic.net/id/160225')
        self.source = source.IkMicSource(question=thing)


    def test_formatPayload(self):
        xml = """
<rsp>
  <vote>
    <id>173603</id>
    <reader_serial>A3S280TD</reader_serial>
    <reader_id_ref>82984</reader_id_ref>
    <rfid_tag>urn:rfid:7E6FD7A0</rfid_tag>
    <user_id_ref>124445</user_id_ref>
    <user_session_id/>
    <answer_id_ref>160252</answer_id_ref>
    <question_id_ref>160225</question_id_ref>
    <reader_location_id_ref/>
    <timestamp>2010-09-09 15:21:29</timestamp>
    <source/>
    <poll_session_id/>
  </vote>
  <person>
    <title>Fred Pook</title>
    <image>http://fast.mediamatic.nl/f/sjnh/image/411/124445-480-480-crop.jpg</image>
    <works_for/>
  </person>
  <question>
    <title>Publieks-poll voor de DOEN pitch</title>
    <id>160225</id>
    <answers>
      <item>
        <answer_id>160252</answer_id>
        <title>Shadow Search Platform</title>
        <count>1</count>
        <percentage>33.3333333333</percentage>
      </item>
    </answers>
    <total_votes>3</total_votes>
  </question>
</rsp>
        """

        notification = formatPayload(self.source, xml)

        self.assertEquals(u'Fred Pook',
                          notification['title'])
        self.assertIn(notification['subtitle'],
                      source.IkMicSource.TEXTS_EN['interrupt'])



class StatusSourceTest(unittest.TestCase, PubSubSourceTests):
    """
    Tests for L{ikdisplay.source.StatusSource}.
    """

    def setUp(self):
        thing = source.Site(uri=u'http://www.mediamatic.net/')
        self.source = source.StatusSource(site=thing)


    def test_formatPayload(self):
        xml = """
<rsp>
  <status>roze koeken ftw</status>
  <person>
    <title>Arjan Scherpenisse</title>
    <image>http://fast.mediamatic.nl/f/sjnh/image/530/27597-480-480-crop.jpg</image>
    <uri>http://www.mediamatic.net/id/22661</uri>
  </person>
</rsp>
        """

        notification = formatPayload(self.source, xml)
        self.assertEquals(u'Arjan Scherpenisse',
                          notification['title'])
        self.assertEquals(u'roze koeken ftw',
                          notification['subtitle'])


    def test_formatPayloadNoStatus(self):
        xml = """
<rsp>
  <status></status>
  <person>
    <title>Arjan Scherpenisse</title>
    <image>http://fast.mediamatic.nl/f/sjnh/image/530/27597-480-480-crop.jpg</image>
    <uri>http://www.mediamatic.net/id/22661</uri>
  </person>
</rsp>
        """

        notification = formatPayload(self.source, xml)
        self.assertIdentical(None, notification)


    def test_formatPayloadStatusEmpty(self):
        xml = """
<rsp>
  <status>is</status>
  <person>
    <title>Arjan Scherpenisse</title>
    <image>http://fast.mediamatic.nl/f/sjnh/image/530/27597-480-480-crop.jpg</image>
    <uri>http://www.mediamatic.net/id/22661</uri>
  </person>
</rsp>
        """

        notification = formatPayload(self.source, xml)
        self.assertIdentical(None, notification)


    def test_getNodeSite(self):
        """
        A StatusSource for the whole site listens to the 'status' node.
        """
        service, nodeIdentifier = self.source.getNode()
        self.assertEqual('pubsub.mediamatic.net', service.full())
        self.assertEqual('status', nodeIdentifier)



class TwitterSourceTest(unittest.TestCase):
    """
    Tests for L{ikdisplay.source.TwitterSource}.
    """

    def setUp(self):
        self.source = source.TwitterSource()


    def test_interfaceISource(self):
        """
        Does this source provide L{source.ISource}?
        """
        verify.verifyObject(source.ISource, self.source)



class IkCamSourceTest(unittest.TestCase, PubSubSourceTests):
    """
    Tests for L{ikdisplay.source.IkCamSource}.
    """

    def setUp(self):
        self.source = source.IkCamSource()


    def test_getNodeCreator(self):
        """
        An IkCamSource with a creator listens for ikcam pictures by creator.
        """
        self.source.creator = source.Thing(uri=u'http://example.org/id/1')
        service, nodeIdentifier = self.source.getNode()
        self.assertEqual(u'pubsub.example.org', service.full())
        self.assertEqual(u'ikcam/1', nodeIdentifier)


    def test_getNodeEvent(self):
        """
        An IkCamSource with an event listens for ikcam pictures taken there.
        """
        self.source.event = source.Thing(uri=u'http://example.org/id/2')
        service, nodeIdentifier = self.source.getNode()
        self.assertEqual(u'pubsub.example.org', service.full())
        self.assertEqual(u'ikcam/by_event/2', nodeIdentifier)

    def test_formatPayload(self):
        xml = """
<notification xmlns="http://mediamatic.nl/ns/ikcam/2009/notification">
  <participants>
    <participant>After Midnight</participant>
  </participants>
  <title_template>%(names)s bij Noord</title_template>
  <body_template>Deze foto is genomen bij de tentoonstelling Noord van Mediamatic.</body_template>
  <event>
    <title>Noord exhibition</title>
    <id>162070</id>
  </event>
  <picture>
    <thg_id>163884</thg_id>
    <rsc_uri>http://www.mediamatic.net/id/163884</rsc_uri>
    <attachment_uri>http://fast.mediamatic.nl/f/sjnh/image/734/163884-600-480.jpg</attachment_uri>
  </picture>
</notification>
        """
        notification = formatPayload(self.source, xml)
        self.assertEquals(u'After Midnight', notification['title'])
        self.assertEquals(u'took a self-portrait at Noord exhibition',
                          notification['subtitle'])

class RegDeskSourceTest(unittest.TestCase, PubSubSourceTests):
    """
    Tests for L{ikdisplay.source.RegDeskSource}.
    """

    def setUp(self):
        self.source = source.RegDeskSource()



class RaceSourceTest(unittest.TestCase, PubSubSourceTests):
    """
    Tests for L{ikdisplay.source.RaceSource}.
    """

    def setUp(self):
        self.source = source.RaceSource()
