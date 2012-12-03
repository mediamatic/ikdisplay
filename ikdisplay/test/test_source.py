"""
Tests for L{ikdisplay.source}.
"""

from zope.interface import verify

from twisted.trial import unittest
from twisted.words.xish import domish

from wokkel.generic import parseXml
from wokkel import pubsub

from twittytwister.streaming import Entities, Indices, Media, Status, URL, User

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



class TestFeed(object):
    storeID = 1
    language = 'en'
    handle = 'test'
    notifications = []

    def processNotifications(self, notifications):
        self.notifications.extend(notifications)



class PubSubSourceMixinTest(unittest.TestCase):

    def setUp(self):


        self.feed = TestFeed()

        self.source = TestPubSubSource()
        self.source.feed = self.feed
        self.source.activate()

        items = [pubsub.Item(payload=domish.Element((None, 'test')))]
        self.event = pubsub.ItemsEvent(None, None, 'vote/160225', items, None)


    def test_receiveItems(self):
        self.source.itemsReceived(self.event)
        self.assertEquals(1, len(self.feed.notifications))


    def test_format(self):
        notifications = self.source.format(self.event)
        self.assertEquals(1, len(notifications))


    def test_formatVia(self):
        notifications = self.source.format(self.event)
        self.assertTrue(notifications[0]['meta'].endswith(u' via Test Source'))


    def test_formatViaFromNotification(self):
        def format_payload(payload):
            return {'via': u'Other'}

        self.source.format_payload = format_payload
        notifications = self.source.format(self.event)
        self.assertTrue(notifications[0]['meta'].endswith(u' via Other'))


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
</rsp>"""

        notification = formatPayload(self.source, xml)

        self.assertEquals(u'Fred Pook',
                          notification['title'])
        self.assertEquals(u'voted for Shadow Search Platform',
                          notification['subtitle'])



    def test_formatPayloadUnknown(self):
        """
        Unknown tags will report as Illegal Alien.
        """
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
    <title/>
    <image/>
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
</rsp>"""

        notification = formatPayload(self.source, xml)

        self.assertEquals(u'An illegal alien',
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
</rsp>"""

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
</rsp>"""

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
</rsp>"""

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
</rsp>"""

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
        self.feed = aggregator.Feed(handle=u'test', language=u'en')

        self.source = source.TwitterSource()
        self.source.feed = self.feed
        self.source.activate()

        user = User()
        user.id = 2426271
        user.screen_name = u'ralphm'
        user.profile_image_url = u'http://a2.twimg.com/profile_images/45293402/ralphm-buddy_normal.png'

        self.status = Status()
        self.status.user = user
        self.status.text = u'Test'

        self.source = source.TwitterSource()
        self.source.feed = self.feed
        self.source.activate()

    def test_interfaceISource(self):
        """
        Does this source provide L{source.ISource}?
        """
        verify.verifyObject(source.ISource, self.source)


    def test_format(self):
        notification = self.source.format(self.status)
        self.assertEquals(u'ralphm', notification['title'])
        self.assertEquals(u'Test', notification['subtitle'])
        self.assertEquals(self.status.user.profile_image_url,
                          notification['icon'])
        self.assertTrue(notification['meta'].endswith(u' via Twitter'))


    def test_formatDisplayURL(self):
        self.status.text = (u'#Photos on Twitter: taking flight '
                            'http://t.co/qbJx26r http://t.co/123456')

        self.status.entities = Entities()
        media = Media()
        media.url = "http://t.co/qbJx26r"
        media.display_url = "pic.twitter.com/qbJx26r"
        media.indices = Indices()
        media.indices.start = 34
        media.indices.end = 53
        self.status.entities.media = [media]
        url = URL()
        url.url = "http://t.co/123456"
        url.display_url = u"pic.twitter.com/12345\u2026"
        url.indices = Indices()
        url.indices.start = 54
        url.indices.end = 73
        self.status.entities.urls = [url]

        notification = self.source.format(self.status)
        self.assertEquals(u'#Photos on Twitter: taking flight '
                            u'pic.twitter.com/qbJx26r '
                            u'pic.twitter.com/12345\u2026',
                          notification['subtitle'])
        self.assertEquals(u'#Photos on Twitter: taking flight '
                            u"<a href='http://t.co/qbJx26r'>"
                              u"pic.twitter.com/qbJx26r</a> "
                            u"<a href='http://t.co/123456'>"
                              u"pic.twitter.com/12345\u2026</a>",
                          notification['html'])


    def test_formatMatchPermutation(self):
        """
        Space separated terms match statuses in other permutations.
        """
        self.status.text = "twisted python rocks"
        self.source.terms = ['python twisted']
        notification = self.source.format(self.status)
        self.assertNotIdentical(None, notification)


    def test_formatMatchQuoted(self):
        """
        Quoted terms match.
        """
        self.status.text = "twisted python rocks"
        self.source.terms = ['"twisted python"']
        notification = self.source.format(self.status)
        self.assertNotIdentical(None, notification)


    def test_formatMatchQuotedNoPermutation(self):
        """
        Quoted terms do not match in other permutations.
        """
        self.status.text = "twisted python rocks"
        self.source.terms = ['"python twisted"']
        notification = self.source.format(self.status)
        self.assertIdentical(None, notification)


    def test_formatMatchUserID(self):
        self.source.terms = []
        self.source.userIDs = ['2426271']
        notification = self.source.format(self.status)
        self.assertNotIdentical(None, notification)


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
<entry xmlns="http://www.w3.org/2005/Atom">
  <published>2011-03-30T14:02:31+02:00</published>
  <updated>2011-03-30T14:02:31+02:00</updated>
  <id>http://ixion.local/activity/832</id>
  <title type="html">&lt;a href="http://ixion.local/person/421/nl"&gt;aapje&lt;/a&gt; maakte een &lt;a href="http://ixion.local/page/613/nl"&gt;zelfportret&lt;/a&gt; tijdens &lt;a href="http://ixion.local/page/528/nl"&gt;Eurosonic Noorderslag&lt;/a&gt;.</title>
  <link rel="alternate" type="text/html" href="http://ixion.local/page/613/nl"/>
  <verb xmlns="http://activitystrea.ms/spec/1.0/">http://mediamatic.nl/ns/anymeta/2010/activitystreams/ikcam</verb>
  <object xmlns="http://activitystrea.ms/spec/1.0/">
    <id xmlns="http://www.w3.org/2005/Atom">http://ixion.local/id/613</id>
    <object-type>http://mediamatic.nl/ns/anymeta/2008/kind/attachment</object-type>
    <title xmlns="http://www.w3.org/2005/Atom">asfd at Eurosonic Noorderslag</title>
    <link xmlns="http://www.w3.org/2005/Atom" rel="alternate" href="http://ixion.local/page/613/nl"/>
    <link xmlns="http://www.w3.org/2005/Atom" rel="enclosure" href="http://ixion.local/image/804/613-480-360.jpg"/>
    <link xmlns="http://www.w3.org/2005/Atom" rel="figure" href="http://ixion.local/figure/613"/>
  </object>
  <target xmlns="http://activitystrea.ms/spec/1.0/">
    <id xmlns="http://www.w3.org/2005/Atom">http://ixion.local/id/528</id>
    <object-type>http://mediamatic.nl/ns/anymeta/2008/kind/artefact</object-type>
    <title xmlns="http://www.w3.org/2005/Atom">Eurosonic Noorderslag</title>
    <link xmlns="http://www.w3.org/2005/Atom" rel="alternate" href="http://ixion.local/page/528/nl"/>
  </target>
  <author>
    <id>http://ixion.local/id/421</id>
    <object-type xmlns="http://activitystrea.ms/spec/1.0/">http://mediamatic.nl/ns/anymeta/2008/kind/person</object-type>
    <link rel="alternate" href="http://ixion.local/person/421/nl"/>
    <name>aapje</name>
    <uri>http://ixion.local/person/421/nl</uri>
  </author>
  <agent xmlns="http://mediamatic.nl/ns/anymeta/">
    <id xmlns="http://www.w3.org/2005/Atom">http://ixion.local/id/526</id>
    <object-type xmlns="http://activitystrea.ms/spec/1.0/">http://mediamatic.nl/ns/anymeta/2008/kind/person</object-type>
    <title xmlns="http://www.w3.org/2005/Atom">ikCam Agent</title>
    <link xmlns="http://www.w3.org/2005/Atom" rel="alternate" href="http://ixion.local/person/526/nl"/>
  </agent>
</entry>"""

        self.source.event = source.Thing(uri=u'http://ixion.local/id/528')
        notification = formatPayload(self.source, xml)
        self.assertEquals(u'aapje', notification['title'])
        self.assertEquals(u'took a self-portrait at Eurosonic Noorderslag',
                          notification['subtitle'])
        self.assertEquals(u'http://ixion.local/figure/613?width=480', notification['picture'])


    def test_formatPayloadMultiple(self):
        xml = """
<entry xmlns="http://www.w3.org/2005/Atom">
  <published>2011-03-30T16:49:31+02:00</published>
  <updated>2011-03-30T16:49:31+02:00</updated>
  <id>http://ixion.local/activity/834</id>
  <title type="html">&lt;a href="http://ixion.local/person/521/nl"&gt;Arjan&lt;/a&gt; en &lt;a href="http://ixion.local/person/421/nl"&gt;aapje&lt;/a&gt; maakten samen een &lt;a href="http://ixion.local/page/614/nl"&gt;groepsfoto&lt;/a&gt; tijdens &lt;a href="http://ixion.local/page/528/nl"&gt;Eurosonic Noorderslag&lt;/a&gt;.</title>
  <link rel="alternate" type="text/html" href="http://ixion.local/page/614/nl"/>
  <verb xmlns="http://activitystrea.ms/spec/1.0/">http://mediamatic.nl/ns/anymeta/2010/activitystreams/ikcam</verb>
  <object xmlns="http://activitystrea.ms/spec/1.0/">
    <id xmlns="http://www.w3.org/2005/Atom">http://ixion.local/id/614</id>
    <object-type>http://mediamatic.nl/ns/anymeta/2008/kind/attachment</object-type>
    <title xmlns="http://www.w3.org/2005/Atom">Arjan en asfd at Eurosonic Noorderslag</title>
    <link xmlns="http://www.w3.org/2005/Atom" rel="alternate" href="http://ixion.local/page/614/nl"/>
    <link xmlns="http://www.w3.org/2005/Atom" rel="enclosure" href="http://ixion.local/image/789/614-480-360.jpg"/>
    <link xmlns="http://www.w3.org/2005/Atom" rel="figure" href="http://ixion.local/figure/614"/>
  </object>
  <target xmlns="http://activitystrea.ms/spec/1.0/">
    <id xmlns="http://www.w3.org/2005/Atom">http://ixion.local/id/528</id>
    <object-type>http://mediamatic.nl/ns/anymeta/2008/kind/artefact</object-type>
    <title xmlns="http://www.w3.org/2005/Atom">Eurosonic Noorderslag</title>
    <link xmlns="http://www.w3.org/2005/Atom" rel="alternate" href="http://ixion.local/page/528/nl"/>
  </target>
  <author>
    <id>http://ixion.local/id/521</id>
    <object-type xmlns="http://activitystrea.ms/spec/1.0/">http://mediamatic.nl/ns/anymeta/2008/kind/person</object-type>
    <link rel="alternate" href="http://ixion.local/person/521/nl"/>
    <name>Arjan</name>
    <uri>http://ixion.local/person/521/nl</uri>
  </author>
  <author>
    <id>http://ixion.local/id/421</id>
    <object-type xmlns="http://activitystrea.ms/spec/1.0/">http://mediamatic.nl/ns/anymeta/2008/kind/person</object-type>
    <link rel="alternate" href="http://ixion.local/person/421/nl"/>
    <name>aapje</name>
    <uri>http://ixion.local/person/421/nl</uri>
  </author>
  <agent xmlns="http://mediamatic.nl/ns/anymeta/">
    <id xmlns="http://www.w3.org/2005/Atom">http://ixion.local/id/526</id>
    <object-type xmlns="http://activitystrea.ms/spec/1.0/">http://mediamatic.nl/ns/anymeta/2008/kind/person</object-type>
    <title xmlns="http://www.w3.org/2005/Atom">ikCam Agent</title>
    <link xmlns="http://www.w3.org/2005/Atom" rel="alternate" href="http://ixion.local/person/526/nl"/>
  </agent>
</entry>
"""
        self.source.event = source.Thing(uri=u'http://ixion.local/id/528')
        notification = formatPayload(self.source, xml)
        self.assertEquals(u'Arjan and aapje', notification['title'])
        self.assertEquals(u'took a group portrait at Eurosonic Noorderslag',
                          notification['subtitle'])
        self.assertEquals(u'http://ixion.local/figure/614?width=480', notification['picture'])


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



class ActivityStreamSourceTest(unittest.TestCase, PubSubSourceTests):
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
        """
        An entry with the post verb that includes an actor icon.
        """
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
    <link rel="enclosure" href="http://dwaal.local/image/432/96-192-192.jpg"/>
    <link rel="figure" href="http://dwaal.local/figure/80"/>
  </author>
</entry>"""

        notification = formatPayload(self.source, xml)
        self.assertEquals(u'Ralph Meijer', notification['title'])
        self.assertEquals(u'posted Birgit Meijer',
                          notification['subtitle'])
        self.assertEquals(u'http://dwaal.local/figure/80?width=80&height=80&filter=crop',
                          notification['icon'])


    def test_formatPayloadPostNoIcon(self):
        """
        An entry with the post verb that lacks an actor icon.
        """
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
        self.assertNotIn('icon', notification)


    def test_formatPayloadPostAttachment(self):
        """
        An entry with the post verb, object type attachment, with picture.
        """
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
    <link xmlns="http://www.w3.org/2005/Atom" rel="enclosure" href="http://fast.mediamatic.nl/f/sjnh/image/403/167544-600-375.jpg"/>
    <link xmlns="http://www.w3.org/2005/Atom" rel="figure" href="http://www.mediamatic.net/figure/167544"/>
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
        self.assertEquals(u'http://www.mediamatic.net/figure/167544?width=480',
                          notification['picture'])


    def test_formatPayloadPostAttachmentNoPicture(self):
        """
        An entry with the post verb, object type attachment, without picture.
        """
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
        self.assertNotIn('picture', notification)


    def test_formatPayloadPostAgent(self):
        """
        An entry with the post verb, object type attachment, with picture.
        """
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
    <link xmlns="http://www.w3.org/2005/Atom" rel="enclosure" href="http://fast.mediamatic.nl/f/sjnh/image/403/167544-600-375.jpg"/>
    <link xmlns="http://www.w3.org/2005/Atom" rel="figure" href="http://www.mediamatic.net/figure/167544"/>
  </object>
  <author>
    <id>http://www.mediamatic.net/id/28344</id>
    <uri>http://www.mediamatic.net/id/28344</uri>
    <name>anyMeta Cyborg</name>
    <object-type xmlns="http://activitystrea.ms/spec/1.0/">http://mediamatic.nl/ns/anymeta/2008/kind/person</object-type>
  </author>
  <agent xmlns='http://mediamatic.nl/ns/anymeta/'>
    <id xmlns='http://www.w3.org/2005/Atom'>http://www.mediamatic.net/id/28344</id>
    <object-type xmlns='http://activitystrea.ms/spec/1.0/'>http://mediamatic.nl/ns/anymeta/2008/kind/person</object-type>
    <title xmlns='http://www.w3.org/2005/Atom'>anyMeta Cyborg</title>
    <link rel='alternate' href='http://www.mediamatic.net/id/28344' xmlns='http://www.w3.org/2005/Atom'/>
    <link rel='enclosure' href='http://fast.mediamatic.nl/f/sjnh/image/456/29055-480-360.jpg' xmlns='http://www.w3.org/2005/Atom'/>
    <link rel='figure' href='http://www.mediamatic.net/figure/28344' xmlns='http://www.w3.org/2005/Atom'/>
  </agent>
</entry>"""

        notification = formatPayload(self.source, xml)
        self.assertIdentical(None, notification)


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


    def test_formatPayloadRFID(self):
        """
        An entry with an RFID (ikTag) verb.
        """
        xml = """
<entry xmlns="http://www.w3.org/2005/Atom">
  <published>2010-12-22T19:23:04+01:00</published>
  <updated>2010-12-22T19:23:04+01:00</updated>
  <id>http://www.mediamatic.net/activity/40313</id>
  <title type="html">Ralph Meijer connected an ikTag to his/her account. </title>
  <link rel="alternate" type="text/html" href="http://www.mediamatic.net/id/24879"/>
  <verb xmlns="http://activitystrea.ms/spec/1.0/">http://mediamatic.nl/ns/anymeta/2010/activitystreams/iktag</verb>
  <object xmlns="http://activitystrea.ms/spec/1.0/">
    <id xmlns="http://www.w3.org/2005/Atom">http://www.mediamatic.net/id/24879</id>
    <object-type>http://mediamatic.nl/ns/anymeta/2008/kind/person</object-type>
    <title xmlns="http://www.w3.org/2005/Atom">Ralph Meijer</title>
    <link xmlns="http://www.w3.org/2005/Atom" rel="alternate" href="http://www.mediamatic.net/id/24879"/>
    <link xmlns="http://www.w3.org/2005/Atom" rel="enclosure" href="http://fast.mediamatic.nl/f/sjnh/image/914/24881-360-480.jpg"/>
    <link xmlns="http://www.w3.org/2005/Atom" rel="figure" href="http://www.mediamatic.net/figure/24879"/>
  </object>
  <author>
    <id>http://www.mediamatic.net/id/24879</id>
    <object-type xmlns="http://activitystrea.ms/spec/1.0/">http://mediamatic.nl/ns/anymeta/2008/kind/person</object-type>
    <title>Ralph Meijer</title>
    <link rel="alternate" href="http://www.mediamatic.net/id/24879"/>
    <link rel="enclosure" href="http://fast.mediamatic.nl/f/sjnh/image/914/24881-360-480.jpg"/>
    <link rel="figure" href="http://www.mediamatic.net/figure/24879"/>
    <name>Ralph Meijer</name>
    <uri>http://www.mediamatic.net/id/24879</uri>
  </author>
</entry>"""

        notification = formatPayload(self.source, xml)
        self.assertEquals(u'Ralph Meijer', notification['title'])
        self.assertEquals(u'linked an ikTag', notification['subtitle'])


    def test_getNodeSite(self):
        """
        A ActivityStreamSource for a site listens to the 'activity' node.
        """
        service, nodeIdentifier = self.source.getNode()
        self.assertEqual('dwaal.local', service.full())
        self.assertEqual('activity', nodeIdentifier)



class WoWSourceTest(unittest.TestCase, PubSubSourceTests):
    """
    Tests for L{ikdisplay.source.WoWSource}.
    """

    def setUp(self):
        agent = source.Thing(uri=u'http://www.mediamatic.net/id/28344')
        self.source = source.WoWSource(agent=agent)


    def test_formatPayloadPostAgent(self):
        """
        An entry with the post verb, object type attachment, with picture.
        """
        xml = """
<entry xmlns="http://www.w3.org/2005/Atom"> <published>2010-11-19T12:16:18+01:00</published>
  <updated>2010-11-19T12:16:18+01:00</updated>
  <id>http://www.mediamatic.net/activity/1053</id>
  <title type="html">anyMeta Cyborg created Evelyn, Simon, Axel at Dev Camp \xe2\x80\x9910 \xe2\x80\x94 IkSentric.</title>
  <link href="http://www.mediamatic.net/id/167544" type="text/html" rel="alternate"/>
  <verb xmlns="http://activitystrea.ms/spec/1.0/">http://activitystrea.ms/schema/1.0/post</verb>
  <object xmlns="http://activitystrea.ms/spec/1.0/">
    <id xmlns="http://www.w3.org/2005/Atom">http://www.mediamatic.net/id/167544</id>
    <title xmlns="http://www.w3.org/2005/Atom">Evelyn, Simon, Axel at Dev Camp \xe2\x80\x9910 \xe2\x80\x94 IkSentric</title>
    <object-type>http://mediamatic.nl/ns/anymeta/2008/kind/attachment</object-type>
    <link xmlns="http://www.w3.org/2005/Atom" rel="enclosure" href="http://fast.mediamatic.nl/f/sjnh/image/403/167544-600-375.jpg"/>
    <link xmlns="http://www.w3.org/2005/Atom" rel="figure" href="http://www.mediamatic.net/figure/167544"/>
  </object>
  <author>
    <id>http://www.mediamatic.net/id/28344</id>
    <uri>http://www.mediamatic.net/id/28344</uri>
    <name>anyMeta Cyborg</name>
    <object-type xmlns="http://activitystrea.ms/spec/1.0/">http://mediamatic.nl/ns/anymeta/2008/kind/person</object-type>
  </author>
  <agent xmlns='http://mediamatic.nl/ns/anymeta/'>
    <id xmlns='http://www.w3.org/2005/Atom'>http://www.mediamatic.net/id/28344</id>
    <object-type xmlns='http://activitystrea.ms/spec/1.0/'>http://mediamatic.nl/ns/anymeta/2008/kind/person</object-type>
    <title xmlns='http://www.w3.org/2005/Atom'>anyMeta Cyborg</title>
    <link rel='alternate' href='http://www.mediamatic.net/id/28344' xmlns='http://www.w3.org/2005/Atom'/>
    <link rel='enclosure' href='http://fast.mediamatic.nl/f/sjnh/image/456/29055-480-360.jpg' xmlns='http://www.w3.org/2005/Atom'/>
    <link rel='figure' href='http://www.mediamatic.net/figure/28344' xmlns='http://www.w3.org/2005/Atom'/>
  </agent>
</entry>"""

        notification = formatPayload(self.source, xml)
        self.assertNotIdentical(None, notification)


    def test_formatPayloadPostNoAgent(self):
        """
        An entry with the post verb, object type attachment, with picture.
        """
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
    <link xmlns="http://www.w3.org/2005/Atom" rel="enclosure" href="http://fast.mediamatic.nl/f/sjnh/image/403/167544-600-375.jpg"/>
    <link xmlns="http://www.w3.org/2005/Atom" rel="figure" href="http://www.mediamatic.net/figure/167544"/>
  </object>
  <author>
    <id>http://www.mediamatic.net/id/28344</id>
    <uri>http://www.mediamatic.net/id/28344</uri>
    <name>anyMeta Cyborg</name>
    <object-type xmlns="http://activitystrea.ms/spec/1.0/">http://mediamatic.nl/ns/anymeta/2008/kind/person</object-type>
  </author>
</entry>"""

        notification = formatPayload(self.source, xml)
        self.assertIdentical(None, notification)


    def test_formatPayloadPostOtherAgent(self):
        """
        An entry with the post verb, object type attachment, with picture.
        """
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
    <link xmlns="http://www.w3.org/2005/Atom" rel="enclosure" href="http://fast.mediamatic.nl/f/sjnh/image/403/167544-600-375.jpg"/>
    <link xmlns="http://www.w3.org/2005/Atom" rel="figure" href="http://www.mediamatic.net/figure/167544"/>
  </object>
  <author>
    <id>http://www.mediamatic.net/id/28344</id>
    <uri>http://www.mediamatic.net/id/28344</uri>
    <name>anyMeta Cyborg</name>
    <object-type xmlns="http://activitystrea.ms/spec/1.0/">http://mediamatic.nl/ns/anymeta/2008/kind/person</object-type>
  </author>
  <agent xmlns='http://mediamatic.nl/ns/anymeta/'>
    <id xmlns='http://www.w3.org/2005/Atom'>http://www.mediamatic.net/id/28345</id>
  </agent>
</entry>"""

        notification = formatPayload(self.source, xml)
        self.assertIdentical(None, notification)



class CheckinsSourceTest(unittest.TestCase, PubSubSourceTests):
    """
    Tests for L{ikdisplay.source.CheckinsSource}.
    """

    def setUp(self):
        site = source.Site(uri=u'http://ixion.local/')
        self.source = source.CheckinsSource(site=site)


    def test_formatPayloadCheckin(self):
        """
        A checkin entry
        """
        xml = """
        <entry xmlns="http://www.w3.org/2005/Atom">
          <published>2011-05-06T15:41:08+02:00</published>
          <updated>2011-05-06T15:41:08+02:00</updated>
          <id>http://ixion.local/activity/1541</id>
          <title type="html">&lt;a href="http://ixion.local/person/964/nl"&gt;Arjan van der Wal&lt;/a&gt; was bij &lt;a href="http://ixion.local/page/113/nl"&gt;Amsterdam&lt;/a&gt;.</title>
          <link href="http://ixion.local/page/113/nl" type="text/html" rel="alternate"/>
          <verb xmlns="http://activitystrea.ms/spec/1.0/">http://activitystrea.ms/schema/1.0/checkin</verb>
          <object xmlns="http://activitystrea.ms/spec/1.0/">
            <id xmlns="http://www.w3.org/2005/Atom">http://ixion.local/id/113</id>
            <object-type>http://mediamatic.nl/ns/anymeta/2008/kind/location</object-type>
            <title xmlns="http://www.w3.org/2005/Atom">Amsterdam</title>
            <link xmlns="http://www.w3.org/2005/Atom" href="http://ixion.local/page/113/nl" rel="alternate"/>
          </object>
          <target xmlns="http://activitystrea.ms/spec/1.0/">
            <id xmlns="http://www.w3.org/2005/Atom">http://ixion.local/id/964</id>
            <object-type>http://mediamatic.nl/ns/anymeta/2008/kind/person</object-type>
            <title xmlns="http://www.w3.org/2005/Atom">Arjan van der Wal</title>
            <link xmlns="http://www.w3.org/2005/Atom" href="http://ixion.local/person/964/nl" rel="alternate"/>
            <link xmlns="http://www.w3.org/2005/Atom" href="http://ixion.local/image/570/965-200-200.jpg" rel="enclosure"/>
            <link xmlns="http://www.w3.org/2005/Atom" href="http://ixion.local/figure/964" rel="figure"/>
          </target>
          <author>
            <id>http://ixion.local/id/964</id>
            <object-type xmlns="http://activitystrea.ms/spec/1.0/">http://mediamatic.nl/ns/anymeta/2008/kind/person</object-type>
            <link href="http://ixion.local/person/964/nl" rel="alternate"/>
            <link href="http://ixion.local/image/570/965-200-200.jpg" rel="enclosure"/>
            <link href="http://ixion.local/figure/964" rel="figure"/>
            <name>Arjan van der Wal</name>
            <uri>http://ixion.local/person/964/nl</uri>
          </author>
          <agent xmlns="http://mediamatic.nl/ns/anymeta/">
            <id xmlns="http://www.w3.org/2005/Atom">http://ixion.local/id/1</id>
            <object-type xmlns="http://activitystrea.ms/spec/1.0/">http://mediamatic.nl/ns/anymeta/2008/kind/person</object-type>
            <title xmlns="http://www.w3.org/2005/Atom"/>
            <link xmlns="http://www.w3.org/2005/Atom" href="http://ixion.local/id/1" rel="alternate"/>
          </agent>
        </entry>"""
        notification = formatPayload(self.source, xml)
        self.assertEquals(u'Arjan van der Wal', notification['title'])
        self.assertEquals(u'was at Amsterdam', notification['subtitle'])
