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

__version__ = "0.3.37"
__author__ = "nagev"
__license__ = "GPLv3"


import re
import os
import sys
import time
import json
import logging
from xml.etree import ElementTree as etree

decode_if_py3 = lambda x: x.decode("utf8")

if sys.version_info[:2] >= (3, 0):
    # pylint: disable=E0611,F0401,I0011
    from urllib.request import build_opener
    from urllib.error import HTTPError, URLError
    from urllib.parse import parse_qs, unquote_plus

else:
    decode_if_py3 = lambda x: x
    from urllib2 import build_opener, HTTPError, URLError
    from urllib import unquote_plus
    from urlparse import parse_qs


if os.environ.get("pafydebug") == "1":
    logging.basicConfig(level=logging.DEBUG)

dbg = logging.debug


def make_url(raw, sig, quick=True):
    """ Construct url. """

    if quick and not "ratebypass=" in raw:
        raw += "&ratebypass=yes"

    if not "signature=" in raw:
        raw += "&signature=" + sig

    return raw


def new(url, basic=True, gdata=False, signature=True, size=False,
        callback=None):
    """ Return a new pafy instance given a url or video id. """

    return Pafy(url, basic, gdata, signature, size, callback)


class g(object):

    """ Class for holding vars / lambdas needed throughout the module. """

    urls = {
        'gdata': "https://gdata.youtube.com/feeds/api/videos/%s?v=2",
        'watchv': "https://www.youtube.com/watch?v=%s",
        'vidinfo': ('https://www.youtube.com/get_video_info?'
                    'video_id=%s&asv=3&el=detailpage&hl=en_US'),
        'playlist': ('http://www.youtube.com/list_ajax?',
                     'style=json&action_get_list=1&list=%s')
    }
    ua = ("Mozilla/5.0 (compatible; MSIE 9.0; Windows NT 6.1; WOW64;"
          " Trident/5.0)")
    UEFSM = 'url_encoded_fmt_stream_map'
    AF = 'adaptive_fmts'
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
        '171': ('128k', 'ogg', 'audio', ''),
        '172': ('192k', 'ogg', 'audio', ''),
        '242': ('360x240', 'webm', 'normal', ''),
        '243': ('480x360', 'webm', 'normal', ''),
        '244': ('640x480', 'webm', 'normal', ''),
        '245': ('640x480', 'webm', 'normal', ''),
        '246': ('640x480', 'webm', 'normal', ''),
        '247': ('720x480', 'webm', 'normal', ''),
        '248': ('1920x1080', 'webm', 'normal', ''),
        '256': ('192k', 'm4a', 'audio', '6-channel'),
        '258': ('320k', 'm4a', 'audio', '6-channel'),
        '264': ('1920x1080', 'm4v', 'video', '')
    }


def _extract_smap(map_name, dic, zero_idx=True):
    if map_name in dic:
        smap = dic.get(map_name)
        smap = smap[0] if zero_idx else smap
        smap = smap.split(",")
        smap = [parse_qs(x) for x in smap]
        smap = [{k:v[0] for k, v in x.items()} for x in smap]
        return smap

    return None


def _extract_function_from_js(name, js):
    """ Find a function definition called `name` and extract components.

    Return a dict representation of the function.

    """

    # use cached js function
    #if g.jsfuncs.get(name) and g.jsfunctimes[name] > time.time() - g.funclife:
        #return g.jsfuncs.get(name)

    fpattern = r'function\s+%s\(((?:\w+,?)+)\)\{([^}]+)\}'
    m = re.search(fpattern % re.escape(name), js)
    args, body = m.groups()
    dbg("extracted function %s(%s){%s};", name, args, body)
    time.sleep(1)
    func = {'name': name, 'parameters': args.split(","), 'body': body}
    return func

def _get_mainfunc_from_js(js):
    m = re.search(r'\w\.sig\|\|(\w+)\(\w+\.\w+\)', js)
    funcname = m.group(1)
    function = _extract_function_from_js(funcname, js)
    return function

def _get_other_funcs(primary_func, js):
    """ Extract all secondary functions used in primary_func. """

    body = primary_func['body']
    body = body.split(";")
    call = re.compile(r'(?:[$\w+])=([$\w]+)\(((?:\w+,?)+)\)$')

    functions = {}

    for part in body:

        # is this a function?
        if call.match(part):
            match = call.match(part)
            name = match.group(1)

            if not name in functions:
                functions[name] = _extract_function_from_js(name, js)

    return functions

