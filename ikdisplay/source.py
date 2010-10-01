from zope.interface import Interface, implements

from twisted.python import log, reflect

from nevow import tags

from axiom import attributes, item

class ISource(Interface):
    """
    A feed source.
    """



class SourceMixin(object):
    implements(ISource)

    title = "Unknown source"

    def installOn(self, other):
        self.feed = other
        other.powerUp(self, ISource)


    def getForm(self):
        """
        Render the configuration form for this source.
        """
        return tags.strong()["Fixme: getForm()"]

    def renderTitle(self):
        """
        Renders a title for display in the configuration.
        """
        return self.title

    def renderForm(self):
        """
        Renders the configuration form for display in the configuration.
        """
        return tags.strong()["Fixme: renderForm()"]


class IPubSubEventProcessor(Interface):
    def itemsReceived(event):
        pass



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

    pubsubClient = None

    def activate(self):
        self.texts = {}

        for language in ('nl', 'en'):
            texts = self.texts[language] = {}
            attr = 'TEXTS_' + language.upper()
            reflect.accumulateClassDict(self.__class__, attr, texts)


#    def startService(self):
#        service.Service.startService(self)
#        self.pubsubClient.addObserver(self.itemsReceived,
#                                      self.config['service'],
#                                      self.config['node'])
#
#
#    def stopService(self):
#        service.Service.stopService(self)
#        self.pubsubClient.removeObserver(self.itemsReceived,
#                                         self.config['service'],
#                                         self.config['node'])


    def itemsReceived(self, event):
        notifications = self.format(event)
        self.feed.processNotifications(notifications)


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



class SimpleSource(PubSubSourceMixin, item.Item):
    title = "Simple source"
    
    feed = attributes.reference()
    via = attributes.text()
    subscription = attributes.reference()

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

    def renderTitle(self):
        return "%s (via: %s)" % (self.title, self.via)


class VoteSource(PubSubSourceMixin, item.Item):
    title = "Vote"

    feed = attributes.reference()
    via = attributes.text()
    question = attributes.reference(allowNone=False)
    template = attributes.text()
    texts = attributes.inmemory()

    TEXTS_NL = {
            'via': 'ikPoll',
            'voted': u'stemde op %s',
            }
    TEXTS_EN = {
            'via': 'ikPoll',
            'voted': u'voted for %s',
            }

    def renderTitle(self):
        return "%s on %s" % (self.title, self.question.title)

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

        template = self.template or self.texts[self.feed.language]['voted']
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


class PresenceSource(SourceMixin, item.Item):
    title = "Presence"

    feed = attributes.reference()
    via = attributes.text()
    question = attributes.reference(allowNone=False)

    def renderTitle(self):
        return "%s, question: %s" % (self.title, self.question.title)



class IkMicSource(SourceMixin, item.Item):
    title = "IkMic"

    feed = attributes.reference()
    via = attributes.text()
    question = attributes.reference(allowNone=False)

    def renderTitle(self):
        return "%s, question: %s" % (self.title, self.question.title)



class StatusSource(SourceMixin, item.Item):
    title = "Status updates"

    feed = attributes.reference()
    via = attributes.text()
    site = attributes.reference("""
    Reference to the site the statuses come from.
    """)
    event = attributes.reference("""
    Reference to the event the things the statuses are from are participant of.
    """)
    user = attributes.reference("""
    Reference to the thing the statuses are from.
    """)

    def renderTitle(self):
        s = "%s from %s" % (self.title, self.site.title)
        if self.event:
            s += " (event: %s)" % self.event.title
        if self.user:
            s += " (user: %s)" % self.event.title
        return s


class TwitterSource(SourceMixin, item.Item):
    title = "Twitter"

    feed = attributes.reference()
    terms = attributes.textlist()
    userIDs = attributes.textlist()



class IkCamSource(SourceMixin, item.Item):
    title = "IkCam pictures"

    feed = attributes.reference()
    via = attributes.text()
    event = attributes.reference("""
    Reference to the event the pictures were taken at.
    """)
    creator = attributes.reference("""
    Reference to the creator of the pictures.
    """)

    def renderTitle(self):
        s = self.title
        if self.event:
            s += " for the event " + self.event.title
        if self.creator:
            s += " created by " + self.creator.title
        return s


class RegDeskSource(SourceMixin, item.Item):
    title = "Registration desk"

    feed = attributes.reference()
    via = attributes.text()
    event = attributes.reference("""
    Reference to the event.
    """)

    def renderTitle(self):
        return "%s for %s" % (self.title, self.event.title)



class RaceSource(SourceMixin, item.Item):
    title = "Race events"

    feed = attributes.reference()
    via = attributes.text()
    race = attributes.reference("""
    Reference to the thing representing the race.
    """)

    def renderTitle(self):
        return "%s for the race %s" % (self.title, self.race.title)



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
