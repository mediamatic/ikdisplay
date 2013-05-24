# -*- test-case-name: ikdisplay.test.test_source -*-

"""
Feed Sources.

A Feed Source is a source of events or notifications, typically received via a
publish-subscribe mechanism that are converted into a common format to be
aggregated into a feed. A feed is composed of one or more sources.
"""

from itertools import permutations
import locale
import re
import random
import time

from zope.interface import Attribute, Interface, implements

from twisted.python import log, reflect
from twisted.web import client
from twisted.words.xish.domish import escapeToXml

from axiom import attributes, item

from ikdisplay.xmpp import IPubSubEventProcessor, JIDAttribute, getPubSubService

NS_ACTIVITY_SPEC = 'http://activitystrea.ms/spec/1.0/'
NS_ACTIVITY_SCHEMA = 'http://activitystrea.ms/schema/1.0/'
NS_ANYMETA_ACTIVITY = 'http://mediamatic.nl/ns/anymeta/2010/activitystreams/'
NS_ATOM = 'http://www.w3.org/2005/Atom'

TYPE_ATTACHMENT = 'http://mediamatic.nl/ns/anymeta/2008/kind/attachment'
ACTIVITY_COMMIT = 'http://mediamatic.nl/ns/schema/2010/verb/commit'

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
    """
    Common code for all sources.

    As axiom does not support attributes on superclasses, this mixin only
    provides the code part of the common features of sources. Each source
    implementation must still provide the (axiom) attributes required by
    L{ISource}.

    @ivar texts: Contains the texts from this class and all the base classes,
        for the language set in the config.
    @type texts: C{dict}
    """

    implements(ISource)

    title = "Unknown source"

    TEXTS_NL = {
            'locale': 'nl_NL.UTF-8',
            'time_format': '%-d %b, %-H:%M',
            'via_template': u'via %s',
            }
    TEXTS_EN = {
            'locale': 'en_GB.UTF-8',
            'time_format': '%b %-d, %-H:%M',
            'via_template': u'via %s',
            }

    texts = None

    def installOn(self, other):
        self.feed = other
        other.powerUp(self, ISource)


    def renderTitle(self):
        return self.title


    def changeAttributes(self, attributes):
        [setattr(item, k, v) for k,v in attributes.iteritems()]


    def activate(self):
        """
        When a source appears in memory, set up the text labels for its class.
        """
        if self.texts is None:
            self.__class__.texts = {}

            for language in ('nl', 'en'):
                texts = self.__class__.texts[language] = {}
                attr = 'TEXTS_' + language.upper()
                reflect.accumulateClassDict(self.__class__, attr, texts)


    def getTime(self, notification):
        """
        Render the timestamp of a notification, using the feed's language.
        """
        texts = self.texts[self.feed.language]

        # Set time in localized format
        oldLocale = locale.getlocale(locale.LC_ALL)
        if oldLocale == (None, None):
            oldLocale = 'C'
        else:
            oldLocale = '.'.join(oldLocale)
        locale.setlocale(locale.LC_ALL, texts['locale'])
        timeStr = time.strftime(texts['time_format'])
        locale.setlocale(locale.LC_ALL, oldLocale)

        return timeStr

    def _addVia(self, notification):
        """
        Set notification metadata to a timestamp and via text.
        """
        texts = self.texts[self.feed.language]

        meta = [self.getTime(notification)]
        via = self.via or notification.get('via', texts.get('via'))
        if via is not None:
            meta.append(texts['via_template'] % via)
        notification['meta'] = u' '.join(meta)



