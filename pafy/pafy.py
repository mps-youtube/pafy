# -*- coding: utf-8 -*-

"""
Python API for YouTube.

https://github.com/np1/pafy

Copyright (C)  2013-2014 nagev

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""


from __future__ import unicode_literals

__version__ = "0.3.46"
__author__ = "nagev"
__license__ = "GPLv3"


import re
import os
import sys
import time
import json
import logging
from xml.etree import ElementTree


early_py_version = sys.version_info[:2] < (2, 7)

if sys.version_info[:2] >= (3, 0):
    # pylint: disable=E0611,F0401,I0011
    from urllib.request import build_opener
    from urllib.error import HTTPError, URLError
    from urllib.parse import parse_qs, unquote_plus
    uni, pyver = str, 3

else:
    from urllib2 import build_opener, HTTPError, URLError
    from urllib import unquote_plus
    from urlparse import parse_qs
    uni, pyver = unicode, 2


if os.environ.get("pafydebug") == "1":
    logging.basicConfig(level=logging.DEBUG)

dbg = logging.debug


def parseqs(data):
    """ parse_qs, return unicode. """
    if type(data) == uni:
        return parse_qs(data)

    elif pyver == 3:
        data = data.decode("utf8")
        data = parse_qs(data)

    else:
        data = parse_qs(data)
        out = {}

        for k, v in data.items():
            k = k.decode("utf8")
            out[k] = [x.decode("utf8") for x in v]
            data = out

    return data


def fetch_decode(url):
    """ Fetch url and decode. """
    req = g.opener.open(url)
    ct = req.headers['content-type']

    if "charset=" in ct:
        encoding = re.search(r"charset=([\w-]+)\s*(:?;|$)", ct).group(1)
        dbg("encoding: %s", ct)
        return req.read().decode(encoding)

    else:
        return req.read()


def new(url, basic=True, gdata=False, signature=True, size=False,
        callback=None):
    """ Return a new pafy instance given a url or video id.

    Optional arguments:
        basic - fetch basic metadata and streams
        gdata - fetch gdata info (upload date, description, category)
        signature - fetch data required to decrypt urls, if encrypted
        size - fetch the size of each stream (slow)(decrypts urls if needed)
        callback - a callback function to receive status strings

    If any of the first four above arguments are False, those data items will
    be fetched only when first called for.

    The defaults are recommended for most cases. If you wish to create
    many video objects at once, you may want to set all to False, eg:

        video = pafy.new(basic=False, signature=False)

    This will be quick because no http requests will be made on initialisation.

    Setting signature or size to True will override the basic argument
    and force basic data to be fetched too (basic data is required to
    obtain Stream objects and determine whether signatures are encrypted.

    Similarly, setting size to true will force the signature data to be
    fetched if the videos have encrypted signatures, so will override the
    value set in the signature argument.

    """
    return Pafy(url, basic, gdata, signature, size, callback)


def get_video_info(video_id, newurl=None):
    """ Return info for video_id.  Returns dict. """
    url = g.urls['vidinfo'] % video_id
    url = newurl if newurl else url
    info = fetch_decode(url)  # bytes
    info = parseqs(info)  # unicode dict
    dbg("Fetched video info")

    if info['status'][0] == "fail":
        reason = info['reason'][0] or "Bad video argument"
        raise IOError("Youtube says: %s [%s]" % (reason, video_id))

    return info


def get_video_gdata(video_id):
    """ Return xml string containing video metadata from gdata api. """
    new.callback("Fetching video gdata")
    url = g.urls['gdata'] % video_id
    gdata = fetch_decode(url)  # unicode
    dbg("Fetched video gdata")
    new.callback("Fetched video gdata")
    return gdata


def extract_video_id(url):
    """ Extract the video id from a url, return video id as str. """
    ok = (r"\w-",) * 3
    regx = re.compile(r'(?:^|[^%s]+)([%s]{11})(?:[^%s]+|$)' % ok)
    url = str(url)
    m = regx.search(url)

    if not m:
        err = "Need 11 character video id or the URL of the video. Got %s"
        raise ValueError(err % url)

    vidid = m.group(1)
    return vidid


class g(object):

    """ Class for holding constants needed throughout the module. """

    urls = {
        'gdata': "http://gdata.youtube.com/feeds/api/videos/%s?v=2",
        'watchv': "http://www.youtube.com/watch?v=%s",
        'vidinfo': ('http://www.youtube.com/get_video_info?'
                    'video_id=%s&asv=3&el=detailpage&hl=en_US'),
        'playlist': ('http://www.youtube.com/list_ajax?'
                     'style=json&action_get_list=1&list=%s'),
        'age_vidinfo': ('https://www.youtube.com/get_video_info?video_id=%s&'
                        'el=player_embedded&gl=US&hl=en&eurl=https://youtube.'
                        'googleapis.com/v/%s&asv=3&sts=1588')
    }
    ua = ("Mozilla/5.0 (compatible; MSIE 9.0; Windows NT 6.1; WOW64;"
          " Trident/5.0)")
    UEFSM = 'url_encoded_fmt_stream_map'
    AF = 'adaptive_fmts'
    jsplayer = r';\s*ytplayer\.config\s*=\s*(\s*{.*?}\s*)\s*;'
    lifespan = 60 * 60 * 5  # 5 hours
    opener = build_opener()
    opener.addheaders = [('User-Agent', ua)]
    itags = {
        '5': ('320x240', 'flv', "normal", ''),
        '17': ('176x144', '3gp', "normal", ''),
        '18': ('640x360', 'mp4', "normal", ''),
        '22': ('1280x720', 'mp4', "normal", ''),
        '34': ('640x360', 'flv', "normal", ''),
        '35': ('854x480', 'flv', "normal", ''),
        '36': ('320x240', '3gp', "normal", ''),
        '37': ('1920x1080', 'mp4', "normal", ''),
        '38': ('4096x3072', 'mp4', "normal", '4:3 hi-res'),
        '43': ('640x360', 'webm', "normal", ''),
        '44': ('854x480', 'webm', "normal", ''),
        '45': ('1280x720', 'webm', "normal", ''),
        '46': ('1920x1080', 'webm', "normal", ''),

        # '59': ('1x1', 'mp4', 'normal', ''),
        # '78': ('1x1', 'mp4', 'normal', ''),

        '82': ('640x360-3D', 'mp4', "normal", ''),
        '83': ('640x480-3D', 'mp4', 'normal', ''),
        '84': ('1280x720-3D', 'mp4', "normal", ''),
        '100': ('640x360-3D', 'webm', "normal", ''),
        '102': ('1280x720-3D', 'webm', "normal", ''),
        '133': ('426x240', 'm4v', 'video', ''),
        '134': ('640x360', 'm4v', 'video', ''),
        '135': ('854x480', 'm4v', 'video', ''),
        '136': ('1280x720', 'm4v', 'video', ''),
        '137': ('1920x1080', 'm4v', 'video', ''),
        '138': ('4096x3072', 'm4v', 'video', ''),
        '139': ('48k', 'm4a', 'audio', ''),
        '140': ('128k', 'm4a', 'audio', ''),
        '141': ('256k', 'm4a', 'audio', ''),
        '160': ('256x144', 'm4v', 'video', ''),
        '167': ('640x480', 'webm', 'video', ''),
        '168': ('854x480', 'webm', 'video', ''),
        '169': ('1280x720', 'webm', 'video', ''),
        '170': ('1920x1080', 'webm', 'video', ''),
        '171': ('128k', 'ogg', 'audio', ''),
        '172': ('192k', 'ogg', 'audio', ''),
        '242': ('360x240', 'webm', 'video', 'VP9'),
        '243': ('480x360', 'webm', 'video', 'VP9'),
        '244': ('640x480', 'webm', 'video', 'VP9'),
        '245': ('640x480', 'webm', 'video', 'VP9'),
        '246': ('640x480', 'webm', 'video', 'VP9'),
        '247': ('720x480', 'webm', 'video', 'VP9'),
        '248': ('1920x1080', 'webm', 'video', 'VP9'),
        '256': ('192k', 'm4a', 'audio', '6-channel'),
        '258': ('320k', 'm4a', 'audio', '6-channel'),
        '264': ('2560x1440', 'm4v', 'video', '')
    }


def _extract_smap(map_name, dic, zero_idx=True):
    """ Extract stream map, returns list of dicts. """
    if map_name in dic:
        smap = dic.get(map_name)
        smap = smap[0] if zero_idx else smap
        smap = smap.split(",")
        smap = [parseqs(x) for x in smap]
        return [dict((k, v[0]) for k, v in x.items()) for x in smap]

    return []


def _extract_function_from_js(name, js):
    """ Find a function definition called `name` and extract components.

    Return a dict representation of the function.

    """
    dbg("Extracting function '%s' from javascript", name)
    fpattern = r'function\s+%s\(((?:\w+,?)+)\)\{([^}]+)\}'
    m = re.search(fpattern % re.escape(name), js)
    args, body = m.groups()
    dbg("extracted function %s(%s){%s};", name, args, body)
    func = {'name': name, 'parameters': args.split(","), 'body': body}
    return func


def _get_mainfunc_from_js(js):
    """ Return main signature decryption function from javascript as dict. """
    dbg("Scanning js for main function.")
    m = re.search(r'\w\.sig\|\|(\w+)\(\w+\.\w+\)', js)
    funcname = m.group(1)
    dbg("Found main function: %s", funcname)
    function = _extract_function_from_js(funcname, js)
    return function


def _get_other_funcs(primary_func, js):
    """ Return all secondary functions used in primary_func. """
    dbg("scanning javascript for secondary functions.")
    body = primary_func['body']
    body = body.split(";")
    call = re.compile(r'(?:[$\w+])=([$\w]+)\(((?:\w+,?)+)\)$')

    functions = {}

    for part in body:

        # is this a function?
        if call.match(part):
            match = call.match(part)
            name = match.group(1)
            # dbg("found secondary function '%s'", name)

            if name not in functions:
                # extract from javascript if not previously done
                functions[name] = _extract_function_from_js(name, js)

            # else:
                # dbg("function '%s' is already in map.", name)

    return functions


def _getval(val, argsdict):
    """ resolve variable values, preserve int literals. Return dict."""
    m = re.match(r'(\d+)', val)

    if m:
        return int(m.group(1))

    elif val in argsdict:
        return argsdict[val]

    else:
        raise IOError("Error val %s from dict %s" % (val, argsdict))


def _get_func_from_call(caller, name, arguments, js_url):
    """
    Return called function complete with called args given a caller function .

    This function requires that Pafy.funcmap contains the function `name`.
    It retrieves the function and fills in the parameter values as called in
    the caller, returning them in the returned newfunction `args` dict

    """
    newfunction = Pafy.funcmap[js_url][name]
    newfunction['args'] = {}

    for n, arg in enumerate(arguments):
        value = _getval(arg, caller['args'])
        param = newfunction['parameters'][n]
        newfunction['args'][param] = value

    return newfunction


def _solve(f, js_url):
    """Solve basic javascript function. Return solution value (str). """
    # pylint: disable=R0914
    patterns = {
        'split_or_join': r'(\w+)=\1\.(?:split|join)\(""\)$',
        'func_call': r'(\w+)=([$\w]+)\(((?:\w+,?)+)\)$',
        'x1': r'var\s(\w+)=(\w+)\[(\w+)\]$',
        'x2': r'(\w+)\[(\w+)\]=(\w+)\[(\w+)\%(\w+)\.length\]$',
        'x3': r'(\w+)\[(\w+)\]=(\w+)$',
        'return': r'return (\w+)(\.join\(""\))?$',
        'reverse': r'(\w+)=(\w+)\.reverse\(\)$',
        'slice': r'(\w+)=(\w+)\.slice\((\w+)\)$'
    }

    parts = f['body'].split(";")

    for part in parts:
        # dbg("Working on part: " + part)

        name = ""

        for n, p in patterns.items():
            m, name = re.match(p, part), n

            if m:
                break
        else:
            raise IOError("no match for %s" % part)

        if name == "split_or_join":
            pass

        elif name == "func_call":
            lhs, funcname, args = m.group(1, 2, 3)
            newfunc = _get_func_from_call(f, funcname, args.split(","), js_url)
            f['args'][lhs] = _solve(newfunc, js_url)  # recursive call

        # new var is an index of another var; eg: var a = b[c]
        elif name == "x1":
            b, c = [_getval(x, f['args']) for x in m.group(2, 3)]
            f['args'][m.group(1)] = b[c]

        # a[b]=c[d%e.length]
        elif name == "x2":
            vals = m.group(*range(1, 6))
            a, b, c, d, e = [_getval(x, f['args']) for x in vals]
            f['args'][m.group(1)] = a[:b] + c[d % len(e)] + a[b + 1:]

        # a[b]=c
        elif name == "x3":
            a, b, c = [_getval(x, f['args']) for x in m.group(1, 2, 3)]
            f['args'][m.group(1)] = a[:b] + c + a[b + 1:]  # a[b] = c

        elif name == "return":
            return f['args'][m.group(1)]

        elif name == "reverse":
            f['args'][m.group(1)] = _getval(m.group(2), f['args'])[::-1]

        elif name == "slice":
            a, b, c = [_getval(x, f['args']) for x in m.group(1, 2, 3)]
            f['args'][m.group(1)] = b[c:]

    raise IOError("Processed js funtion parts without finding return")


def _decodesig(sig, js_url):
    """  Return decrypted sig given an encrypted sig and js_url key. """
    # lookup main function in Pafy.funcmap dict
    mainfunction = Pafy.funcmap[js_url]['mainfunction']
    param = mainfunction['parameters']

    if not len(param) == 1:
        raise IOError("Main sig js function has more than one arg: %s" % param)

    # fill in function argument with signature
    mainfunction['args'] = {param[0]: sig}
    new.callback("Decrypting signature")
    solved = _solve(mainfunction, js_url)
    dbg("Decrypted sig = %s...", solved[:30])
    new.callback("Decrypted signature")
    return solved


def get_js_sm(video_id):
    """ Fetch watchinfo page and extract stream map and js funcs if not known.

    This function is needed by videos with encrypted signatures.
    If the js url referred to in the watchv page is not a key in Pafy.funcmap,
    the javascript is fetched and functions extracted.

    Returns streammap (list of dicts), js url (str)  and funcs (dict)

    """
    watch_url = g.urls['watchv'] % video_id
    new.callback("Fetching watchv page")
    watchinfo = fetch_decode(watch_url)  # unicode

    if re.search(r'player-age-gate-content">', watchinfo) is not None:
        # create a new Pafy object
        dbg("creating new instance for age restrictved video")
        doppleganger = new(video_id, False, False, False)
        video_info_url = g.urls['age_vidinfo'] % (video_id, video_id)
        doppleganger.fetch_basic(ageurl=video_info_url)
        return "age", "age", doppleganger

    dbg("Fetched watchv page")
    new.callback("Fetched watchv page")
    m = re.search(g.jsplayer, watchinfo)
    myjson = json.loads(m.group(1))
    stream_info = myjson['args']
    smap = _extract_smap(g.UEFSM, stream_info, False)
    smap += _extract_smap(g.AF, stream_info, False)
    js_url = myjson['assets']['js']
    js_url = "https:" + js_url if js_url.startswith("//") else js_url
    funcs = Pafy.funcmap.get(js_url)

    if not funcs:
        new.callback("Fetching javascript")
        javascript = fetch_decode(js_url)  # bytes
        javascript = javascript.decode("utf8")  # unicode
        dbg("Fetched javascript")
        new.callback("Fetched javascript")
        mainfunc = _get_mainfunc_from_js(javascript)
        funcs = _get_other_funcs(mainfunc, javascript)
        funcs['mainfunction'] = mainfunc

    return smap, js_url, funcs


def _make_url(raw, sig, quick=True):
    """ Return usable url. Set quick=False to disable ratebypass override. """
    if quick and "ratebypass=" not in raw:
        raw += "&ratebypass=yes"

    if "signature=" not in raw:

        if not sig:
            raise IOError("Error retrieving url")

        raw += "&signature=" + sig

    return raw


def gen_ageurl(dop, itag):
    """ Decrypt signature for age-restricted item. Return url. """
    for x in dop.sm + dop.asm:

        if x['itag'] == itag and len(x['s']) == 86:
            s = x['s']
            s = s[2:63] + s[82] + s[64:82] + s[63]
            dbg("decrypted agesig: %s%s", s[:22], "..")
            return _make_url(x['url'], s)


def _get_matching_stream(smap, itag):
    """ Return the url and signature for a stream matching itag in smap. """
    for x in smap:

        if x['itag'] == itag:
            return x['url'], x.get('s')

    raise IOError("Error fetching stream")


class Stream(object):

    """ YouTube video stream class. """

    def __init__(self, sm, parent):
        """ Set initial values. """
        safeint = lambda x: int(x) if x.isdigit() else x

        self._itag = sm['itag']
        self._threed = 'stereo3d' in sm and sm['stereo3d'] == '1'
        self._resolution = g.itags[self.itag][0]
        self._dimensions = tuple(self.resolution.split("-")[0].split("x"))
        self._dimensions = tuple(map(safeint, self.dimensions))
        self._vidformat = sm['type'].split(';')[0]  # undocumented
        self._quality = self.resolution
        self._extension = g.itags[self.itag][1]
        self._title = parent.title
        self.encrypted = 's' in sm
        self._parent = parent
        self._filename = self.title + "." + self.extension
        self._fsize = None
        self._bitrate = self._rawbitrate = None
        self._mediatype = g.itags[self.itag][2]
        self._notes = g.itags[self.itag][3]
        self._url = None
        self._rawurl = sm['url']
        self._sig = sm['s'] if self.encrypted else sm.get("sig")

        if self.mediatype == "audio":
            self._dimensions = (0, 0)
            self._bitrate = self.resolution
            self._quality = self.bitrate
            self._resolution = "0x0"
            self._rawbitrate = int(sm["bitrate"])

    @property
    def rawbitrate(self):
        """ Return raw bitrate value. """
        return self._rawbitrate

    @property
    def threed(self):
        """ Return bool, True if stream is 3D. """
        return self._threed

    @property
    def itag(self):
        """ Return itag value of stream. """
        return self._itag

    @property
    def resolution(self):
        """ Return resolution of stream as str. 0x0 if audio. """
        return self._resolution

    @property
    def dimensions(self):
        """ Return dimensions of stream as tuple.  (0, 0) if audio. """
        return self._dimensions

    @property
    def quality(self):
        """ Return quality of stream (bitrate or resolution).

        eg, 128k or 640x480 (str)
        """
        return self._quality

    @property
    def title(self):
        """ Return YouTube video title as a string. """
        return self._title

    @property
    def extension(self):
        """ Return appropriate file extension for stream (str).

        Possible values are: 3gp, m4a, m4v, mp4, webm, ogg
        """
        return self._extension

    @property
    def bitrate(self):
        """ Return bitrate of an audio stream. """
        return self._bitrate

    @property
    def mediatype(self):
        """ Return mediatype string (normal, audio or video).

        (normal means a stream containing both video and audio.)
        """
        return self._mediatype

    @property
    def notes(self):
        """ Return additional notes regarding the stream format. """
        return self._notes

    @property
    def filename(self):
        """ Return filename of stream; derived from title and extension. """
        return self._filename

    @property
    def url(self):
        """ Return the url, decrypt if required. """
        if self._url:
            pass

        elif self._parent.age:
            self._url = gen_ageurl(self._parent.doppleganger, self.itag)

        elif not self.encrypted:
            self._url = _make_url(self._rawurl, self._sig)

        else:
            # encrypted url signatures
            if self._parent.js_url:
                # dbg("using cached js %s" % self._parent.js_url[-15:])
                enc_streams = self._parent.enc_streams

            else:
                enc_streams, js_url, funcs = get_js_sm(self._parent.videoid)
                self._parent.expiry = time.time() + g.lifespan
                self._parent.js_url = js_url

                # check for age
                if type(enc_streams) == uni and enc_streams == "age":
                    self._parent.age = True
                    dop = self._parent.doppleganger = funcs
                    self._url = gen_ageurl(dop, self.itag)
                    return self._url

                # Create Pafy funcmap dict for this js_url
                if not Pafy.funcmap.get(js_url):
                    Pafy.funcmap[js_url] = funcs

                # else:
                    # Add javascript functions to Pafy funcmap dict
                    # in case same js_url has different functions
                    # Pafy.funcmap[js_url].update(funcs)

                # Stash usable urls and encrypted sigs in parent Pafy object
                self._parent.enc_streams = enc_streams

            url, s = _get_matching_stream(enc_streams, self.itag)
            sig = _decodesig(s, self._parent.js_url) if s else None
            self._url = _make_url(url, sig)

        return self._url

    def __repr__(self):
        """ Return string representation. """
        out = "%s:%s@%s" % (self.mediatype, self.extension, self.quality)
        return out

    def get_filesize(self):
        """ Return filesize of the stream in bytes.  Set member variable. """
        if not self._fsize:

            try:
                dbg("Getting stream size")
                cl = "content-length"
                self._fsize = int(g.opener.open(self.url).headers[cl])
                dbg("Got stream size")

            except (AttributeError, HTTPError, URLError):
                self._fsize = 0

        return self._fsize

    def download(self, filepath="", quiet=False, callback=None):
        """ Download.  Use quiet=True to supress output. Return filename. """
        # pylint: disable=R0914
        # Too many local variables - who cares?
        status_string = ('  {:,} Bytes [{:.2%}] received. Rate: [{:4.0f} '
                         'KB/s].  ETA: [{:.0f} secs]')

        if early_py_version:
            status_string = ('  {0:} Bytes [{1:.2%}] received. Rate:'
                             ' [{2:4.0f} KB/s].  ETA: [{3:.0f} secs]')

        response = g.opener.open(self.url)
        total = int(response.info()['Content-Length'].strip())
        chunksize, bytesdone, t0 = 16384, 0, time.time()
        fname = filepath or self.filename

        try:
            outfh = open(fname, 'wb')

        except IOError:
            ok = re.compile(r'[^\\/?*$\'"%&:<>|]')
            fname = "".join(x if ok.match(x) else "_" for x in self.filename)
            outfh = open(fname.encode("utf8", "ignore"), 'wb')

        while True:
            chunk = response.read(chunksize)
            outfh.write(chunk)
            elapsed = time.time() - t0
            bytesdone += len(chunk)
            rate = (bytesdone / 1024) / elapsed
            eta = (total - bytesdone) / (rate * 1024)
            progress_stats = (bytesdone, bytesdone * 1.0 / total, rate, eta)

            if not chunk:
                outfh.close()
                break

            if not quiet:
                status = status_string.format(*progress_stats)
                sys.stdout.write("\r" + status + ' ' * 4 + "\r")
                sys.stdout.flush()

            if callback:
                callback(total, *progress_stats)

        return fname


class Pafy(object):

    """ Class to represent a YouTube video. """

    funcmap = {}  # keep functions as a class variable

    def __init__(self, video_url, basic=True, gdata=False,
                 signature=True, size=False, callback=None):
        """ Set initial values. """
        self.version = __version__
        self.videoid = extract_video_id(video_url)
        self.watchv_url = g.urls['watchv'] % self.videoid

        nullf = lambda x: None
        new.callback = callback or nullf
        self._have_basic = False
        self._have_gdata = False

        self._description = None
        self._category = None
        self._published = None
        self._username = None

        self.sm = []
        self.asm = []
        self.js_url = None  # if js_url is set then has new stream map
        self.age = False
        self._streams = []
        self._oggstreams = []
        self._m4astreams = []
        self._allstreams = []
        self._videostreams = []
        self._audiostreams = []

        self._title = None
        self._thumb = None
        self._rating = None
        self._length = None
        self._author = None
        self._formats = None
        self._videoid = None
        self.ciphertag = None  # used by Stream class in url property def
        self._duration = None
        self._keywords = None
        self._bigthumb = None
        self._viewcount = None
        self._bigthumbhd = None
        self.expiry = None
        self.playlist_meta = None

        if basic:
            self.fetch_basic()

        if gdata:
            self._fetch_gdata()

        if signature:
            # pylint: disable=W0104
            s = self.streams

            if self.ciphertag:
                s[0].url  # forces signature decryption

        if size:

            for s in self.allstreams:
                # pylint: disable=W0104
                s.get_filesize()

    def fetch_basic(self, ageurl=None):
        """ Fetch info url page and set member vars. """
        if self._have_basic:
            return

        if ageurl:
            allinfo = get_video_info("none", ageurl)

        else:
            allinfo = get_video_info(self.videoid)

        new.callback("Fetched video info")
        f = lambda x: allinfo.get(x, ["unknown"])[0]
        t = lambda x: allinfo.get(x, [0.0])[0]
        z = lambda x: allinfo.get(x, [""])[0]

        self._title = f('title').replace("/", "-")
        self._author = f('author')
        self._videoid = f('video_id')
        self._rating = float(t('avg_rating'))
        self._length = int(f('length_seconds'))
        self._viewcount = int(f('view_count'))
        self._thumb = unquote_plus(f('thumbnail_url'))
        self._formats = [x.split("/") for x in f('fmt_list').split(",")]
        self._keywords = z('keywords').split(',')
        self._bigthumb = z('iurlsd')
        self._bigthumbhd = z('iurlsdmaxres')
        self.ciphertag = f("use_cipher_signature") == "True"

        if ageurl:
            self.ciphertag = False
            dbg("Encrypted signature detected - age restricted")

        if self.ciphertag:
            dbg("Encrypted signature detected.")

        # extract stream maps
        self.sm = _extract_smap(g.UEFSM, allinfo, not self.js_url)
        self.asm = _extract_smap(g.AF, allinfo, not self.js_url)

        self._have_basic = 1
        self._process_streams()
        self.expiry = time.time() + g.lifespan

    def _fetch_gdata(self):
        """ Extract gdata values, fetch gdata if necessary. """
        if self._have_gdata:
            return

        gdata = get_video_gdata(self.videoid)
        t0 = "{http://search.yahoo.com/mrss/}"
        t1 = "{http://www.w3.org/2005/Atom}"
        t2 = "{http://gdata.youtube.com/schemas/2007}"
        gdata = gdata.encode("utf8")
        tree = ElementTree.fromstring(gdata)
        groups = tree.find(t0 + "group")
        published = uni(tree.find(t1 + "published").text)
        rating = tree.find(t2 + "rating")  # already exists in basic data
        likes = int(rating.get("numLikes") if rating is not None else 0)
        dislikes = int(rating.get("numDislikes") if rating is not None else 0)
        description = uni(groups.find(t0 + "description").text)
        category = uni(groups.find(t0 + "category").text)
        username = tree.find(t1 + "author/" + t1 + "uri").text.split("/")[-1]
        setattr(self, "_username", username)
        setattr(self, "_published", published)
        setattr(self, "_description", description)
        setattr(self, "_category", category)
        setattr(self, "_likes", likes)
        setattr(self, "_dislikes", dislikes)

        self._have_gdata = 1

    def _process_streams(self):
        """ Create Stream object lists from internal stream maps. """
        if not self._have_basic:
            self.fetch_basic()

        streams = [Stream(z, self) for z in self.sm]
        adpt_streams = [Stream(z, self) for z in self.asm]
        audiostreams = [x for x in adpt_streams if x.bitrate]
        videostreams = [x for x in adpt_streams if not x.bitrate]
        m4astreams = [x for x in audiostreams if x.extension == "m4a"]
        oggstreams = [x for x in audiostreams if x.extension == "ogg"]
        self._streams = streams
        self._audiostreams = audiostreams
        self._videostreams = videostreams
        self._m4astreams, self._oggstreams = m4astreams, oggstreams
        self._allstreams = streams + videostreams + audiostreams

    def __repr__(self):
        """ Print video metadata. Return utf8 string. """
        if self._have_basic:
            keys = "Title Author ID Duration Rating Views Thumbnail Keywords"
            keys = keys.split(" ")
            keywords = ", ".join(self.keywords)
            info = {"Title": self.title,
                    "Author": self.author,
                    "Views": self.viewcount,
                    "Rating": self.rating,
                    "Duration": self.duration,
                    "ID": self.videoid,
                    "Thumbnail": self.thumb,
                    "Keywords": keywords}

            nfo = "\n".join(["%s: %s" % (k, info.get(k, "")) for k in keys])

        else:
            nfo = "Pafy object: %s [%s]" % (self.videoid,
                                            self.title[:45] + "..")

        return nfo.encode("utf8", "replace") if pyver == 2 else nfo

    @property
    def streams(self):
        """ The streams for a video. Returns list."""
        self.fetch_basic()
        return self._streams

    @property
    def allstreams(self):
        """ All stream types for a video. Returns list. """
        self.fetch_basic()
        return self._allstreams

    @property
    def audiostreams(self):
        """ Return a list of audio Stream objects. """
        self.fetch_basic()
        return self._audiostreams

    @property
    def videostreams(self):
        """ The video streams for a video. Returns list. """
        self.fetch_basic()
        return self._videostreams

    @property
    def oggstreams(self):
        """ Return a list of ogg encoded Stream objects. """
        self.fetch_basic()
        return self._oggstreams

    @property
    def m4astreams(self):
        """ Return a list of m4a encoded Stream objects. """
        self.fetch_basic()
        return self._m4astreams

    @property
    def title(self):
        """ Return YouTube video title as a string. """
        if not self._title:
            self.fetch_basic()

        return self._title

    @property
    def author(self):
        """ The uploader of the video. Returns str. """
        if not self._author:
            self.fetch_basic()

        return self._author

    @property
    def rating(self):
        """ Rating for a video. Returns float. """
        if not self._rating:
            self.fetch_basic()

        return self._rating

    @property
    def length(self):
        """ Length of a video in seconds. Returns int. """
        if not self._length:
            self.fetch_basic()

        return self._length

    @property
    def viewcount(self):
        """ Number of views for a video. Returns int. """
        if not self._viewcount:
            self.fetch_basic()

        return self._viewcount

    @property
    def bigthumb(self):
        """ Large thumbnail image url. Returns str. """
        self.fetch_basic()
        return self._bigthumb

    @property
    def bigthumbhd(self):
        """ Extra large thumbnail image url. Returns str. """
        self.fetch_basic()
        return self._bigthumbhd

    @property
    def thumb(self):
        """ Thumbnail image url. Returns str. """
        if not self._thumb:
            self.fetch_basic()

        return self._thumb

    @property
    def duration(self):
        """ Duration of a video (HH:MM:SS). Returns str. """
        if not self._length:
            self.fetch_basic()

        self._duration = time.strftime('%H:%M:%S', time.gmtime(self._length))
        self._duration = uni(self._duration)

        return self._duration

    @property
    def keywords(self):
        """ Return keywords as list of str. """
        self.fetch_basic()
        return self._keywords

    @property
    def category(self):
        """ YouTube category of the video. Returns string. """
        self._fetch_gdata()
        return self._category

    @property
    def description(self):
        """ Description of the video. Returns string. """
        if not self._description:
            self._fetch_gdata()

        return self._description

    @property
    def username(self):
        """ Return the username of the uploader. """
        self._fetch_gdata()
        return self._username

    @property
    def published(self):
        """ The upload date and time of the video. Returns string. """
        self._fetch_gdata()
        return self._published.replace(".000Z", "").replace("T", " ")

    @property
    def likes(self):
        """ The number of likes for the video. Returns int. """
        self._fetch_gdata()
        return self._likes

    @property
    def dislikes(self):
        """ The number of dislikes for the video. Returns int. """
        self._fetch_gdata()
        return self._dislikes

    def getbest(self, preftype="any", ftypestrict=True):
        """
        Return the best resolution available.

        set ftypestrict to False to use a non preferred format if that
        has a higher resolution
        """
        if not self.streams:
            return None

        def _sortkey(x, key3d=0, keyres=0, keyftype=0):
            """ sort function for max(). """
            key3d = "3D" not in x.resolution
            keyres = int(x.resolution.split("x")[0])
            keyftype = preftype == x.extension
            strict = (key3d, keyftype, keyres)
            nonstrict = (key3d, keyres, keyftype)
            return strict if ftypestrict else nonstrict

        r = max(self.streams, key=_sortkey)

        if ftypestrict and preftype != "any" and r.extension != preftype:
            return None

        else:
            return r

    def getbestaudio(self, preftype="any", ftypestrict=True):
        """ Return the highest bitrate audio Stream object."""
        if not self.audiostreams:
            return None

        def _sortkey(x, keybitrate=0, keyftype=0):
            """ Sort function for max(). """
            keybitrate = int(x.rawbitrate)
            keyftype = preftype == x.extension
            strict, nonstrict = (keyftype, keybitrate), (keybitrate, keyftype)
            return strict if ftypestrict else nonstrict

        r = max(self.audiostreams, key=_sortkey)

        if ftypestrict and preftype != "any" and r.extension != preftype:
            return None

        else:
            return r

    def populate_from_playlist(self, pl_data):
        """ Populate Pafy object with items fetched from playlist data. """
        self._title = pl_data.get("title")
        self._author = pl_data.get("author")
        self._length = int(pl_data.get("length_seconds", 0))
        self._rating = pl_data.get("rating", 0.0)
        self._viewcount = "".join(re.findall(r"\d", pl_data.get("views", "0")))
        self._viewcount = int(self._viewcount)
        self._thumb = pl_data.get("thumbnail")
        self._description = pl_data.get("description")
        self.playlist_meta = pl_data


def get_playlist(playlist_url, basic=False, gdata=False, signature=False,
                 size=False, callback=None):
    """ Return a dict containing Pafy objects from a YouTube Playlist.

    The returned Pafy objects are initialised using the arguments to
    get_playlist() in the manner documented for pafy.new()

    """
    # pylint: disable=R0914
    # too many local vars
    nullf = lambda x: None
    callback = callback or nullf
    x = (r"-_0-9a-zA-Z",) * 2 + (r'(?:\&|\#.{1,1000})',)
    regx = re.compile(r'(?:^|[^%s]+)([%s]{18,})(?:%s|$)' % x)
    m = regx.search(playlist_url)

    if not m:
        err = "Unrecognized playlist url: %s"
        raise ValueError(err % playlist_url)

    playlist_id = m.group(1)
    url = g.urls["playlist"] % playlist_id

    try:
        allinfo = fetch_decode(url)  # unicode
        allinfo = json.loads(allinfo)

    except:
        raise IOError("Error fetching playlist %s" % m.groups(0))

    # playlist specific metadata
    playlist = dict(
        playlist_id=playlist_id,
        likes=allinfo.get('likes'),
        title=allinfo.get('title'),
        author=allinfo.get('author'),
        dislikes=allinfo.get('dislikes'),
        description=allinfo.get('description'),
        items=[]
    )

    # playlist items specific metadata
    for v in allinfo['video']:

        vid_data = dict(
            added=v.get('added'),
            is_cc=v.get('is_cc'),
            is_hd=v.get('is_hd'),
            likes=v.get('likes'),
            title=v.get('title'),
            views=v.get('views'),
            rating=v.get('rating'),
            author=v.get('author'),
            user_id=v.get('user_id'),
            privacy=v.get('privacy'),
            dislikes=v.get('dislikes'),
            duration=v.get('duration'),
            comments=v.get('comments'),
            keywords=v.get('keywords'),
            thumbnail=v.get('thumbnail'),
            cc_license=v.get('cc_license'),
            category_id=v.get('category_id'),
            description=v.get('description'),
            encrypted_id=v.get('encrypted_id'),
            time_created=v.get('time_created'),
            time_updated=v.get('time_updated'),
            length_seconds=v.get('length_seconds')
        )

        try:
            pafy_obj = new(vid_data['encrypted_id'],
                           basic=basic,
                           gdata=gdata,
                           signature=signature,
                           size=size,
                           callback=callback)

        except IOError as e:
            callback("%s: %s" % (v['title'], e.message))
            continue

        pafy_obj.populate_from_playlist(vid_data)
        playlist['items'].append(dict(pafy=pafy_obj,
                                      playlist_meta=vid_data))
        callback("Added video: %s" % v['title'])

    return playlist
