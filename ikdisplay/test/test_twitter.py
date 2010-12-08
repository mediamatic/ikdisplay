"""
Tests for L{ikdisplay.twitter}.
"""

from twisted.trial import unittest
from ikdisplay import twitter


class TestExtractImage(unittest.TestCase):

    def _testExtractImage(self, inurl, outurl):
        d = twitter.extractImage(inurl)
        d.addCallback(lambda result: self.assertEquals(outurl, result))
        return d


    def testTwitpic(self):
        return self._testExtractImage("http://twitpic.com/3dhy78", "http://twitpic.com/show/large/3dhy78")


    def testMobyPictureFull(self):
        return self._testExtractImage("http://www.mobypicture.com/user/marjolijn/view/90053", "http://img.mobypicture.com/5bd603ae84e09ac10ce15b98f4dd5e7f_full.jpg")


    def testMobyPictureShort(self):
        return self._testExtractImage("http://moby.to/1234", "http://img.mobypicture.com/5d84733aa1dd84f9bb0da21e2413acfa_full.jpg")


    def testFlickr(self):
        return self._testExtractImage("http://www.flickr.com/photos/bees/2341623661/", "http://farm4.static.flickr.com/3123/2341623661_7c99f48bbf.jpg")


    def testYFrog(self):
        return self._testExtractImage("http://yfrog.com/c9vd30j", "http://img441.yfrog.com/img441/3194/vd30.jpg")


    def testUnsupported(self):
        return self._testExtractImage("http://some.unsupported/url", None)