class PubSubSourceMixin(SourceMixin):
    """
    Common code for XMPP Publish-Subscribe sources.
    """

    implements(IPubSubEventProcessor)

    TEXTS_NL = {
            'alien': u'Een illegale alien',
            }
    TEXTS_EN = {
            'alien': u'An illegal alien',
            }

    def installOnSubscription(self, other):
        self.subscription = other
        other.powerUp(self, IPubSubEventProcessor)


    def uninstallFromSubscription(self, other):
        other.powerDown(self, IPubSubEventProcessor)
        self.subscription = None


    def itemsReceived(self, event):
        try:
            notifications = self.format(event)
            if notifications:
                self.feed.processNotifications(notifications)
        except:
            log.err()


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
                self._addVia(notification)
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

    path = urlparse(uri)[2]
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
            title = self.texts[self.feed.language]['alien']

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


    def getNode(self):
        if self.question is not None:
            return (getPubSubService(self.question.uri), unicode('vote/' + getThingID(self.question.uri)))



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

        return {
            'title': unicode(payload.person.title),
            'subtitle': text,
            'icon': unicode(payload.person.image),
            'via': self.site.title,
            }


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

    TEXTS_NL = {
            'via': 'Twitter',
            }
    TEXTS_EN = {
            'via': 'Twitter',
            }

    feed = attributes.reference()
    enabled = attributes.boolean()
    via = attributes.text()
    terms = attributes.textlist()
    userIDs = attributes.textlist()

    def onEntry(self, entry):
        notification = self.format(entry)
        if notification:
            self.feed.processNotifications([notification])


    def _gatherTexts(self, status):
        texts = []

        texts.append(status.text)

        try:
            texts.append(status.in_reply_to_screen_name or '')
        except AttributeError:
            pass

        try:
            texts.append(status.user.screen_name)
        except AttributeError:
            pass

        urls = []
        try:
            urls += status.entities.urls
        except AttributeError:
            pass
        try:
            urls += status.entities.media
        except AttributeError:
            pass

        for url in urls:
            try:
                texts.append(url.expanded_url)
            except AttributeError:
                pass

        return texts, urls


    def _matchStatus(self, status):
        texts, urls = self._gatherTexts(status)

        if (not self.terms and
            not self.userIDs):
            return True, urls

        text = ' '.join(texts)
        for term in self.terms:
            if term.startswith('"'):
                regexps = [term.strip('"')]
            else:
                words = term.split()
                regexps = ('.*'.join(permutation)
                           for permutation in permutations(words))
            for regexp in regexps:
                if re.search(regexp, text, re.IGNORECASE):
                    return True, urls

        if self.userIDs:
            userID = str(status.user.id)
            return (userID in self.userIDs), urls
        else:
            return False, urls


    def format(self, status):

        match, urls = self._matchStatus(status)

        if not match:
            return None

        notification = {
            'title': status.user.screen_name,
            'subtitle': status.text,
            'icon': status.user.profile_image_url,
            'uri': ('https://twitter.com/%s/statuses/%d' %
                    (status.user.screen_name.encode('utf-8'),
                     status.id)),
            }

        urls.sort(key=lambda url: url.indices.start, reverse=True)
        notification['html'] = notification['subtitle']
        for url in urls:
            if getattr(url, 'display_url'):
                head = notification['subtitle'][0:url.indices.start]
                tail = notification['subtitle'][url.indices.end:]
                text = u''.join([head, url.display_url, tail])
                notification['subtitle'] = text

                headHTML = notification['html'][0:url.indices.start]
                tailHTML = notification['html'][url.indices.end:]
                linkHRef = escapeToXml(url.url, isattrib=1)
                linkText = escapeToXml(url.display_url)
                link = u"<a href='%s'>%s</a>" % (linkHRef, linkText)
                html = u''.join([headHTML, link, tailHTML])
                notification['html'] = html

        if getattr(status, 'image_url', None):
            notification['picture'] = status.image_url
        self._addVia(notification)
        return notification


    def renderTitle(self):
        return "%s (%d terms, %d users)" % (self.title,
                                            len(self.terms or []),
                                            len(self.userIDs or []))




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
        subtitle = random.choice(self.texts[self.feed.language]['regdesk'])

        if payload.person:
            return {'title': unicode(payload.person.title),
                    'subtitle': subtitle,
                    'icon': unicode(payload.person.image),
                    }

    def renderTitle(self):
        return "%s for %s" % (self.title, (self.event and self.event.title) or "?")


    def getNode(self):
        if self.event is not None:
            return (getPubSubService(self.event.uri), unicode('regdesk/by_event/' + getThingID(self.event.uri)))



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
        subtitle = self.texts[self.feed.language]['race_finish'] % (unicode(payload.event),
                                                                    unicode(payload.time))

        return {'title': unicode(payload.person.title),
                'subtitle': subtitle,
                'icon': unicode(payload.person.image)}

    def renderTitle(self):
        return "%s for the race %s" % (self.title, (self.race and self.race.title) or "?")


    def getNode(self):
        if self.race is not None:
            return (getPubSubService(self.race.uri), unicode('race/' + getThingID(self.race.uri)))



