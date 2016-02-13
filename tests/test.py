# encoding: utf8

""" Tests for pafy. """

from __future__ import unicode_literals
from functools import wraps
import hashlib
import pafy
import time
import os
import sys

try:
    import unittest2 as unittest

except ImportError:
    import unittest


def stdout_to_null(fn):
    """  Supress stdout. """
    @wraps(fn)
    def wrapper(*a, **b):
        """ wrapping function. """
        with open(os.devnull, "w") as nul:
            stash = sys.stdout
            sys.stdout = nul
            retval = fn(*a, **b)
            sys.stdout = stash
        return retval
    return wrapper


class Test(unittest.TestCase):

    """ Tests. """

    def runOnce(self):
        """ Create pafy objects for tests. """
        if hasattr(Test, "hasrun"):
            return

        Test.quick = os.environ.get("quick")
        Test.videos = VIDEOS if not Test.quick else []
        Test.playlists = PLAYLISTS if not Test.quick else []

        for video in Test.videos:
            time.sleep(0 if Test.quick else self.delay)
            video['pafy'] = pafy.new(video['identifier'])
            video['streams'] = video['pafy'].streams
            video['best'] = video['pafy'].getbest()
            video['bestaudio'] = video['pafy'].getbestaudio()
            video['bestvideo'] = video['pafy'].getbestvideo()

            # get urls for age restricted vids
            if video['pafy'].videoid == "07FYdnEawAQ":
                _ = video['pafy'].streams[0].url
                _ = video['pafy'].streams[1].url_https
                del _

        for playlist in Test.playlists:


            playlist['fetched'] = pafy.get_playlist(playlist['identifier'])

        Test.hasrun = True

    def setUp(self):
        """ setup for tests. """
        self.delay = 3
        self.properties = ("videoid title length duration author "
                           "username category thumb published").split()
        self.runOnce()

    def test_generate_filename_with_meta(self):
        """ Use meta argument to generate filename. """
        if Test.quick:
            return

        p = pafy.new('jrNLsC_Y9Oo', size=True)
        a = p.getbestaudio()
        filename = a.generate_filename(meta=True)
        self.assertEqual(filename, 'Jessie J - WILD (Official) ft. Big Sean'
                         ', Dizzee Rascal-jrNLsC_Y9Oo-251.webm')
        self.assertEqual(a.threed, False)
        self.assertEqual(a.title, 'Jessie J - WILD (Official) ft. Big Sean'
                         ', Dizzee Rascal')
        self.assertEqual(a.notes, 'DASH audio')
        self.assertEqual(a.filename, 'Jessie J - WILD (Official) ft. Big Sean'
                         ', Dizzee Rascal.webm')

    @stdout_to_null
    def test_pafy_download(self):
        """ Test downloading. """
        callback = lambda a, b, c, d, e: 0
        vid = pafy.new("DsAn_n6O5Ns", gdata=True)
        vstream = vid.audiostreams[-1]
        name = vstream.download(callback=callback)
        self.assertEqual(name[0:5], "WASTE")

    @stdout_to_null
    def test_pafy_download_resume(self):
        """ Test resuming a partial download. """
        tempname = "WASTE  2 SECONDS OF YOUR LIFE-DsAn_n6O5Ns-171.m4a.temp"
        with open(tempname, "w") as ladeeda:
            ladeeda.write("abc")
        vid = pafy.new("DsAn_n6O5Ns", gdata=True, basic=False)
        vstream = vid.audiostreams[-1].download(meta=True, remux_audio=True)
        name = "WASTE  2 SECONDS OF YOUR LIFE.m4a"
        self.assertEqual(63639, os.stat(name).st_size)

        # test fetching attributes
        vid._title = None
        _ = vid.title
        vid._rating = None
        _ = vid.rating
        vid._author = None
        _ = vid.author
        vid._rating = None
        _ = vid.rating
        vid._length = None
        _ = vid.length
        vid._viewcount = None
        _ = vid.viewcount
        vid._thumb = None
        _ = vid.thumb
        vid._length = None
        _ = vid.duration

    def test_pafy_download_invalid_dirname(self):
        """ Test user specified invalid path. """
        vid = pafy.new("DsAn_n6O5Ns", gdata=True)
        self.assertRaises(IOError, vid.audiostreams[-1].download, "/bad/h/")

    @stdout_to_null
    def test_pafy__invalid_win_filename(self):
        """ Test Windows and colon character in video name. """
        os.name = "nt"
        vid = pafy.new("http://www.youtube.com/watch?v=K-TNJSBrFEk")
        audio = vid.getbestaudio()
        expected = ("Jon Meacham_ _Thomas Jefferson_ the Art of Power_ _ Talks"
                    " at Google.m4a")
        self.assertEqual(expected, audio.generate_filename())

    @stdout_to_null
    def test_pafy_download_to_dir(self):
        """ Test user specified path. """
        vid = pafy.new("DsAn_n6O5Ns", gdata=True)
        vstream = vid.audiostreams[-1].download("/tmp", meta=True)
        name = "/tmp/WASTE  2 SECONDS OF YOUR LIFE.m4a"
        self.assertEqual(63639, os.stat(name).st_size)

    #def test_lazy_pafy(self):
    #    """ Test create pafy object without fetching data. """

    #    vid = pafy.new("DsAn_n6O5Ns", basic=False, signature=False)
    #    self.assertEqual(vid.bigthumb, '')
    #    self.assertEqual(vid.bigthumbhd, '')
    #    self.assertIsInstance(vid.likes, int)
    #    self.assertIsInstance(vid.dislikes, int)

    def test_pafy_init(self):
        """ Test Pafy object creation. """
        # test bad video id, 11 chars
        badid = "12345678901"
        too_short = "123"
        self.assertRaises(ValueError, pafy.new, too_short)
        self.assertRaises(ValueError, pafy.get_playlist, badid)
        self.assertRaises(IOError, pafy.new, badid)
        self.assertRaises(IOError, pafy.get_playlist, 'PL' + "a" * 16)

    def test_video_properties(self):
        """ Test video properties. """
        for video in Test.videos:
            description = video['pafy'].description.encode("utf8")
            self.assertEqual(hashlib.sha1(description).hexdigest(),
                             video['description'])

            for prop in self.properties:

                if prop != "thumb":
                    paf_prop = getattr(video['pafy'], prop)
                    exp_prop = video[prop]
                    self.assertEqual(paf_prop, exp_prop)

            self.assertNotEqual(video.__repr__(), None)

    def test_streams_exist(self):
        """ Test for expected number of streams. """
        for video in Test.videos:
            paf = video['pafy']
            self.assertEqual(video['all streams'], len(paf.allstreams))
            self.assertEqual(video['normal streams'], len(paf.streams))
            self.assertEqual(video['audio streams'], len(paf.audiostreams))
            self.assertEqual(video['video streams'], len(paf.videostreams))
            self.assertEqual(video['ogg streams'], len(paf.oggstreams))
            self.assertEqual(video['m4a streams'], len(paf.m4astreams))

    def test_best_stream_size(self):
        """ Test stream filesize. """
        for video in Test.videos:
            time.sleep(0 if Test.quick else self.delay)
            size = video['best'].get_filesize()
            self.assertEqual(video['bestsize'], size)

    def test_get_playlist(self):
        """ Test get_playlist function. """
        for pl in Test.playlists:
            fetched = pl['fetched']
            self.assertEqual(len(fetched['items']), pl['count'])

            for field in "playlist_id description author title".split():
                self.assertEqual(fetched[field], pl[field])


