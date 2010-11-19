"""
Tests for L{ikdisplay.source}.
"""

from zope.interface import verify

from twisted.trial import unittest
from twisted.words.xish import domish

from wokkel.generic import parseXml
from wokkel import pubsub

from ikdisplay import aggregator, source, xmpp

class TestPubSubSource(source.PubSubSourceMixin):
    TEXTS_NL = {
            'via': u'Test Bron',
            }
    TEXTS_EN = {
            'via': u'Test Source',
            }

    via = None

    def format_payload(self, payload):
        return {
            'title': u'Title',
            'subtitle': u'Subtitle',
        }



class PubSubSourceMixinTest(unittest.TestCase):

    def setUp(self):
        self.notifications = []

        class TestFeed(object):
            language = 'en'
            handle = 'test'
            processNotifications = self.notifications.append


        self.source = TestPubSubSource()
        self.source.activate()
        self.source.feed = TestFeed()

        items = [pubsub.Item(payload=domish.Element((None, 'test')))]
        self.event = pubsub.ItemsEvent(None, None, 'vote/160225', items, None)


    def test_receiveItems(self):
        self.source.itemsReceived(self.event)
        self.assertEquals(1, len(self.notifications))


    def test_format(self):
        notifications = self.source.format(self.event)
        self.assertEquals(1, len(notifications))


    def test_formatVia(self):
        notifications = self.source.format(self.event)
        self.assertEquals(u'via Test Source', notifications[0]['meta'])


    def test_formatViaFromNotification(self):
        def format_payload(payload):
            return {'via': u'Other'}

        self.source.format_payload = format_payload
        notifications = self.source.format(self.event)
        self.assertEquals(u'via Other', notifications[0]['meta'])


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
        site = source.Site(uri=u'http://www.mediamatic.net/')
        self.source = source.StatusSource(site=site)


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



