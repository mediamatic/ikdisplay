# -*- test-case-name: ikdisplay.test.test_source -*-

import re
import random

from zope.interface import Attribute, Interface, implements

from twisted.python import log, reflect
from twisted.web import client

from axiom import attributes, item

from ikdisplay.xmpp import IPubSubEventProcessor, JIDAttribute, getPubSubService

class ISource(Interface):
    """
    A feed source.
    """

    feed = Attribute("""Reference to the feed this source belongs to""")
    enabled = Attribute("""Enabled state.""")
    via = Attribute("""Optional text for the 'via' field of a notification.""")

    def renderTitle():
        """
        Renders a title for display in the configuration.
        """



class SourceMixin(object):
    implements(ISource)

    title = "Unknown source"

    def installOn(self, other):
        self.feed = other
        other.powerUp(self, ISource)


    def renderTitle(self):
        return self.title


    def changeAttributes(self, attributes):
        [setattr(item, k, v) for k,v in attributes.iteritems()]



class PubSubSourceMixin(SourceMixin):
    """

    @ivar texts: Contains the texts from this class and all the base classes,
        for the language set in the config.
    @type texts: C{dict}
    """
    implements(IPubSubEventProcessor)

    TEXTS_NL = {
            'via_template': u'via %s',
            'alien': u'Een illegale alien',
            }
    TEXTS_EN = {
            'via_template': u'via %s',
            'alien': u'An illegal alien',
            }

    texts = None

    pubsubClient = None

    def activate(self):
        if self.texts is None:
            self.__class__.texts = {}

            for language in ('nl', 'en'):
                texts = self.__class__.texts[language] = {}
                attr = 'TEXTS_' + language.upper()
                reflect.accumulateClassDict(self.__class__, attr, texts)


    def installOnSubscription(self, other):
        self.subscription = other
        other.powerUp(self, IPubSubEventProcessor)


    def uninstallFromSubscription(self, other):
        other.powerDown(self, IPubSubEventProcessor)
        self.subscription = None


    def itemsReceived(self, event):
        notifications = self.format(event)
        self.feed.processNotifications(notifications)


    def getNode(self):
        raise NotImplementedError()


    def format(self, event):
        notifications = []

        for item in event.items:
            try:
                element = item.elements().next()
            except (StopIteration):
                continue

            notification = self.format_payload(element)

            if notification:
                texts = self.texts[self.feed.language]
                via = self.via or texts.get('via')
                if via is not None:
                    notification['meta'] = texts['via_template'] % via
                notifications.append(notification)
            else:
                log.msg("Formatter returned None. Dropping.")

        return notifications


    def format_payload(self, payload):
        raise NotImplementedError()



class Site(item.Item):
    title = attributes.text()
    uri = attributes.text(allowNone=False)



def getThingID(uri):
    from urlparse import urlparse

    path = urlparse(uri).path
    match = re.match(r'^/id/(\d+)$', path)
    return match.group(1)



class Thing(item.Item):
    title = attributes.text()
    uri = attributes.text(allowNone=False)


    def discoverCreate(cls, store, uri):
        """ Perform discovery on the URL to get the title, and then create a thing. """
        d = client.getPage(uri)
        def parsePage(content):
            from lxml.html.soupparser import fromstring
            tree = fromstring(content)
            h1 = tree.find(".//h1")
            title = unicode((h1 is not None and h1.text) or "?")
            slf = tree.find(".//link[@rel=\"self\"]")
            newuri = unicode((slf is not None and slf.attrib["href"]) or uri)
            return Thing(store=store, uri=newuri, title=title)
        d.addCallback(parsePage)
        return d
    discoverCreate = classmethod(discoverCreate)


    def getID(self):
        """
        Return the id of this thing.
        """
        return int(self.uri.split("/")[-1])




class SimpleSource(PubSubSourceMixin, item.Item):
    title = "Simple source"

    feed = attributes.reference()
    enabled = attributes.boolean()
    via = attributes.text()
    subscription = attributes.reference()
    service = JIDAttribute()
    nodeIdentifier = attributes.text()

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


    def getNode(self):
        return (self.service, self.nodeIdentifier)


    def renderTitle(self):
        return "%s (via: %s)" % (self.title, self.via)