def _getval(val, argsdict):
    """ resolve variable values, preserve int literals. Return dict."""

    m = re.match(r'(\d+)', val)

    if m:
        return int(m.group(1))

    elif val in argsdict:
        return argsdict[val]

    else:
        raise RuntimeError("Error val %s from dict %s" % (val, argsdict))

def _get_func_from_call(caller_function, name, arguments, js_url):
    """
    Search js string for function call to `name`.

    Returns dict representation of the funtion
    Places argument values specified in `arguments` list parameter into
    the returned function representations `args` dict

    """

    #newfunction = _extract_function_from_js(name, js)
    newfunction = Pafy.funcmap[js_url][name]
    newfunction['args'] = {}

    for n, arg in enumerate(arguments):
        value = _getval(arg, caller_function['args'])
        param = newfunction['parameters'][n]
        newfunction['args'][param] = value

    return newfunction

def _solve(f, js_url):
    """Solve basic javascript function. Return dict function representation."""

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
        dbg("Working on part: " + part)

        name = ""

        for n, p in patterns.items():
            m, name = re.match(p, part), n
            if m:
                break

        if name == "split_or_join":
            pass

        elif name == "func_call":
            lhs, funcname, args = m.group(1, 2, 3)
            newfunc = _get_func_from_call(f, funcname, args.split(","), js_url)
            #dbg("Function call to %s", funcname)
            f['args'][lhs] = _solve(newfunc, js_url)  # recursive call
            #dbg("solved! %s", f['args'][lhs])

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

        else:
            raise RuntimeError("no match for %s" % part)

    raise RuntimeError("Processed js funtion parts without finding return")

def _decodesig(sig, js_url):
    """Get sig func name from a function call. Return function dict, js."""

    #m = re.search(r'\w\.sig\|\|(\w+)\(\w+\.\w+\)', js)
    #funcname = m.group(1)
    #function = _extract_function_from_js(funcname, js)

    function = Pafy.funcmap[js_url]['mainfunction']
    if not len(function['parameters']) == 1:
        raise RuntimeError("Main sig js function has more than one arg: %s" %
                           function['parameters'])
    function['args'] = {function['parameters'][0]: sig}
    new.callback("Decrypting signature")
    solved = _solve(function, js_url)
    new.callback("Decrypted signature")
    return solved


def extract_video_id(url):
    """ Extract the video id from a url, return video id and info url. """

    ok = (r"\w-",) * 3
    regx = re.compile(r'(?:^|[^%s]+)([%s]{11})(?:[^%s]+|$)' % ok)
    m = regx.search(url)

    if not m:
        err = "Need 11 character video id or the URL of the video. Got %s"
        raise RuntimeError(err % video_url)

    vidid = m.group(1)
    return vidid


def get_video_info(video_id):
    """ Get info for video_id. """

    url = g.urls['vidinfo'] % video_id

    info = decode_if_py3(g.opener.open(url).read())
    info = parse_qs(info)

    if info['status'][0] == "fail":
        reason = info['reason'][0] or "Bad video argument"
        raise RuntimeError("Youtube says: %s" % reason)

    return info

def get_video_gdata(video_id):
    """ Get video gdata. """

    #dbg("Fetching gdata info")
    url = g.urls['gdata'] % video_id
    return g.opener.open(url).read()

def get_js_sm(video_id):
    """ Get location of html5player javascript file and fetch.

    Return javascript as string and args.

    """

    watch_url = g.urls['watchv'] % video_id
    new.callback("Fetching watchv page")
    watchinfo = g.opener.open(watch_url).read().decode("utf8")
    new.callback("Fetched watchv page")
    m = re.search(r';ytplayer.config = ({.*?});', watchinfo)
    myjson = json.loads(m.group(1))
    info = myjson['args']
    js_url = myjson['assets']['js']

    if js_url.startswith("//"):
        js_url = "https:" + js_url

    funcs = {}

    if not js_url in Pafy.funcmap:
        new.callback("Fetching javascript")
        javascript = g.opener.open(js_url).read().decode("UTF-8")
        new.callback("Fetched javascript")
        mainfunc = _get_mainfunc_from_js(javascript)
        funcs = _get_other_funcs(mainfunc, javascript)
        funcs['mainfunction'] = mainfunc

    return info, js_url, funcs

