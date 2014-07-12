# encoding: utf8

from __future__ import unicode_literals
from functools import wraps
import hashlib
import pafy.pafy as pafy
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
        with open(os.devnull, "w") as nul:
            stash = sys.stdout
            sys.stdout = nul
            retval = fn(*a, **b)
            sys.stdout = stash
        return retval
    return wrapper


class Test(unittest.TestCase):

    def runOnce(self):
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

        for playlist in Test.playlists:
            playlist['fetched'] = pafy.get_playlist(playlist['identifier'])

        Test.hasrun = True

    def setUp(self):
        self.delay = 3
        self.properties = ("videoid title length duration author "
                           "username category thumb published").split()
        self.runOnce()

    def get_all_funcs(self):
        mainfunc = pafy._get_mainfunc_from_js(JAVASCRIPT)
        otherfuncs = pafy._get_other_funcs(mainfunc, JAVASCRIPT)

        # store all functions in Pafy.funcmap
        pafy.Pafy.funcmap = {"jsurl": {mainfunc['name']: mainfunc}}
        pafy.Pafy.funcmap["jsurl"]["mainfunction"] = mainfunc
        for funcname, func in otherfuncs.items():
            pafy.Pafy.funcmap['jsurl'][funcname] = func

        return mainfunc, otherfuncs

    def test_make_url_no_sig(self):
        """ Test signature not in raw and no sig argument. """
        args=dict(raw="a=b&c=d", sig=None, quick=False)
        self.assertRaises(IOError, pafy._make_url, **args)

    def test_no_matching_stream(self):
        """ Test no matching stream found. """
        smap = dict()
        self.assertRaises(IOError, pafy._get_matching_stream, smap, None)

    def test_generate_filename_with_meta(self):
        p = pafy.new('jrNLsC_Y9Oo')
        a = p.getbestaudio()
        filename = a.generate_filename(meta=True)
        self.assertEqual(filename, 'Jessie J - WILD (Official) ft. Big Sean'
                         ', Dizzee Rascal-jrNLsC_Y9Oo-171.ogg')
        self.assertEqual(a.threed, False)
        self.assertEqual(a.title, 'Jessie J - WILD (Official) ft. Big Sean'
                         ', Dizzee Rascal')
        self.assertEqual(a.notes, '')
        self.assertEqual(a.filename, 'Jessie J - WILD (Official) ft. Big Sean'
                         ', Dizzee Rascal.ogg')

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
        tempname = "WASTE  2 SECONDS OF YOUR LIFE-DsAn_n6O5Ns-171.ogg.temp"
        open(tempname, "w").write("abc")
        vid = pafy.new("DsAn_n6O5Ns", gdata=True)
        vstream = vid.audiostreams[-1].download(meta=True)
        name = "WASTE  2 SECONDS OF YOUR LIFE.ogg"
        self.assertEqual(22675, os.stat(name).st_size)

    def test_pafy_download_invalid_dirname(self):
        """ Test user specified invalid path. """
        vid = pafy.new("DsAn_n6O5Ns", gdata=True)
        self.assertRaises(IOError, vid.audiostreams[-1].download, "/bad/h/")

    @stdout_to_null
    def test_pafy__invalid_win_filename(self):
        """ Test Windows and colon character in video name. """
        os.name = "nt"
        youtube_title = "#$&#@)($&)(*_)&@#()&#@$_*#(&@"
        vid = pafy.new("http://www.youtube.com/watch?v=6vaX2P5R3VI")
        audio = vid.getbestaudio()
        expected = "#$&#@)($&)(__)&@#()&#@$__#(&@.m4a"
        self.assertEquals(expected, audio.generate_filename())

    @stdout_to_null
    def test_pafy_download_to_dir(self):
        """ Test user specified path. """
        vid = pafy.new("DsAn_n6O5Ns", gdata=True)
        vstream = vid.audiostreams[-1].download("/tmp", meta=True)
        name = "/tmp/WASTE  2 SECONDS OF YOUR LIFE.ogg"
        self.assertEqual(22675, os.stat(name).st_size)

    def test_lazy_pafy(self):
        """ Test create pafy object without fetching data. """

        vid = pafy.new("DsAn_n6O5Ns", basic=False, signature=False)
        self.assertEqual(vid.bigthumb, '')
        self.assertEqual(vid.bigthumbhd, '')
        self.assertIsInstance(vid.likes, int)
        self.assertIsInstance(vid.dislikes, int)

    def test_pafy_init(self):
        """ Test Pafy object creation. """
        # test bad video id, 11 chars
        badid = "12345678901"
        too_short = "123"
        self.assertRaises(ValueError, pafy.new, too_short)
        self.assertRaises(ValueError, pafy.get_playlist, badid)
        self.assertRaises(IOError, pafy.new, badid)
        self.assertRaises(IOError, pafy.get_playlist, "a" * 18)

        for video in Test.videos:
            self.assertIsInstance(video['pafy'], pafy.Pafy)
            #self.assertTrue(isinstance(video['pafy'], pafy.Pafy))

    def test_video_properties(self):
        """ Test video properties. """
        for video in Test.videos:
            description = video['pafy'].description.encode("utf8")
            self.assertEqual(hashlib.sha1(description).hexdigest(),
                             video['description'])

            for prop in self.properties:
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

    def test_get_other_funcs(self):
        """ Test extracting javascript functions. """
        js = "function  f$(x,y){var X=x[1];var Y=y[1];return X;}"
        primary_func = dict(body="a=f$(12,34);b=f$(56,67)")
        otherfuncs = pafy._get_other_funcs(primary_func, js)
        # otherfuncs should be:
        #{'f$': {'body': var X=x[1];var Y=y[1];return X;",
        #        'name': 'f$', 'parameters': ['x', 'y']}}
        expected_body = 'var X=x[1];var Y=y[1];return X;'
        self.assertEqual(otherfuncs['f$']['body'], expected_body)
        self.assertEqual(otherfuncs['f$']['name'], 'f$')
        self.assertEqual(otherfuncs['f$']['parameters'], ['x', 'y'])

    def test_solve(self):
        """ Test solve js function. """
        mainfunc, otherfuncs = self.get_all_funcs()
        self.assertEqual(mainfunc['name'], "mthr")
        self.assertEqual(mainfunc["parameters"], ["a"])
        self.assertGreater(len(mainfunc['body']), 3)
        #self.assertTrue(len(mainfunc['body']) > 3,
                        #"%s not greater than %s" % (len(mainfunc['body']), 3))
        self.assertIn("return", mainfunc['body'])
        self.assertEqual(otherfuncs['fkr']['parameters'], ['a', 'b'])
        # test pafy._solve
        mainfunc['args'] = {'a': "1234567890"}
        solved = pafy._solve(mainfunc, "jsurl")
        self.assertEqual(solved, "2109876752")

    def test_solve_errors(self):
        """ Test solve function exceptions. """

        mainfunc, otherfuncs = self.get_all_funcs()

        # test unknown javascript
        mainfunc['body'] = mainfunc['body'].replace("a=a.reverse()", "a=a.peverse()")
        mainfunc['args'] = dict(a="1234567890")
        self.assertRaises(IOError, pafy._solve, mainfunc, "jsurl")

        # test return statement not found
        mainfunc, otherfuncs = self.get_all_funcs()
        mainfunc['body'] = mainfunc['body'].replace("return ", "a=")
        mainfunc['args'] = dict(a="1234567890")
        self.assertRaises(IOError, pafy._solve, mainfunc, "jsurl")

    def test_decodesig(self):
        """ Test signature decryption function. """
        mainfunc, otherfuncs = self.get_all_funcs()
        pafy.new.callback = lambda x: None
        self.assertEqual('2109876752', pafy._decodesig('1234567890', 'jsurl'))
        mainfunc, otherfuncs = self.get_all_funcs()
        pafy.Pafy.funcmap["jsurl"]['mainfunction']['parameters'] = ["a", "b"]
        self.assertRaises(IOError, pafy._decodesig, '1234567890', 'jsurl')

    def test_get_playlist(self):
        """ Test get_playlist function. """

        for pl in Test.playlists:
            fetched = pl['fetched']
            self.assertEqual(len(fetched['items']), pl['count'])

            for field in "playlist_id description author title".split():
                self.assertEqual(fetched[field], pl[field])

    def test_misc_tests(self):
        """ Test extract_smap and _getval. """
        self.assertEqual(pafy._extract_smap("a", "bcd"), [])
        self.assertRaises(IOError, pafy._getval, "no_digits_here", "88")

        # _get_func_from_call
        xcaller = {"args": [1, 2, 3]}
        xname = {'parameters': [1, 2, 3]}
        xarguments = ["1", "2", "3"]
        pafy.Pafy.funcmap["js_url"] = {"hello": xname}
        pafy._get_func_from_call(xcaller, "hello", xarguments, "js_url")


