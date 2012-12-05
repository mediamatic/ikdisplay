"""
Tests for L{ikdisplay.twitter}.
"""

from twisted.internet import defer
from twisted.trial import unittest

from axiom.store import Store

from twittytwister.streaming import Status, Entities, Media, URL

from ikdisplay.source import TwitterSource
from ikdisplay import twitter

class FakeMonitor(object):
    """
    Fake TwitterMonitor that collects connect calls.
    """
    args = None
    delegate = None

    def __init__(self):
        self.connects = []

    def connect(self, forceReconnect=False):
        self.connects.append(forceReconnect)



class TwitterDispatcherTest(unittest.TestCase):
    """
    Tests for L{ikdisplay.twitter.TwitterDispatcher}.
    """

    def setUp(self):
        self.monitor = FakeMonitor()
        self.store = Store()
        self.dispatcher = twitter.TwitterDispatcher(self.store, self.monitor,
                                                    None)


    def test_initSetFilters(self):
        """
        setFilters gets called from __init__, setting delegate.
        """
        source = TwitterSource(store=self.store)
        source.enabled = True
        source.terms = ['ikdisplay']
        source.userIDs = ['2426271']
        self.dispatcher = twitter.TwitterDispatcher(self.store, self.monitor,
                                                    None)
        self.assertEqual(self.dispatcher.onEntry, self.monitor.delegate)
        self.assertEqual([], self.monitor.connects)


    def test_initSetFiltersNoArgs(self):
        """
        When there are no initial arguments, the delegate remains empty.
        """
        self.assertIdentical(None, self.monitor.delegate)
        self.assertEqual([], self.monitor.connects)


    def test_setFiltersEmptyTrack(self):
        """
        If the list of filter terms is empty, don't set the track argument.
        """
        source = TwitterSource(store=self.store)
        source.enabled = True
        source.terms = []
        source.userIDs = ['2426271']
        self.dispatcher.setFilters()

        self.assertNotIn('track', self.monitor.args)


    def test_setFiltersEmptyFollow(self):
        """
        If the list of user ids is empty, don't set the follow argument.
        """
        source = TwitterSource(store=self.store)
        source.enabled = True
        source.terms = ['ikdisplay']
        source.userIDs = []
        self.dispatcher.setFilters()

        self.assertNotIn('follow', self.monitor.args)



    def test_refreshFiltersDisabled(self):
        """
        If a source with terms has been disabled, reconnect.
        """
        source = TwitterSource(store=self.store)
        source.enabled = True
        source.terms = ['ikdisplay']
        source.userIDs = []
        self.dispatcher.refreshFilters()

        self.assertEqual([True], self.monitor.connects)
        self.assertEqual(self.dispatcher.onEntry, self.monitor.delegate)

        source.enabled = False
        self.dispatcher.refreshFilters()

        self.assertEqual([True, True], self.monitor.connects)
        self.assertIdentical(None, self.monitor.delegate)


    def test_refreshFiltersUnchangedArgs(self):
        """
        If a source has changed, but not the monitor args, don't reconnect.
        """
        source = TwitterSource(store=self.store)
        source.enabled = False
        source.terms = ['ikdisplay']
        source.userIDs = []
        self.dispatcher.refreshFilters()

        self.assertEqual([], self.monitor.connects)

        source.terms = ['ikdisplay', 'xmpp']
        self.dispatcher.refreshFilters()

        self.assertEqual([], self.monitor.connects)