PLAYLISTS = [
    {
        'identifier': "https://www.youtube.com/playlist?list=PL9-cZf_sidpkzR4W_LxvZjh4F7YFo4WoG",
        'playlist_id': "PL9-cZf_sidpkzR4W_LxvZjh4F7YFo4WoG",
        'description': "",
        'author': "#TheBeatles",
        'title': "All Tracks - The Beatles",
        'count': 200,
    },
]

VIDEOS = [
    {
        'identifier': 'ukm64IUANwE',
        'videoid': 'ukm64IUANwE',
        'title': 'Getting started with automated testing',
        'length': 1837,
        'duration': '00:30:37',
        'author': 'Next Day Video',
        'username': 'NextDayVideo',
        'published': '2013-03-19 23:43:42',
        'thumb': 'http://i.ytimg.com/vi/ukm64IUANwE/default.jpg',
        'category': 'Education',
        'description': '1223db22b4a38d0a8ebfcafb549f40c39af26251',
        'bestsize': 54284129,
        'all streams': 19,
        'normal streams': 5,
        'video streams': 8,
        'audio streams': 6,
        'ogg streams': 0,
        'm4a streams': 2,
    },
    {
        'identifier': 'www.youtube.com/watch?v=SeIJmciN8mo',
        'videoid': 'SeIJmciN8mo',
        'title': 'Nicki Minaj - Starships (Explicit)',
        'length': 261,
        'duration': '00:04:21',
        'author': 'NickiMinajAtVEVO',
        'username': 'NickiMinajAtVEVO',
        'published': '2012-04-27 04:22:39',
        'thumb': 'http://i.ytimg.com/vi/SeIJmciN8mo/default.jpg',
        'category': 'Music',
        'description': 'fa34f2704be9c1b21949af515e813f644f14b89a',
        'bestsize': 102152520,
        'all streams': 17,
        'normal streams': 6,
        'video streams': 6,
        'audio streams': 5,
        'ogg streams': 0,
        'm4a streams': 1,
    },
    {
        'identifier': 'EnHp24CVORc',
        'videoid': 'EnHp24CVORc',
        'title': 'Chinese Knock Off Sky Loop Roller Coaster POV Chuanlord Holiday Manor China 魔环垂直过山车',
        'length': 312,
        'duration': '00:05:12',
        'author': 'Theme Park Review',
        'username': 'themeparkreviewTPR',
        'published': '2014-05-05 19:58:07',
        'thumb': 'http://i.ytimg.com/vi/EnHp24CVORc/default.jpg',
        'category': 'People & Blogs',
        'description': '3c884d9791be15646ddf351edffcb2dd22ec70f8',
        'bestsize': 101082749,
        'all streams': 21,
        'normal streams': 6,
        'video streams': 12,
        'audio streams': 3,
        'ogg streams': 0,
        'm4a streams': 2,
    },
    {
        'identifier': 'http://youtube.com/watch?v=rYEDA3JcQqw',
        'videoid': 'rYEDA3JcQqw',
        'title': 'Adele - Rolling in the Deep',
        'length': 234,
        'duration': '00:03:54',
        'author': 'AdeleVEVO',
        'username': 'AdeleVEVO',
        'published': '2010-11-30 23:16:19',
        'thumb': 'http://i.ytimg.com/vi/rYEDA3JcQqw/default.jpg',
        'category': 'Music',
        'description': '72bfd9472e59a8f48b83af36197ebcf5d2227609',
        'bestsize': 41333693,
        'all streams': 23,
        'normal streams': 6,
        'video streams': 12,
        'audio streams': 5,
        'ogg streams': 0,
        'm4a streams': 1,
    }
]

if __name__ == "__main__":
    unittest.main(verbosity=2)