class VoteSourceMixin(PubSubSourceMixin):
    TEXTS_NL = {
            'via': 'ikPoll',
            'voted': u'stemde op %s',
            }
    TEXTS_EN = {
            'via': 'ikPoll',
            'voted': u'voted for %s',
            }

    def renderTitle(self):
        return "%s on %s" % (self.title, (self.question and self.question.title) or "?")

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

        template = getattr(self, 'template', None) or self.texts[self.feed.language]['voted']
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


class VoteSource(VoteSourceMixin, item.Item):
    title = "Vote"

    feed = attributes.reference()
    enabled = attributes.boolean()
    via = attributes.text()
    subscription = attributes.reference()
    question = attributes.reference()
    template = attributes.text()

    def renderTitle(self):
        return "%s, question: %s" % (self.title, (self.question and self.question.title) or "?")


class PresenceSource(VoteSourceMixin, item.Item):
    title = "Presence"

    feed = attributes.reference()
    enabled = attributes.boolean()
    via = attributes.text()
    subscription = attributes.reference()
    question = attributes.reference()

    TEXTS_NL = {
            'present': u'is bij de ingang gesignaleerd',
            'alien_present': u'is bij de ingang tegengehouden',
            }
    TEXTS_EN = {
            'present': u'was at the entrance',
            'alien_present': u'has been detained at the entrance',
            }

    def format_vote(self, payload):
        texts = self.texts[self.feed.language]
        if unicode(payload.person.title):
            subtitle = texts['present']
        else:
            subtitle = texts['alien_present']

        return {"subtitle": subtitle}



class IkMicSource(VoteSourceMixin, item.Item):
    title = "IkMic"

    feed = attributes.reference()
    enabled = attributes.boolean()
    via = attributes.text()
    subscription = attributes.reference()
    question = attributes.reference()

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
        choices = self.texts[self.feed.language]['interrupt']
        return {"subtitle": random.choice(choices)}


    def renderTitle(self):
        return "%s, question: %s" % (self.title, (self.question and self.question.title) or "?")




class StatusSource(PubSubSourceMixin, item.Item):
    title = "Status updates"

    feed = attributes.reference()
    enabled = attributes.boolean()
    via = attributes.text()
    subscription = attributes.reference()
    site = attributes.reference("""
    Reference to the site the statuses come from.
    """)
    event = attributes.reference("""
    Reference to the event the things the statuses are from are participant of.
    """)
    user = attributes.reference("""
    Reference to the thing the statuses are from.
    """)

    def format_payload(self, payload):
        text = unicode(payload.status).strip()
        if not text or text == 'is':
            return None

        return {'title': unicode(payload.person.title),
                'subtitle': text,
                'icon': unicode(payload.person.image)}


    def getNode(self):
        if self.site is not None:
            return (getPubSubService(self.site.uri), u'status')


    def renderTitle(self):
        s = "%s from %s" % (self.title, (self.site and self.site.title) or "?")
        if self.event:
            s += " (event: %s)" % self.event.title
        if self.user:
            s += " (user: %s)" % self.event.title
        return s


class TwitterSource(SourceMixin, item.Item):
    title = "Twitter"

    feed = attributes.reference()
    enabled = attributes.boolean()
    via = attributes.text()
    terms = attributes.textlist()
    userIDs = attributes.textlist()

    def onEntry(self, entry):
        notification = self.format(entry)
        if notification:
            self.feed.processNotifications([notification])


    def format(self, status):
        if (not self.terms and
            not self.userIDs):
            match = True
        else:
            match = False

            for term in self.terms:
                if re.search(term, status.text, re.IGNORECASE):
                    match = True

            if self.userIDs:
                userID = status.user.id
                match = match or (userID in self.userIDs)

        if match:
            return {'title': status.user.screen_name,
                    'subtitle': status.text,
                    'icon': status.user.profile_image_url,
                    }


    def renderTitle(self):
        return "%s (%d terms, %d users)" % (self.title,
                                            len(self.terms or []),
                                            len(self.userIDs or []))



