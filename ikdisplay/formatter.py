import random
import re

from twisted.application import service
from twisted.python import log
from twisted.python import reflect
from twisted.words.xish import domish

from wokkel.generic import parseXml

NS_ATOM = 'http://www.w3.org/2005/Atom'

class PubSubItemsFormatter(service.Service):
    """

    @ivar texts: Contains the texts from this class and all the base classes,
        for the language set in the config.
    @type texts: C{dict}
    """

    TEXTS_NL = {
            'via_template': u'via %s',
            'alien': u'Een illegale alien',
            }
    TEXTS_EN = {
            'via_template': u'via %s',
            'alien': u'An illegal alien',
            }

    pubsubClient = None

    def __init__(self, callback, config):
        self.callback = callback
        self.config = config

        self.texts = {}
        attr = 'TEXTS_' + self.config['language'].upper()
        reflect.accumulateClassDict(self.__class__, attr, self.texts)


    def startService(self):
        service.Service.startService(self)
        self.pubsubClient.addObserver(self.itemsReceived,
                                      self.config['service'],
                                      self.config['node'])


    def stopService(self):
        service.Service.stopService(self)
        self.pubsubClient.removeObserver(self.itemsReceived,
                                         self.config['service'],
                                         self.config['node'])


    def itemsReceived(self, event):
        notifications = self.format(event)
        if self.running:
            self.callback(notifications)


    def format(self, event):
        notifications = []

        for item in event.items:
            try:
                element = item.elements().next()
            except (StopIteration):
                continue

            notification = self.format_payload(element)

            if notification:
                via = self.config.get('via', self.texts.get('via'))
                if via is not None:
                    notification['meta'] = self.texts['via_template'] % via
                notifications.append(notification)
            else:
                log.msg("Formatter returned None. Dropping.")

        return notifications


    def format_payload(self, payload):
        raise NotImplementedError()



class SimpleFormatter(PubSubItemsFormatter):
    def format_payload(self, payload):
        elementMap = {'title': 'title',
                      'subtitle': 'subtitle',
                      'image': 'icon',
                      }

        notification = {}
        for child in payload.elements():
            if child.name in elementMap:
                notification[elementMap[child.name]] = unicode(child)

        return notification



class VoteFormatter(PubSubItemsFormatter):
    TEXTS_NL = {
            'via': 'ikPoll',
            'voted': u'stemde op %s',
            }
    TEXTS_EN = {
            'via': 'ikPoll',
            'voted': u'voted for %s',
            }

    def _voteToName(self, vote):
        title = unicode(vote.person.title)
        if title:
            prefix = vote.person.prefix and (unicode(vote.person.prefix) + " ") or ""
            return prefix + title
        else:
            return None


    def _voteToAnswer(self, vote):
        answerID = unicode(vote.vote.answer_id_ref)
        for element in vote.question.answers.elements():
            if ((element.uri, element.name) == ('', 'item') and
                unicode(element.answer_id) == answerID):
                    return unicode(element.title)

        return None


    def format_payload(self, payload):
        title = self._voteToName(payload)
        answer = self._voteToAnswer(payload)

        if not title:
            title = self.texts['alien']

        template = self.config.get('template', self.texts['voted'])
        subtitle = template % answer

        notification = {
                'title': title,
                'subtitle': subtitle,
                'icon': unicode(payload.person.image),
                }

        notification.update(self.format_vote(payload))

        return notification


    def format_vote(self, payload):
        """
        Augment default formatting for special types of votes.
        """
        return {}



class PresenceFormatter(VoteFormatter):
    """
    Formatter for doorman via ikPoll.
    """

    TEXTS_NL = {
            'present': u'is bij de ingang gesignaleerd',
            'alien_present': u'is bij de ingang tegengehouden',
            }
    TEXTS_EN = {
            'present': u'was at the entrance',
            'alien_present': u'has been detained at the entrance',
            }

    def format_vote(self, payload):
        if unicode(payload.person.title):
            subtitle = self.texts['present']
        else:
            subtitle = self.texts['alien_present']

        return {"subtitle": subtitle}