class EmbedderTest(unittest.TestCase):
    """
    Tests for L{twitter.Embedder}.
    """

    def setUp(self):
        self.config = {}
        self.embedder = twitter.Embedder(self.config)


    def test_augmentStatusWithImageMediaEntities(self):
        def cb(entry):
            self.assertEqual(media.media_url, entry.image_url)

        media = Media()
        media.media_url = 'http://p.twimg.com/AQ9JtQsCEAA7dEN.jpg'
        status = Status()
        status.entities = Entities()
        status.entities.media = [media]

        d = self.embedder.augmentStatusWithImage(status)
        d.addCallback(cb)
        return d


    def test_augmentStatusWithImageURLEntities(self):
        """
        If there is no media entity, try expanded extracted URLs.

        This overrides L{twitter.extractImage} so that it always returns
        the given URL, as if it was successfully extracted.
        """
        def cb(entry):
            self.assertEqual(url.expanded_url, entry.image_url)

        url = URL()
        url.url = 'http://t.co/qbJx26r'
        url.expanded_url = 'http://twitter.com/twitter/status/' \
                               '76360760606986241/photo/1'
        status = Status()
        status.entities = Entities()
        status.entities.urls = [url]

        self.patch(self.embedder, 'extractImage', defer.succeed)

        d = self.embedder.augmentStatusWithImage(status)
        d.addCallback(cb)
        return d


    def test_augmentStatusWithImageURLEntitiesNoImage(self):
        """
        If the embedded URLs don't resolve to an image, set it to None.

        This overrides L{twitter.extractImage} so that it always returns
        the given URL, as if it was successfully extracted.
        """
        def cb(entry):
            self.assertIdentical(None, entry.image_url)

        url = URL()
        url.url = 'http://t.co/qbJx26r'
        url.expanded_url = 'http://twitter.com/twitter/status/' \
                               '76360760606986241/photo/1'
        status = Status()
        status.entities = Entities()
        status.entities.urls = [url]

        self.patch(self.embedder, 'extractImage',
                   lambda url: defer.succeed(None))

        d = self.embedder.augmentStatusWithImage(status)
        d.addCallback(cb)
        return d


    def test_augmentStatusWithImageURLEntitiesException(self):
        """
        If an exception is raised while trying to resolve entities, log it.

        This overrides L{twitter.extractImage} so that it always returns
        the given URL, as if it was successfully extracted.
        """
        def cb(entry):
            self.assertIdentical(None, entry.image_url)
            self.flushLoggedErrors()

        url = URL()
        url.url = 'http://t.co/qbJx26r'
        url.expanded_url = 'http://twitter.com/twitter/status/' \
                               '76360760606986241/photo/1'
        status = Status()
        status.entities = Entities()
        status.entities.urls = [url]

        self.patch(self.embedder, 'extractImage',
                   lambda url: defer.fail(Exception()))

        d = self.embedder.augmentStatusWithImage(status)
        d.addCallback(cb)
        return d


    def test_augmentStatusWithImageURLEntitiesURL(self):
        """
        If there is no expanded URL, try the extracted URL.
        """
        def extractImage(url):
            return defer.succeed(url)

        def cb(entry):
            self.assertEqual(url.url, entry.image_url)

        url = URL()
        url.url = 'http://t.co/qbJx26r'
        status = Status()
        status.entities = Entities()
        status.entities.urls = [url]

        self.patch(self.embedder, 'extractImage', defer.succeed)

        d = self.embedder.augmentStatusWithImage(status)
        d.addCallback(cb)
        return d


    def test_augmentStatusWithImageURLEntitiesURLNoSchema(self):
        """
        If the extracted URL doesn't have a schema, add it.
        """
        def extractImage(url):
            return defer.succeed(url)

        def cb(entry):
            self.assertEqual('http://' + url.url, entry.image_url)

        url = URL()
        url.url = 't.co/qbJx26r'
        status = Status()
        status.entities = Entities()
        status.entities.urls = [url]

        self.patch(self.embedder, 'extractImage', defer.succeed)

        d = self.embedder.augmentStatusWithImage(status)
        d.addCallback(cb)
        return d


    def test_augmentStatusWithImageNoEntities(self):
        def cb(entry):
            self.assertIdentical(None, entry.image_url)

        status = Status()
        status.entities = Entities()

        d = self.embedder.augmentStatusWithImage(status)
        d.addCallback(cb)
        return d


    def _testExtractImage(self, inurl, outurl):
        d = self.embedder.extractImage(inurl)
        d.addCallback(lambda result: self.assertEquals(outurl, result))
        return d


    def testTwitpic(self):
        return self._testExtractImage(
            "http://twitpic.com/3dhy78",
            "http://twitpic.com/show/large/3dhy78")


    def testMobyPictureFull(self):
        return self._testExtractImage(
            "http://www.mobypicture.com/user/marjolijn/view/90053",
            "http://a3.img.mobypicture.com/"
                "5bd603ae84e09ac10ce15b98f4dd5e7f_full.jpg")


    def testMobyPictureShort(self):
        return self._testExtractImage(
            "http://moby.to/1234",
            "http://a1.img.mobypicture.com/"
                "5d84733aa1dd84f9bb0da21e2413acfa_full.jpg")


    def testFlickr(self):
        return self._testExtractImage(
            "http://www.flickr.com/photos/bees/2341623661/",
            "http://farm4.staticflickr.com/3123/2341623661_7c99f48bbf_b.jpg")


    def testImgur(self):
        return self._testExtractImage(
            "http://imgur.com/hPa9B",
            "http://imgur.com/hPa9B.jpg")


    def testTinypic(self):
        return self._testExtractImage(
            "http://i56.tinypic.com/zoc3o0.jpg",
            "http://i56.tinypic.com/zoc3o0.jpg")


    def testInstagram(self):
        return self._testExtractImage(
            "http://instagr.am/p/S2aLN-DbxS/",
            "http://instagr.am/p/S2aLN-DbxS/media?size=l")


    def testEmbedly(self):
        def _oEmbed(url):
            return defer.succeed(url)

        self.patch(self.embedder, '_oEmbed', _oEmbed)
        self._testExtractImage(
                "http://yfrog.com/c9vd30j",
                "http://api.embed.ly/1/oembed?url=http://yfrog.com/c9vd30j")


    def testEmbedlyAPIKey(self):
        """
        If the config passed the embedder has an embed.ly API key, use it.
        """
        def _oEmbed(url):
            return defer.succeed(url)

        self.config['embedly-key'] = 'mykey'
        self.patch(self.embedder, '_oEmbed', _oEmbed)
        self._testExtractImage(
                "http://yfrog.com/c9vd30j",
                "http://api.embed.ly/1/oembed?key=mykey&"
                                             "url=http://yfrog.com/c9vd30j")


    def testUnsupported(self):
        return self._testExtractImage("http://some.unsupported/url", None)