class IkCamSource(PubSubSourceMixin, item.Item):
    title = "IkCam pictures"

    feed = attributes.reference()
    enabled = attributes.boolean()
    subscription = attributes.reference()
    via = attributes.text()
    event = attributes.reference("""
    Reference to the event the pictures were taken at.
    """)
    creator = attributes.reference("""
    Reference to the creator of the pictures.
    """)

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
        texts = self.texts[self.feed.language]

        participants = [unicode(element)
                        for element in payload.participants.elements()
                        if element.name == 'participant']

        if not participants:
            return
        elif len(participants) == 1:
            subtitle = texts['ikcam_picture_singular']
        else:
            subtitle = texts['ikcam_picture_plural']

        if payload.event:
            subtitle += texts['ikcam_event'] % unicode(payload.event.title)

        pictureElement = payload.picture.attachment_uri or payload.picture.rsc_uri

        return {'title': u', '.join(participants),
                'subtitle': subtitle,
                'icon': u'http://docs.mediamatic.nl/images/ikcam-80x80.png',
                'picture': unicode(pictureElement),
                }

    def getNode(self):
        nodeIdentifier = 'ikcam/'
        if self.creator:
            service = getPubSubService(self.creator.uri)
            nodeIdentifier += getThingID(self.creator.uri)
        elif self.event:
            service = getPubSubService(self.event.uri)
            nodeIdentifier += 'by_event/' + getThingID(self.event.uri)

        return service, nodeIdentifier



    def renderTitle(self):
        s = self.title
        if self.event:
            s += " for the event " + self.event.title
        if self.creator:
            s += " created by " + self.creator.title
        return s




class RegDeskSource(PubSubSourceMixin, item.Item):
    title = "Registration desk"

    feed = attributes.reference()
    enabled = attributes.boolean()
    via = attributes.text()
    subscription = attributes.reference()
    event = attributes.reference("""
    Reference to the event.
    """)

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

    def renderTitle(self):
        return "%s for %s" % (self.title, (self.event and self.event.title) or "?")



class RaceSource(PubSubSourceMixin, item.Item):
    title = "Race events"

    feed = attributes.reference()
    enabled = attributes.boolean()
    via = attributes.text()
    subscription = attributes.reference()
    race = attributes.reference("""
    Reference to the thing representing the race.
    """)

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

    def renderTitle(self):
        return "%s for the race %s" % (self.title, (self.race and self.race.title) or "?")



NS_ACTIVITY_SCHEMA = 'http://activitystrea.ms/schema/1.0/'

class ActivityStreamSource(PubSubSourceMixin, item.Item):
    title = "Activity Stream"

    feed = attributes.reference()
    enabled = attributes.boolean()
    via = attributes.text()
    subscription = attributes.reference()
    site = attributes.reference("""
    Reference to the site representing where activities occur.
    """)
    actor = attributes.reference("""
    Reference to the thing representing the actor of the activities.
    """)

    TEXTS_NL = {
            }
    TEXTS_EN = {
            'activity_verbs': {
                NS_ACTIVITY_SCHEMA + 'post': 'posted %s',
                NS_ACTIVITY_SCHEMA + 'like': 'liked %s',
                NS_ACTIVITY_SCHEMA + 'tag': 'tagged %s in %s',
                NS_ACTIVITY_SCHEMA + 'make-friend': 'friended %s',
                NS_ACTIVITY_SCHEMA + 'update': 'updated %s',
                NS_ACTIVITY_SCHEMA + 'rsvp-yes': 'will attend %s',
                }
            }

    activitiesWithTarget = (
        NS_ACTIVITY_SCHEMA + 'tag',
        )

    def format_payload(self, payload):
        verb = unicode(payload.verb)

        try:
            template = self.texts[self.feed.language]['activity_verbs'][verb]
        except KeyError:
            return

        from twisted.words.xish.domish import generateElementsNamed
        actorTitle = unicode(generateElementsNamed(payload.author.elements(),
                                                   'name').next())

        actorURI = unicode(payload.author.uri)
        match = re.match(r'^(http://[^/]+)/id/(\d+)$', actorURI)
        if match:
            figureURI = match.expand('\1/figure/\2?width=80&height=80')
        else:
            figureURI = None

        objectTitle = unicode(payload.object.title)

        if verb in self.activitiesWithTarget:
            targetTitle = unicode(payload.target.title)
            subtitle = template % (objectTitle, targetTitle)
        else:
            subtitle = template % (objectTitle,)

        return {'title': actorTitle,
                'subtitle': subtitle,
                'icon': figureURI}


    def getNode(self):
        if self.site is not None:
            return (getPubSubService(self.site.uri), u'activity')


    def renderTitle(self):
        return "%s for %s" % (self.title, self.site.title)



allSources = [
    SimpleSource,
    VoteSource,
    PresenceSource,
    IkMicSource,
    StatusSource,
    TwitterSource,
    IkCamSource,
    RegDeskSource,
    RaceSource
    ]
"""
The global list of all sources.
"""