def _get_matching_stream(encrypted, itag):

    for x in encrypted:
        if x['itag'] == itag:
            url, sig = x['url'], x['s']
            return url, sig

class Stream(object):

    """ YouTube video stream class. """
    def __init__(self, sm, parent):

        safeint = lambda x: int(x) if x.isdigit() else x
        self.itag = sm['itag']
        self.threed = 'stereo3d' in sm and sm['stereo3d'] == '1'
        self.resolution = g.itags[self.itag][0]
        self.dimensions = tuple(self.resolution.split("-")[0].split("x"))
        self.dimensions = tuple(map(safeint, self.dimensions))
        self.vidformat = sm['type'].split(';')[0]
        self.quality = self.resolution
        self.extension = g.itags[self.itag][1]
        self.title = parent._title
        self.encrypted = parent._ciphertag
        self._parent = parent
        self.filename = self.title + "." + self.extension
        self.fsize = None
        self.bitrate = self.rawbitrate = None
        self.mediatype = g.itags[self.itag][2]
        self.notes = g.itags[self.itag][3]
        self._url = None
        self._rawurl = sm['url']
        self.sig = sm['s'] if self.encrypted else sm.get("sig")

        if self.mediatype == "audio":
            self.dimensions = (0, 0)
            self.bitrate = self.resolution
            self.quality = self.bitrate
            self.resolution = "0x0"
            self.rawbitrate = int(sm["bitrate"][0])

    @property
    def url(self):
        """ Return the url, decrypt if required. """

        if self._url:
            pass

        elif not self.encrypted:
            self._url = make_url(self._rawurl, self.sig)

        else:

            if self._parent._js_url:
                dbg("using cached js")
                enc_streams = self._parent._enc_streams
                url, s = _get_matching_stream(enc_streams, self.itag)
                sig = _decodesig(s, self._parent._js_url)
                self._url = make_url(url, sig)

            else:
                info, js_url, funcs = get_js_sm(self._parent._videoid)
                self._parent._js_url = js_url

                if not Pafy.funcmap.get(js_url):
                    Pafy.funcmap[js_url] = funcs

                Pafy.funcmap[js_url].update(funcs)

                new_sm = _extract_smap(g.UEFSM, info, False)
                new_sm += _extract_smap(g.AF, info, False)
                self._parent._enc_streams = new_sm

                url, s = _get_matching_stream(new_sm, self.itag)
                sig = _decodesig(s, js_url)
                self._url = make_url(url, sig)

        return self._url



    def __repr__(self):
        out = "%s:%s@%s" % (self.mediatype, self.extension, self.quality)
        return out

    def get_filesize(self):
        """ Return filesize of the stream in bytes.  Set member variable. """

        if not self.fsize:

            try:
                cl = "content-length"
                self.fsize = int(g.opener.open(self.url).headers[cl])

            except (HTTPError, URLError):
                self.fsize = 0

        return self.fsize

    # pylint: disable=R0914
    # Too many local variables - who cares?
    def download(self, filepath="", quiet=False, callback=None):
        """ Download.  Use quiet=True to supress output. Return filename. """

        status_string = ('  {:,} Bytes [{:.2%}] received. Rate: [{:4.0f} '
                         'KB/s].  ETA: [{:.0f} secs]')
        response = g.opener.open(self.url)
        total = int(response.info()['Content-Length'].strip())
        chunksize, bytesdone, t0 = 16384, 0, time.time()
        fname = filepath or self.filename

        try:
            outfh = open(fname, 'wb')

        except IOError:
            ok = re.compile(r'[^\\/?*$\'"%&:<>|]')
            fname = "".join(x if ok.match(x) else "_" for x in self.filename)
            outfh = open(fname, 'wb')

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
    funcmap = {}

    # This is probably not the recommended way to use len()
    # R0924: implemented __len__ but not __getitem__
    # pylint: disable=R0924
    def __len__(self):
        return self.length

    def __repr__(self):

        keys = "Title Author ID Duration Rating Views Thumbnail Keywords"
        keys = keys.split(" ")
        keywords = ", ".join(self.keywords)
        length = time.strftime('%H:%M:%S', time.gmtime(self.length))

        info = dict(Title=self.title,
                    Author=self.author,
                    Views=self.viewcount,
                    Rating=self.rating,
                    Duration=length,
                    ID=self.videoid,
                    Thumbnail=self.thumb,
                    Keywords=keywords)

        return "\n".join(["%s: %s" % (k, info.get(k, "")) for k in keys])

        """ get stream map. Return stream map and javascript."""

        js = self.js
        streamMap = allinfo[key][0].split(',')
        smap = [parse_qs(sm) for sm in streamMap]
        if smap[0].get("s"):
            new.callback("Encrypted signature detected")
            js, args = self.get_js()
            streamMap = args[key].split(",")
            smap = [parse_qs(sm) for sm in streamMap]
        return(smap, js)

    def _fetch_basic(self):
        """ Fetches info url page and sets member vars. """

        if self._have_basic:
            return

        new.callback("Fetching video info..")
        allinfo = get_video_info(self.videoid)
        new.callback("Fetched video info")
        f = lambda x: allinfo.get(x, ["unknown"])[0]
        z = lambda x: allinfo.get(x, [""])[0]
        self._title = f('title').replace("/", "-")
        self._author = f('author')
        self._videoid = f('video_id')
        self._rating = float(f('avg_rating'))
        self._length = int(f('length_seconds'))
        self._viewcount = int(f('view_count'))
        self._thumb = unquote_plus(f('thumbnail_url'))
        self._duration = time.strftime('%H:%M:%S', time.gmtime(self._length))
        self._formats = [x.split("/") for x in f('fmt_list').split(",")]
        self._keywords = z('keywords').split(',')
        self._bigthumb = z('iurlsd')
        self._bigthumbhd = z('iurlsdmaxres')
        self._ciphertag = f("use_cipher_signature") == "True"

        # fetch sm

        self._sm = _extract_smap(g.UEFSM, allinfo, not self._js_url)
        self._asm = _extract_smap(g.AF, allinfo, not self._js_url)

        self._have_basic = 1
        self._process_streams()

    def _fetch_gdata(self):
        """ Extract gdata values, fetch gdata if necessary. """

        if self._have_gdata:
            return

        new.callback("Fetching video data")
        gdata = get_video_gdata(self.videoid)
        new.callback("Fetched video gdata")
        t0 = "{http://search.yahoo.com/mrss/}"
        t1 = "{http://www.w3.org/2005/Atom}"
        tree = etree.fromstring(gdata)
        groups = tree.find(t0 + "group")
        published = tree.find(t1 + "published").text
        description = groups.find(t0 + "description").text
        category = groups.find(t0 + "category").text
        setattr(self, "_published", published)
        setattr(self, "_description", description)
        setattr(self, "_category", category)

        self._have_gdata = 1


    def __init__(self, video_url, basic=True, gdata=False,
                 signature=True, size=False, callback=None):

        args = dict(basic=basic, gdata=gdata, signature=signature,
                    size=size, callback=callback, video_url=video_url)

        self.version = __version__
        self.videoid = extract_video_id(video_url)
        self.watchv_url = g.urls['watchv'] % self.videoid

        nullf = lambda x: None
        self._init_args = args
        new.callback = callback or nullf
        self._have_basic = False

        self._have_gdata = False
        self._description = None
        self._category = None
        self._published = None

        self._sm = []
        self._asm = []
        self._js_url= None  # if _js_url is set then has new stream map
        self._streams = []
        self._videostreams = []
        self._audiostreams = []
        self._oggstreams = []
        self._m4astreams = []

        if self._init_args['basic']:
            self._fetch_basic()

        if self._init_args['gdata']:
            self._fetch_gdata()


    def _process_streams(self):
        """ Extract stream urls. """

        if not self._have_basic:
            self._fetch_basic()

        streams = [Stream(sm, self) for sm in self._sm]
        adpt_streams = [Stream(sm, self) for sm in self._asm]
        audiostreams = [x for x in adpt_streams if x.bitrate]
        videostreams = [x for x in adpt_streams if not x.bitrate]
        m4astreams = [x for x in self.audiostreams if x.extension == "m4a"]
        oggstreams = [x for x in self.audiostreams if x.extension == "ogg"]
        allstreams = streams + videostreams + audiostreams
        self._streams = streams
        self._m4astreams, self._oggstreams = m4astreams, oggstreams
        self._allstreams = streams + videostreams + audiostreams


    @property
    def streams(self):
        self._fetch_basic()
        return self._streams

    @property
    def allstreams(self):
        self._fetch_basic()
        return self._allstreams

    @property
    def audiostreams(self):
        self._fetch_basic()
        return self._audiostreams

    @property
    def videostreams(self):
        self._fetch_basic()
        return self._videostreams

    @property
    def oggstreams(self):
        self._fetch_basic()
        return self._oggstreams

    @property
    def m4astreams(self):
        self._fetch_basic()
        return self._m4astreams

    @property
    def title(self):
        self._fetch_basic()
        return self._title

    @property
    def author(self):
        self._fetch_basic()
        return self._author

    @property
    def rating(self):
        self._fetch_basic()
        return self._rating

    @property
    def length(self):
        self._fetch_basic()
        return self._length

    @property
    def viewcount(self):
        self._fetch_basic()
        return self._viewcount

    @property
    def bigthumb(self):
        self._fetch_basic()
        return self._bigthumb

    @property
    def bigthumbhd(self):
        self._fetch_basic()
        return self._bigthumbhd

    @property
    def thumb(self):
        self._fetch_basic()
        return self._thumb

    @property
    def duration(self):
        self._fetch_basic()
        return self._duration

    @property
    def formats(self):
        self._fetch_basic()
        return self._formats

    @property
    def keywords(self):
        self._fetch_basic()
        return self._keywords


    @property
    def category(self):
        self._fetch_gdata()
        return self._category

    @property
    def description(self):
        self._fetch_gdata()
        return self._description

    @property
    def published(self):
        self._fetch_gdata()
        return self._published.rstrip(".000Z").replace("T", " ")


    def getbest(self, preftype="any", ftypestrict=True):
        """
        Return the best resolution available.

        set ftypestrict to False to use a non preferred format if that
        has a higher resolution

        """

        if not self.streams:
            return False

        def _sortkey(x, key3d=0, keyres=0, keyftype=0):

            """ sort function for max() """

            key3d = "3D" not in x.resolution
            keyres = int(x.resolution.split("x")[0])
            keyftype = preftype == x.extension

            if ftypestrict:
                return (key3d, keyftype, keyres)

            else:
                return (key3d, keyres, keyftype)

        r = max(self.streams, key=_sortkey)

        if ftypestrict and preftype != "any" and r.extension != preftype:
            return None

        else:
            return r

    def getbestaudio(self, preftype="any", ftypestrict=True):
        """ Return the highest bitrate audio Stream object."""

        if not self.audiostreams:
            return False

        def _sortkey(x, keybitrate=0, keyftype=0):
            """ Sort function for sort by bitrates. """

            keybitrate = int(x.rawbitrate)
            keyftype = preftype == x.extension

            if ftypestrict:
                return(keyftype, keybitrate)

            else:
                return(keybitrate, keyftype)

        r = max(self.audiostreams, key=_sortkey)

        if ftypestrict and preftype != "any" and r.extension != preftype:
            return None

        else:
            return r


def get_playlist(playlist_url, callback=None):
    """ Return a list of Pafy objects from a YouTube Playlist. """

    nullf = lambda x: None
    callback = callback or nullf
    ok = (r"\w-",) * 3
    regx = re.compile(r'(?:^|[^%s]+)([%s]{18})(?:[^%s]+|$)' % ok)
    m = regx.search(playlist_url)

    if not m:
        err = "Need 18 character video id or the URL of the video. Got %s"
        raise RuntimeError(err % playlist_url)

    playlistid = m.groups(0)
    url = g.urls["playlist"] % playlistid

    try:
        allinfo = json.loads(decode_if_py3(g.opener.open(url).read()))

    except:
        raise RuntimeError("Error fetching playlist %s" % m.groups(0))

    videos = []

    for v in allinfo['video']:

        try:
            video = Pafy(v['encrypted_id'])
            callback("Added video: %s" % v.title)
            videos.append(video)

        except RuntimeError as e:

            callback("%s: %s" % (v['title'], e.message))
            continue

    return videos
