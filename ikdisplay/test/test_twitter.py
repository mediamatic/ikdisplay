"""
Tests for L{ikdisplay.twitter}.
"""

from twisted.internet import defer
from twisted.trial import unittest

from twittytwister.streaming import Status, Entities, Media, URL

from ikdisplay import twitter

class TwitterMonitorTest(unittest.TestCase):
    """
    Tests for L{twitter.TwitterMonitor}.
    """

    def setUp(self):
        self.entries = []
        self.monitor = twitter.TwitterMonitor(None, None, consumer=self)


    def onEntry(self, entry):
        self.entries.append(entry)


    def test_augmentStatusWithImageMediaEntities(self):
        def cb(result):
            entry = self.entries[-1]
            self.assertEqual(media.media_url, entry.image_url)

        media = Media()
        media.media_url = 'http://p.twimg.com/AQ9JtQsCEAA7dEN.jpg'
        status = Status()
        status.entities = Entities()
        status.entities.media = [media]

        d = self.monitor.onEntry(status)
        d.addCallback(cb)
        return d


    def test_augmentStatusWithImageURLEntities(self):
        """
        If there is no media entity, try expanded extracted URLs.

        This overrides L{twitter.extractImage} so that it always returns
        the given URL, as if it was successfully extracted.
        """
        def cb(result):
            entry = self.entries[-1]
            self.assertEqual(url.expanded_url, entry.image_url)

        url = URL()
        url.url = 'http://t.co/qbJx26r'
        url.expanded_url = 'http://twitter.com/twitter/status/76360760606986241/photo/1'
        status = Status()
        status.entities = Entities()
        status.entities.urls = [url]

        self.patch(twitter, 'extractImage', defer.succeed)

        d = self.monitor.onEntry(status)
        d.addCallback(cb)
        return d


    def test_augmentStatusWithImageURLEntitiesNoImage(self):
        """
        If the embedded URLs don't resolve to an image, set it to None.

        This overrides L{twitter.extractImage} so that it always returns
        the given URL, as if it was successfully extracted.
        """
        def cb(result):
            entry = self.entries[-1]
            self.assertIdentical(None, entry.image_url)

        url = URL()
        url.url = 'http://t.co/qbJx26r'
        url.expanded_url = 'http://twitter.com/twitter/status/76360760606986241/photo/1'
        status = Status()
        status.entities = Entities()
        status.entities.urls = [url]

        self.patch(twitter, 'extractImage', lambda url: defer.succeed(None))

        d = self.monitor.onEntry(status)
        d.addCallback(cb)
        return d


    def test_augmentStatusWithImageURLEntitiesException(self):
        """
        If an exception is raised while trying to resolve entities, 

        This overrides L{twitter.extractImage} so that it always returns
        the given URL, as if it was successfully extracted.
        """
        def cb(result):
            entry = self.entries[-1]
            self.assertIdentical(None, entry.image_url)
            self.flushLoggedErrors()

        url = URL()
        url.url = 'http://t.co/qbJx26r'
        url.expanded_url = 'http://twitter.com/twitter/status/76360760606986241/photo/1'
        status = Status()
        status.entities = Entities()
        status.entities.urls = [url]

        self.patch(twitter, 'extractImage',
                            lambda url: defer.fail(Exception()))

        d = self.monitor.onEntry(status)
        d.addCallback(cb)
        return d


    def test_augmentStatusWithImageURLEntitiesURL(self):
        """
        If there is no expanded URL, try the extracted URL.
        """
        def extractImage(url):
            return defer.succeed(url)

        def cb(result):
            entry = self.entries[-1]
            self.assertEqual(url.url, entry.image_url)

        url = URL()
        url.url = 'http://t.co/qbJx26r'
        status = Status()
        status.entities = Entities()
        status.entities.urls = [url]

        self.patch(twitter, 'extractImage', defer.succeed)

        d = self.monitor.onEntry(status)
        d.addCallback(cb)
        return d


    def test_augmentStatusWithImageURLEntitiesURLNoSchema(self):
        """
        If the extracted URL doesn't have a schema, add it.
        """
        def extractImage(url):
            return defer.succeed(url)

        def cb(result):
            entry = self.entries[-1]
            self.assertEqual('http://' + url.url, entry.image_url)

        url = URL()
        url.url = 't.co/qbJx26r'
        status = Status()
        status.entities = Entities()
        status.entities.urls = [url]

        self.patch(twitter, 'extractImage', defer.succeed)

        d = self.monitor.onEntry(status)
        d.addCallback(cb)
        return d


    def test_augmentStatusWithImageNoEntities(self):
        def cb(result):
            entry = self.entries[-1]
            self.assertIdentical(None, entry.image_url)

        status = Status()
        status.entities = Entities()

        d = self.monitor.onEntry(status)
        d.addCallback(cb)
        return d



class TestExtractImage(unittest.TestCase):

    def _testExtractImage(self, inurl, outurl):
        d = twitter.extractImage(inurl)
        d.addCallback(lambda result: self.assertEquals(outurl, result))
        return d


    def testTwitpic(self):
        return self._testExtractImage("http://twitpic.com/3dhy78", "http://twitpic.com/show/large/3dhy78")


    def testMobyPictureFull(self):
        return self._testExtractImage("http://www.mobypicture.com/user/marjolijn/view/90053", "http://a3.img.mobypicture.com/5bd603ae84e09ac10ce15b98f4dd5e7f_full.jpg")


    def testMobyPictureShort(self):
        return self._testExtractImage("http://moby.to/1234", "http://a1.img.mobypicture.com/5d84733aa1dd84f9bb0da21e2413acfa_full.jpg")


    def testFlickr(self):
        return self._testExtractImage(
            "http://www.flickr.com/photos/bees/2341623661/",
            "http://farm4.staticflickr.com/3123/2341623661_7c99f48bbf_b.jpg")


    def testYFrog(self):
        return self._testExtractImage("http://yfrog.com/c9vd30j", "http://img441.yfrog.com/img441/3194/vd30.jpg")


    def testImgur(self):
        return self._testExtractImage("http://imgur.com/hPa9B", "http://imgur.com/hPa9B.jpg")


    def testTinypic(self):
        return self._testExtractImage("http://i56.tinypic.com/zoc3o0.jpg", "http://i56.tinypic.com/zoc3o0.jpg")


    def testUnsupported(self):
        return self._testExtractImage("http://some.unsupported/url", None)