class ActivityStreamSourceMixin(PubSubSourceMixin):
    """
    Common code for Activity Stream via XMPP Publish-Subscribe sources.

    The text labels under the C{'activity_verbs'} key are all templates
    where the titles of activity object and target can be used as variables.

    A subclass of this mixin will define the list of supported activity streams
    verbs it will render into notifications. Notifications with other verbs
    are dropped.

    Upon receiving a new notification, this list will be processed in order,
    checking if the verb is used in the notification. If it is, a matching text
    template is looked up in the text labels. If that label is C{None}, the
    notification will be dropped. This allows for ignoring certain verbs that
    are a subverb of a supported verb. E.g. when the status-update verb is
    derived from the post verb, but we don't want to render the status-update
    verb at all, we put the status-update verb in C{'supportedVerbs'}, but then
    assign C{None} as its text label.

    Processing of the list of supported verbs will stop at the first verb that
    is found in the notification. Notifications with verbs that derive from
    other verbs will have all the superverbs also mentioned in the
    notification. Make sure that the list of supported verbs is ordered from
    most to least specific, so that the most specific verb for a notification
    is found first.

    @ivar supportedVerbs: The verbs supported by this instance as a tuple of
        verb URIs.
    @type supportedVerbs: C{tuple}.
    """

    TEXTS_NL = {
            'activity_verbs': {
                NS_ACTIVITY_SCHEMA + 'post': 'plaatste %(object)s',
                NS_ACTIVITY_SCHEMA + 'like': u'is ge\u00efntresseerd in %(object)s',
                NS_ACTIVITY_SCHEMA + 'tag': 'wees %(object)s aan in %(target)s',
                NS_ACTIVITY_SCHEMA + 'share': 'deelde %(object)s op %(target)s',
                NS_ACTIVITY_SCHEMA + 'make-friend': 'werd vrienden met %(object)s',
                NS_ACTIVITY_SCHEMA + 'update': 'paste %(object)s aan',
                NS_ACTIVITY_SCHEMA + 'rsvp-yes': 'komt naar %(object)s',
                NS_ACTIVITY_SCHEMA + 'checkin': 'was bij %(object)s',
                NS_ANYMETA_ACTIVITY + 'link-to': 'linkte naar %(object)s vanaf %(target)s',
                NS_ANYMETA_ACTIVITY + 'status-update': None,
                NS_ANYMETA_ACTIVITY + 'iktag': 'koppelde een ikTag',
                NS_ANYMETA_ACTIVITY + 'facebook-connect': 'koppelde aan Facebook',
                ACTIVITY_COMMIT: 'committe %(object)s op %(target)s',
                }
            }
    TEXTS_EN = {
            'activity_verbs': {
                NS_ACTIVITY_SCHEMA + 'post': 'posted %(object)s',
                NS_ACTIVITY_SCHEMA + 'like': 'liked %(object)s',
                NS_ACTIVITY_SCHEMA + 'tag': 'tagged %(object)s in %(target)s',
                NS_ACTIVITY_SCHEMA + 'share': 'shared %(object)s on %(target)s',
                NS_ACTIVITY_SCHEMA + 'make-friend': 'friended %(object)s',
                NS_ACTIVITY_SCHEMA + 'update': 'updated %(object)s',
                NS_ACTIVITY_SCHEMA + 'rsvp-yes': 'will attend %(object)s',
                NS_ACTIVITY_SCHEMA + 'checkin': 'was at %(object)s',
                NS_ANYMETA_ACTIVITY + 'link-to': 'linked to %(object)s from %(target)s',
                NS_ANYMETA_ACTIVITY + 'status-update': None,
                NS_ANYMETA_ACTIVITY + 'iktag': 'linked an ikTag',
                NS_ANYMETA_ACTIVITY + 'facebook-connect': 'connected to Facebook',
                ACTIVITY_COMMIT: 'committed %(object)s on %(target)s',
                }
            }

    supportedVerbs = ()
    agentVerbs = frozenset()

    def format_payload(self, payload):
        """
        Render the payload into a notification.

        If available, this uses the anyMeta specific 'figure' links to point to
        scaled-and-cropped versions of the image used for the actor (icon) or
        the object (picture).
        """
        verbs = set([unicode(element)
                 for element in payload.elements(NS_ACTIVITY_SPEC, 'verb')])

        template = None
        for verb in self.supportedVerbs:
            if verb in verbs:
                template = self.texts[self.feed.language]['activity_verbs'][verb]
                break

        if template is None:
            return None

        if payload.agent and verb not in self.agentVerbs:
            return None

        from twisted.words.xish.domish import generateElementsNamed
        actorTitle = unicode(generateElementsNamed(payload.author.elements(),
                                                   'name').next())

        figureURI = None
        for element in payload.author.elements(NS_ATOM, 'link'):
            if element.getAttribute('rel', 'alternate') == 'figure':
                figureURI = element.getAttribute('href')
                break

        if figureURI:
            figureURI += '?width=80&height=80&filter=crop'

        pictureURI = None
        for element in payload.object.elements(NS_ACTIVITY_SPEC,
                                               'object-type'):
            if unicode(element) == TYPE_ATTACHMENT:
                for element in payload.object.elements(NS_ATOM, 'link'):
                    if element.getAttribute('rel', 'alternate') == 'figure':
                        pictureURI = element.getAttribute('href')
                        break
                if pictureURI:
                    pictureURI += '?width=480'

        vars = {}
        if payload.object and payload.object.title:
            vars['object'] = unicode(payload.object.title)

        if payload.target and payload.target.title:
            vars['target'] = unicode(payload.target.title)

        subtitle = template % vars

        notification = {
                'title': actorTitle,
                'subtitle': subtitle,
                'via': self.getVia()
                }
        if figureURI:
            notification['icon'] = figureURI
        if pictureURI:
            notification['picture'] = pictureURI

        return notification



