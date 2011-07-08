"""
Tests for L{ikdisplay.web}.
"""
from twisted.trial import unittest

from axiom import store
from ikdisplay import source, web

class APIResourceTest(unittest.TestCase):
    """
    Tests for L{APIResource}.
    """

    def setUp(self):
        self.store = store.Store()
        self.resource = web.APIResource(self.store, self, self, 'secret')
        self.calls = []
        self.observers = []
        self.refreshes = 0
        self.question = source.Thing(store=self.store,
                                     uri=u'http://any.nu/id/47074')
        self.vote = source.VoteSource(store=self.store,
                                      question=self.question,
                                      template=u"voted %s",
                                      enabled=True)

    def addObserver(self, observer):
        self.calls.append('add')
        self.observers.append(observer)


    def removeObserver(self, observer):
        self.calls.append('remove')
        self.observers.append(observer)


    def refreshFilters(self):
        self.refreshes += 1


    def test_api_updateItemNodeUnchanged(self):
        """
        If the pubsub node is unchanged, don't resubscribe.
        """
        class FakeRequest(object):
            args = {u'id': [self.vote.storeID],
                    u'template': ["voted %s "]}

        self.resource.api_updateItem(FakeRequest())

        self.assertEquals([], self.calls)


    def test_api_updateItemNodeChanged(self):
        """
        If the pubsub node is changed, resubscribe.
        """
        question2 = source.Thing(store=self.store, uri=u'http://any.nu/id/1')

        class FakeRequest(object):
            args = {u'id': [self.vote.storeID],
                    u'question': [question2.storeID]}

        self.resource.api_updateItem(FakeRequest())

        self.assertEquals(['remove', 'add'], self.calls)
        self.assertEquals([self.vote, self.vote], self.observers)


    def test_api_updateItemEnable(self):
        """
        If the pubsub source is enabled, subscribe.
        """
        class FakeRequest(object):
            args = {u'id': [self.vote.storeID],
                    u'enabled': [u'true']}

        self.vote.enabled = False
        self.resource.api_updateItem(FakeRequest())

        self.assertEquals(['add'], self.calls)


    def test_api_updateItemDisable(self):
        """
        If the pubsub source is disabled, unsubscribe.
        """
        class FakeRequest(object):
            args = {u'id': [self.vote.storeID],
                    u'enabled': [u'false']}

        self.vote.enabled = True
        self.resource.api_updateItem(FakeRequest())

        self.assertEquals(['remove'], self.calls)


    def test_api_updateItemTwitterDisabled(self):
        """
        If the twitter source is disabled, don't refresh.
        """
        twitter = source.TwitterSource(store=self.store,
                                       terms=[u'mediamatic'],
                                       userIDs=[],
                                       enabled=False)

        class FakeRequest(object):
            args = {u'id': [twitter.storeID],
                    u'terms': [u'mediamatic\niktag']}

        self.resource.api_updateItem(FakeRequest())

        self.assertEquals([], self.calls)
        self.assertEquals(0, self.refreshes)


    def test_api_updateItemTwitterEnabled(self):
        """
        If the twitter source is enabled, refresh.
        """
        twitter = source.TwitterSource(store=self.store,
                                       terms=[u'mediamatic'],
                                       userIDs=[],
                                       enabled=True)

        class FakeRequest(object):
            args = {u'id': [twitter.storeID],
                    u'terms': [u'mediamatic\niktag']}

        self.resource.api_updateItem(FakeRequest())

        self.assertEquals([], self.calls)
        self.assertEquals(1, self.refreshes)