class InterruptFormatter(VoteFormatter):
    """
    Formatter for interruption mic via ikPoll.
    """

    TEXTS_NL = {
            'via': 'ikMic',
            'interrupt': [u'wil iets zeggen',
                          u'heeft een opmerking',
                          u'interrumpeert',
                          u'onderbreekt de discussie'],
            }
    TEXTS_EN = {
            'via': 'ikMic',
            'interrupt': [u'has something to say',
                          u'has a remark',
                          u'is speaking'],
            }

    def format_vote(self, payload):
        return {"subtitle": random.choice(self.texts['interrupt'])}



class StatusFormatter(PubSubItemsFormatter):
    """
    Formatter for anyMeta statuses.
    """

    def format_payload(self, payload):
        text = unicode(payload.status).strip()
        if not text or text == 'is':
            return None

        return {'title': unicode(payload.person.title),
                'subtitle': text,
                'icon': unicode(payload.person.image)}



class AtomEntryFormatter(PubSubItemsFormatter):
    """
    Formatter for Atom Entry documents.
    """
    def format_payload(self, payload, nodeInfo):
        import feedparser

        data = feedparser.parse(payload.toXml().encode('utf-8'))
        if not 'entries' in data:
            return None

        notification = {}
        entry = data.entries[0]

        if not 'title' in entry:
            return None
        else:
            notification['subtitle'] = entry.title

        if 'author' in entry:
            notification['title'] = entry.author
        elif 'source' in entry and 'author' in entry.source:
            notification['title'] = entry.source.author
        else:
            notification['title'] = u''

        if 'link' in entry:
            notification['link'] = entry.link

        if 'source' in entry and 'icon' in entry.source:
            notification['icon'] = entry.source.icon

        return notification



class TwitterStatusFormatter(PubSubItemsFormatter):
    """
    Formatter for Twitter statuses.
    """

    def format_payload(self, payload):
        text = unicode(payload.text)

        if ('terms' not in self.config and
            'userIDs' not in self.config):
            match = True
        else:
            match = False

            for term in self.config.get('terms', ()):
                if re.search(term, text, re.IGNORECASE):
                    match = True

            if 'userIDs' in self.config:
                userID = unicode(payload.user.id)
                match = match or (userID in self.config['userIDs'])

        if match:
            return {'title': unicode(payload.user.screen_name),
                    'subtitle': text,
                    'icon': unicode(payload.user.profile_image_url),
                    }



class IkCamFormatter(PubSubItemsFormatter):
    """
    Formatter for ikCam.
    """
    TEXTS_NL = {
            'via': 'ikCam',
            'ikcam_picture_singular': u'ging op de foto',
            'ikcam_picture_plural': u'gingen op de foto',
            'ikcam_event': u' bij %s',
            }
    TEXTS_EN = {
            'via': 'ikCam',
            'ikcam_picture_singular': u'took a self-portrait',
            'ikcam_picture_plural': u'took a group portrait',
            'ikcam_event': u' at %s',
            }

    def format_payload(self, payload):

        participants = [unicode(element)
                        for element in payload.participants.elements()
                        if element.name == 'participant']

        if not participants:
            return
        elif len(participants) == 1:
            subtitle = self.texts['ikcam_picture_singular']
        else:
            subtitle = self.texts['ikcam_picture_plural']

        if payload.event:
            subtitle += self.texts['ikcam_event'] % unicode(payload.event.title)

        pictureElement = payload.picture.attachment_uri or payload.picture.rsc_uri

        return {'title': u', '.join(participants),
                'subtitle': subtitle,
                'icon': u'http://docs.mediamatic.nl/images/ikcam-80x80.png',
                'picture': unicode(pictureElement),
                }



class RegDeskFormatter(PubSubItemsFormatter):
    TEXTS_NL = {
            'via': 'Registratiebalie',
            'regdesk': [u'is binnen',
                        u'is er nu ook',
                        u'is net binnengekomen',
                        u'is gearriveerd'],
            }
    TEXTS_EN = {
            'via': 'Registration Desk',
            'regdesk': [u'just arrived',
                        u'showed up at the entrance',
                        u'received a badge',
                        u'has entered the building',
                        ],
            }

    def format_payload(self, payload):
        subtitle = random.choice(self.texts['regdesk'])

        if payload.person:
            return {'title': unicode(payload.person.title),
                    'subtitle': subtitle,
                    'icon': unicode(payload.person.image),
                    }



