from twisted.trial import unittest

from wokkel.generic import parseXml
from wokkel import pubsub

from ikdisplay import aggregator, source

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


class VoteSourceTest(unittest.TestCase):

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

        thing = aggregator.Thing(uri=u'http://www.mediamatic.net/id/160225')
        src = source.VoteSource(question=thing)
        notification = formatPayload(src, xml)

        self.assertEquals(u'Fred Pook',
                          notification['title'])
        self.assertEquals(u'voted for Shadow Search Platform',
                          notification['subtitle'])



class PresenceSourceTest(unittest.TestCase):

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

        thing = aggregator.Thing(uri=u'http://www.mediamatic.net/id/160225')
        src = source.PresenceSource(question=thing)
        notification = formatPayload(src, xml)

        self.assertEquals(u'Fred Pook',
                          notification['title'])
        self.assertEquals(u'was at the entrance',
                          notification['subtitle'])


class IkMicSourceTest(unittest.TestCase):

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

        thing = aggregator.Thing(uri=u'http://www.mediamatic.net/id/160225')
        src = source.IkMicSource(question=thing)
        notification = formatPayload(src, xml)

        self.assertEquals(u'Fred Pook',
                          notification['title'])
        self.assertIn(notification['subtitle'],
                      source.IkMicSource.TEXTS_EN['interrupt'])


class StatusSourceTest(unittest.TestCase):

    def formatPayload(self, xml):
        thing = aggregator.Site(uri=u'http://www.mediamatic.net/')
        src = source.StatusSource(site=thing)
        return formatPayload(src, xml)


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

        notification = self.formatPayload(xml)
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

        notification = self.formatPayload(xml)
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

        notification = self.formatPayload(xml)
        self.assertIdentical(None, notification)