JAVASCRIPT = """\
function mthr(a){a=a.split("");a=fkr(a,59);a=a.slice(1);a=fkr(a,66);\
a=a.slice(3);a=fkr(a,10);a=a.reverse();a=fkr(a,55);a=fkr(a,70);\
a=a.slice(1);return a.join("")};

function fkr(a,b){var c=a[0];a[0]=a[b%a.length];a[b]=c;return a};

z.sig||mthr(aaa.bbb)
"""


PLAYLISTS = [
    {
        'identifier': "http://www.youtube.com/playlist?list=PL91EF4BD43796A9A4",
        'playlist_id': "PL91EF4BD43796A9A4",
        'description': "",
        'author': "sanjeev virmani",
        'title': "Android Development 200 lectures",
        'count': 200,
    },
]

VIDEOS = [
    {
        'identifier': 'ukm64IUANwE',
        'videoid': 'ukm64IUANwE',
        'title': 'Getting started with automated testing',
        'length': 1838,
        'duration': '00:30:38',
        'author': 'NextDayVideo',
        'username': 'NextDayVideo',
        'published': '2013-03-19 23:43:42',
        'thumb': 'http://i1.ytimg.com/vi/ukm64IUANwE/default.jpg',
        'category': 'Education',
        'description': '1223db22b4a38d0a8ebfcafb549f40c39af26251',
        'bestsize': 54284129,
        'all streams': 10,
        'normal streams': 5,
        'video streams': 4,
        'audio streams': 1,
        'ogg streams': 0,
        'm4a streams': 1,
    },
    {
        'identifier': 'www.youtube.com/watch?v=SeIJmciN8mo',
        'videoid': 'SeIJmciN8mo',
        'title': 'Nicki Minaj - Starships (Explicit)',
        'length': 262,
        'duration': '00:04:22',
        'author': 'NickiMinajAtVEVO',
        'username': 'NickiMinajAtVEVO',
        'published': '2012-04-27 04:22:39',
        'thumb': 'http://i1.ytimg.com/vi/SeIJmciN8mo/default.jpg',
        'category': 'Music',
        'description': 'fa34f2704be9c1b21949af515e813f644f14b89a',
        'bestsize': 101836539,
        'all streams': 21,
        'normal streams': 6,
        'video streams': 13,
        'audio streams': 2,
        'ogg streams': 1,
        'm4a streams': 1,
    },
    {
        'identifier': 'https://youtu.be/watch?v=07FYdnEawAQ',
        'videoid': '07FYdnEawAQ',
        'title': 'Justin Timberlake - Tunnel Vision (Explicit)',
        'length': 419,
        'duration': '00:06:59',
        'author': 'justintimberlakeVEVO',
        'username': 'justintimberlakeVEVO',
        'published': '2013-07-03 22:00:16',
        'thumb': 'http://i1.ytimg.com/vi/07FYdnEawAQ/default.jpg',
        'category': 'Music',
        'description': '55e8e6e2b219712bf94d67c2434530474a503265',
        'bestsize': 79885533,
        'all streams': 21,
        'normal streams': 6,
        'video streams': 13,
        'audio streams': 2,
        'ogg streams': 1,
        'm4a streams': 1,
    },
    {
        'identifier': 'EnHp24CVORc',
        'videoid': 'EnHp24CVORc',
        'title': 'Chinese Knock Off Sky Loop Roller Coaster POV Chuanlord Holiday Manor China \u9b54\u73af\u5782\u76f4\u8fc7\u5c71\u8f66',
        'length': 313,
        'duration': '00:05:13',
        'author': 'Theme Park Review',
        'username': 'themeparkreviewTPR',
        'published': '2014-05-05 19:58:07',
        'thumb': 'http://i1.ytimg.com/vi/EnHp24CVORc/default.jpg',
        'category': 'People',
        'description': '3c884d9791be15646ddf351edffcb2dd22ec70f8',
        'bestsize': 101083389,
        'all streams': 19,
        'normal streams': 6,
        'video streams': 11,
        'audio streams': 2,
        'ogg streams': 1,
        'm4a streams': 1,
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
        'thumb': 'http://i1.ytimg.com/vi/rYEDA3JcQqw/default.jpg',
        'category': 'Music',
        'description': '72bfd9472e59a8f48b83af36197ebcf5d2227609',
        'bestsize': 41334333,
        'all streams': 27,
        'normal streams': 6,
        'video streams': 19,
        'audio streams': 2,
        'ogg streams': 1,
        'm4a streams': 1,
    }
]

if __name__ == "__main__":
    unittest.main(verbosity=2)
    #unittest.main()