class IkBelFormatter(PubSubItemsFormatter):
    TEXTS_NL = {
            'via': 'ikBel',
            'ikbel': u'sprak net met %s',
            }
    TEXTS_EN = {
            'via': 'ikBel',
            'ikbel': u'just talked to %s',
            }

    def format_payload(self, payload):
        subtitle = self.texts["ikbel"] % payload.person2.title

        if payload.person1:
            return {'title': unicode(payload.person1.title),
                    'subtitle': subtitle,
                    'icon': unicode(payload.person1.image),
                    }



class RaceFormatter(PubSubItemsFormatter):
    """
    Formatter for Races.
    """
    TEXTS_NL = {
            'via': 'Alleycat',
            'race_finish': u'finishte de %s in %s.',
            }
    TEXTS_EN = {
            'via': 'Alleycat',
            'race_finish': u'finished the %s in %s.',
            }

    def format_payload(self, payload):
        subtitle = self.texts['race_finish'] % (unicode(payload.event),
                                                unicode(payload.time))

        return {'title': unicode(payload.person.title),
                'subtitle': subtitle,
                'icon': unicode(payload.person.image)}



class FlickrFormatter(PubSubItemsFormatter):
    """
    Formatter for Flickr feeds.

    This groups pictures per author and then creates one notification
    per author.
    """

    TEXTS_NL = {
            'via': 'Flickr',
            'flickr_upload': u'plaatste een plaatje',
            'flickr_more': u' (en nog %d meer)',
            }
    TEXTS_EN = {
            'via': 'Flickr',
            'flickr_upload': u'posted a picture',
            'flickr_more': u' (and %d more)',
            }

    def format(self, event):
        import feedparser

        elements = (item.entry for item in event.items
                               if item.entry and item.entry.uri == NS_ATOM)

        feedDocument = domish.Element((NS_ATOM, 'feed'))
        for element in elements:
            feedDocument.addChild(element)

        feed = feedparser.parse(feedDocument.toXml().encode('utf-8'))
        entries = feed.entries

        entriesByAuthor = {}
        for entry in entries:
            if not hasattr(entry, 'enclosures'):
                return

            author = getattr(entry, 'author', None) or self.texts['alien']
            entriesByAuthor.setdefault(author, {'entry': entry, 'count': 0})
            entriesByAuthor[author]['count'] += 1

        notifications = []
        for author, value in entriesByAuthor.iteritems():
            entry = value['entry']
            count = value['count']

            subtitle = self.texts['flickr_upload']
            if count > 1:
                subtitle += self.texts['flickr_more'] % (count - 1,)

            content = entry.content[0].value.encode('utf-8')
            parsedContent = parseXml(content)
            print parsedContent.toXml()

            uri = None

            for element in parsedContent.elements():
                if element.a and element.a.img:
                    uri = element.a.img['src']

            if uri:
                ext = uri.rsplit('.', 1)[1]
                uriParts = uri.split('_')
                uri = u'%s.%s' % (u'_'.join(uriParts[:-1]), ext)

            notification = {'title': author,
                            'subtitle': subtitle,
                            'meta': u"via %s" % self.config['via'],
                            'picture': uri,
                            }
            notifications.append(notification)

        return notifications



class FormatterFactory(object):

    formatters = {
            'simple': SimpleFormatter,
            'vote': VoteFormatter,
            'presence': PresenceFormatter,
            'interrupt': InterruptFormatter,
            'status': StatusFormatter,
            'atom': AtomEntryFormatter,
            'twitter': TwitterStatusFormatter,
            'ikcam': IkCamFormatter,
            'regdesk': RegDeskFormatter,
            'ikbel': IkBelFormatter,
            'race': RaceFormatter,
            'flickr': FlickrFormatter,
            }

    def __init__(self, pubsubClient):
        self.pubsubClient = pubsubClient


    def buildFormatter(self, source, callback):
        formatter = self.formatters[source['type']](callback, source)

        if hasattr(formatter, 'pubsubClient'):
            formatter.pubsubClient = self.pubsubClient

        return formatter