class ActivityStreamTest(unittest.TestCase, PubSubSourceTests):
    """
    Tests for L{ikdisplay.source.ActivityStreamSource}.
    """

    def setUp(self):
        site = source.Site(uri=u'http://dwaal.local/')
        self.source = source.ActivityStreamSource(site=site)


    def test_formatPayloadTag(self):
        xml = """
<entry xmlns="http://www.w3.org/2005/Atom">
  <published>2010-10-22T15:12:55+02:00</published>
  <updated>2010-10-22T15:12:55+02:00</updated>
  <id>http://dwaal.local/activity/80/15</id>
  <title type="html">Ralph Meijer tagde Birgit Meijer in Test artikel</title>
  <link href="http://dwaal.local/id/99" type="text/html" rel="alternate"/>
  <verb xmlns="http://activitystrea.ms/spec/1.0/">http://activitystrea.ms/schema/1.0/tag</verb>
  <object xmlns="http://activitystrea.ms/spec/1.0/">
    <id xmlns="http://www.w3.org/2005/Atom">http://dwaal.local/id/99</id>
    <title xmlns="http://www.w3.org/2005/Atom">Birgit Meijer</title>
    <object-type>http://mediamatic.nl/ns/anymeta/2008/kind/person</object-type>
  </object>
  <target xmlns="http://activitystrea.ms/spec/1.0/">
    <id xmlns="http://www.w3.org/2005/Atom">http://dwaal.local/id/83</id>
    <title xmlns="http://www.w3.org/2005/Atom">Test artikel</title>
    <object-type>http://mediamatic.nl/ns/anymeta/2008/kind/article</object-type>
  </target>
  <author>
    <id>http://dwaal.local/id/80</id>
    <uri>http://dwaal.local/id/80</uri>
    <name>Ralph Meijer</name>
    <object-type xmlns="http://activitystrea.ms/spec/1.0/">http://mediamatic.nl/ns/anymeta/2008/kind/person</object-type>
  </author>
</entry>"""

        notification = formatPayload(self.source, xml)
        self.assertEquals(u'Ralph Meijer', notification['title'])
        self.assertEquals(u'tagged Birgit Meijer in Test artikel',
                          notification['subtitle'])


    def test_formatPayloadPost(self):
        xml = """
<entry xmlns="http://www.w3.org/2005/Atom">
  <published>2010-10-22T15:12:55+02:00</published>
  <updated>2010-10-22T15:12:55+02:00</updated>
  <id>http://dwaal.local/activity/80/14</id>
  <title type="html">Ralph Meijer maakte Birgit Meijer</title>
  <link href="http://dwaal.local/id/99" type="text/html" rel="alternate"/>
  <verb xmlns="http://activitystrea.ms/spec/1.0/">http://activitystrea.ms/schema/1.0/post</verb>
  <object xmlns="http://activitystrea.ms/spec/1.0/">
    <id xmlns="http://www.w3.org/2005/Atom">http://dwaal.local/id/99</id>
    <title xmlns="http://www.w3.org/2005/Atom">Birgit Meijer</title>
    <object-type>http://mediamatic.nl/ns/anymeta/2008/kind/person</object-type>
  </object>
  <author>
    <id>http://dwaal.local/id/80</id>
    <uri>http://dwaal.local/id/80</uri>
    <name>Ralph Meijer</name>
    <object-type xmlns="http://activitystrea.ms/spec/1.0/">http://mediamatic.nl/ns/anymeta/2008/kind/person</object-type>
  </author>
</entry>"""

        notification = formatPayload(self.source, xml)
        self.assertEquals(u'Ralph Meijer', notification['title'])
        self.assertEquals(u'posted Birgit Meijer',
                          notification['subtitle'])
        self.assertEquals(u'http://dwaal.local/figure/80?width=80&height=80',
                          notification['icon'])


    def test_formatPayloadPostAttachment(self):
        xml = """
<entry xmlns="http://www.w3.org/2005/Atom">
  <published>2010-11-19T12:16:18+01:00</published>
  <updated>2010-11-19T12:16:18+01:00</updated>
  <id>http://www.mediamatic.net/activity/1053</id>
  <title type="html">anyMeta Cyborg created Evelyn, Simon, Axel at Dev Camp \xe2\x80\x9910 \xe2\x80\x94 IkSentric.</title>
  <link href="http://www.mediamatic.net/id/167544" type="text/html" rel="alternate"/>
  <verb xmlns="http://activitystrea.ms/spec/1.0/">http://activitystrea.ms/schema/1.0/post</verb>
  <object xmlns="http://activitystrea.ms/spec/1.0/">
    <id xmlns="http://www.w3.org/2005/Atom">http://www.mediamatic.net/id/167544</id>
    <title xmlns="http://www.w3.org/2005/Atom">Evelyn, Simon, Axel at Dev Camp \xe2\x80\x9910 \xe2\x80\x94 IkSentric</title>
    <object-type>http://mediamatic.nl/ns/anymeta/2008/kind/attachment</object-type>
  </object>
  <author>
    <id>http://www.mediamatic.net/id/28344</id>
    <uri>http://www.mediamatic.net/id/28344</uri>
    <name>anyMeta Cyborg</name>
    <object-type xmlns="http://activitystrea.ms/spec/1.0/">http://mediamatic.nl/ns/anymeta/2008/kind/person</object-type>
  </author>
  <link href="http://www.mediamatic.net/figure/28344" rel="preview"/>
</entry>"""

        notification = formatPayload(self.source, xml)
        self.assertEquals(u'http://www.mediamatic.net/figure/167544?width=480&height=320',
                          notification['picture'])


    def test_formatPayloadUpdate(self):
        xml = """
<entry xmlns="http://www.w3.org/2005/Atom">
  <published>2010-10-22T16:37:42+02:00</published>
  <updated>2010-10-22T16:37:42+02:00</updated>
  <id>http://dwaal.local/activity/80/16</id>
  <title type="html">Ralph Meijer paste Birgit Meijer! aan</title>
  <link href="http://dwaal.local/id/99" type="text/html" rel="alternate"/>
  <verb xmlns="http://activitystrea.ms/spec/1.0/">http://activitystrea.ms/schema/1.0/update</verb>
  <object xmlns="http://activitystrea.ms/spec/1.0/">
    <id xmlns="http://www.w3.org/2005/Atom">http://dwaal.local/id/99</id>
    <title xmlns="http://www.w3.org/2005/Atom">Birgit Meijer</title>
    <object-type>http://mediamatic.nl/ns/anymeta/2008/kind/person</object-type>
  </object>
  <author>
    <id>http://dwaal.local/id/80</id>
    <uri>http://dwaal.local/id/80</uri>
    <name>Ralph Meijer</name>
    <object-type xmlns="http://activitystrea.ms/spec/1.0/">http://mediamatic.nl/ns/anymeta/2008/kind/person</object-type>
  </author>
</entry>"""

        notification = formatPayload(self.source, xml)
        self.assertEquals(u'Ralph Meijer', notification['title'])
        self.assertEquals(u'updated Birgit Meijer',
                          notification['subtitle'])


    def test_getNodeSite(self):
        """
        A ActivityStreamSource for a site listens to the 'activity' node.
        """
        service, nodeIdentifier = self.source.getNode()
        self.assertEqual('dwaal.local', service.full())
        self.assertEqual('activity', nodeIdentifier)