class ActivityStreamSource(ActivityStreamSourceMixin, item.Item):
    """
    Generic anyMeta Activity Streams source.
    """

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

    supportedVerbs = (
                NS_ANYMETA_ACTIVITY + 'status-update',
                NS_ACTIVITY_SCHEMA + 'post',
                NS_ACTIVITY_SCHEMA + 'like',
                NS_ACTIVITY_SCHEMA + 'tag',
                NS_ACTIVITY_SCHEMA + 'share',
                NS_ACTIVITY_SCHEMA + 'make-friend',
                NS_ACTIVITY_SCHEMA + 'update',
                #NS_ACTIVITY_SCHEMA + 'rsvp-yes',
                #NS_ANYMETA_ACTIVITY + 'link-to',
                NS_ANYMETA_ACTIVITY + 'iktag',
                NS_ANYMETA_ACTIVITY + 'facebook-connect',
                )

    agentVerbs = frozenset((
                NS_ACTIVITY_SCHEMA + 'like',
                NS_ANYMETA_ACTIVITY + 'iktag',
                NS_ANYMETA_ACTIVITY + 'facebook-connect',
                ))

    def getNode(self):
        if self.site is not None:
            return (getPubSubService(self.site.uri), u'activity')


    def renderTitle(self):
        s = "%s from %s" % (self.title, (self.site and self.site.title) or "?")
        return s


    def getVia(self):
        return self.site.title



class IkCamSource(ActivityStreamSourceMixin, item.Item):
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

    ikCamVerb = NS_ANYMETA_ACTIVITY + 'ikcam'

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
        """
        Render the payload into a notification.

        If available, this uses the anyMeta specific 'figure' links to point to
        scaled-and-cropped versions of the image used for the actor (icon) or
        the object (picture).
        """
        texts = self.texts[self.feed.language]

        verbs = set([unicode(element)
                 for element in payload.elements(NS_ACTIVITY_SPEC, 'verb')])

        if self.ikCamVerb not in verbs:
            return None

        # filter out ikcam notifications from other agents
        if payload.agent and self.creator and unicode(payload.agent.id) != self.creator.uri:
            return None

        # filter out ikcam notifications from other events
        if payload.target and self.event and unicode(payload.target.id) != self.event.uri:
            return None

        from twisted.words.xish.domish import generateElementsQNamed
        actors = generateElementsQNamed(payload.elements(), 'author', NS_ATOM)
        names = reduce(lambda x, y: x+y, [list(generateElementsQNamed(actor.elements(), 'name', NS_ATOM)) for actor in actors], [])
        actorTitles = [unicode(element) for element in names]

        if not actorTitles:
            return
        elif len(actorTitles) == 1:
            subtitle = texts['ikcam_picture_singular']
        else:
            subtitle = texts['ikcam_picture_plural']

        if payload.target:
            subtitle += texts['ikcam_event'] % unicode(payload.target.title)

        pictureURI = None
        for element in payload.object.elements(NS_ATOM, 'link'):
            if element.getAttribute('rel', 'alternate') == 'figure':
                pictureURI = element.getAttribute('href')
                break
        if pictureURI:
            pictureURI += '?width=480'

        return {'title': unicode(implodeNames(actorTitles, self.feed.language)),
                'subtitle': subtitle,
                'icon': u'http://docs.mediamatic.nl/images/ikcam-80x80.png',
                'picture': pictureURI,
                }


    def getNode(self):
        nodeIdentifier = 'ikcam/'
        if self.creator:
            service = getPubSubService(self.creator.uri)
            nodeIdentifier += getThingID(self.creator.uri)
        elif self.event:
            service = getPubSubService(self.event.uri)
            nodeIdentifier += 'by_event/' + getThingID(self.event.uri)
        else:
            return None

        return service, nodeIdentifier


    def renderTitle(self):
        s = self.title
        if self.event:
            s += " for the event " + self.event.title
        if self.creator:
            s += " created by " + self.creator.title
        return s



class CommitsSource(ActivityStreamSourceMixin, item.Item):
    """
    Mediamatic Subversion commits source.
    """

    title = "Commits"

    feed = attributes.reference()
    enabled = attributes.boolean()
    via = attributes.text()
    subscription = attributes.reference()
    service = JIDAttribute()
    nodeIdentifier = attributes.text()

    supportedVerbs = (
            ACTIVITY_COMMIT,
            )

    def format_payload(self, payload):
        try:
            notification = ActivityStreamSourceMixin.format_payload(self, payload)
            msg = unicode(payload.object.message).split('\n')[0]
            notification['subtitle'] += ': %s' % msg
        except Exception, e:
            log.err(e)
        return notification


    def getNode(self):
        return (self.service, self.nodeIdentifier)


    def renderTitle(self):
        s = "Commits from %s" % (self.service and self.service.full() or "?")
        return s


    def getVia(self):
        return 'Subversion'



class WoWSource(ActivityStreamSourceMixin, item.Item):
    """
    Write on Wall Activity Stream source.
    """

    title = "WoW Stream"

    feed = attributes.reference()
    enabled = attributes.boolean()
    via = attributes.text()
    subscription = attributes.reference()
    agent = attributes.reference("""
    Reference to the thing representing the agent of the activities.
    """)

    supportedVerbs = (
                NS_ACTIVITY_SCHEMA + 'post',
                NS_ACTIVITY_SCHEMA + 'like',
                )

    agentVerbs = frozenset((
                NS_ACTIVITY_SCHEMA + 'post',
                NS_ACTIVITY_SCHEMA + 'like',
                ))

    def getNode(self):
        if self.agent is not None:
            return (getPubSubService(self.agent.uri), u'activity')


    def format_payload(self, payload):
        if not payload.agent or unicode(payload.agent.id) != self.agent.uri:
            return None

        return ActivityStreamSourceMixin.format_payload(self, payload)


    def renderTitle(self):
        return self.title


    def getVia(self):
        return self.via



class CheckinsSource(ActivityStreamSourceMixin, item.Item):
    """
    anyMeta Activity Streams source for checkins
    """

    title = "Checkins"

    feed = attributes.reference()
    enabled = attributes.boolean()
    via = attributes.text()
    subscription = attributes.reference()
    site = attributes.reference("""
    Reference to the site representing where activities occur.
    """)

    supportedVerbs = (
                NS_ACTIVITY_SCHEMA + 'checkin',
                )

    agentVerbs = frozenset((
                NS_ACTIVITY_SCHEMA + 'checkin',
                ))

    def getNode(self):
        if self.site is not None:
            return (getPubSubService(self.site.uri), u'activity')


    def renderTitle(self):
        s = "%s from %s" % (self.title, (self.site and self.site.title) or "?")
        return s


    def getVia(self):
        return self.site.title



def implodeNames(names, lang):
    lastsep = {'en': ' and ',
               'nl': ' en '}[lang]
    if len(names) < 3:
        return lastsep.join(names)
    return ', '.join(names[:-1]) + lastsep + names[-1]



allSources = [
#    SimpleSource,
    VoteSource,
    PresenceSource,
    IkMicSource,
    StatusSource,
    TwitterSource,
    IkCamSource,
    RegDeskSource,
    RaceSource,
    ActivityStreamSource,
    CommitsSource,
    WoWSource,
    CheckinsSource,
    ]
"""
The global list of all sources.
"""
