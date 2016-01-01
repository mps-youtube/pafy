# -*- coding: utf-8 -*-

"""
pafy.py.

Python library to download YouTube content and retrieve metadata

https://github.com/np1/pafy

Copyright (C)  2013-2014 np1

This program is free software: you can redistribute it and/or modify it under
the terms of the GNU Lesser General Public License as published by the Free
Software Foundation, either version 3 of the License, or (at your option) any
later version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY
WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
PARTICULAR PURPOSE.  See the GNU Lesser General Public License for more details.

You should have received a copy of the GNU Lesser General Public License along
with this program.  If not, see <http://www.gnu.org/licenses/>.

"""


from __future__ import unicode_literals

__version__ = "0.3.82"
__author__ = "np1"
__license__ = "LGPLv3"


import re
import os
import sys
import time
import json
import logging
import hashlib
import tempfile
from xml.etree import ElementTree


early_py_version = sys.version_info[:2] < (2, 7)

if sys.version_info[:2] >= (3, 0):
    # pylint: disable=E0611,F0401,I0011
    from urllib.request import build_opener
    from urllib.error import HTTPError, URLError
    from urllib.parse import parse_qs, unquote_plus, urlencode, urlparse
    uni, pyver = str, 3

else:
    from urllib2 import build_opener, HTTPError, URLError
    from urllib import unquote_plus, urlencode
    from urlparse import parse_qs, urlparse
    uni, pyver = unicode, 2


from .jsinterp import JSInterpreter


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


def fetch_decode(url, encoding=None):
    """ Fetch url and decode. """
    try:
        req = g.opener.open(url)
    except HTTPError as e:
        if e.getcode() == 503:
            time.sleep(.5)
            return fetch_decode(url, encoding)
        else:
            raise

    ct = req.headers['content-type']

    if encoding:
        return req.read().decode(encoding)

    elif "charset=" in ct:
        dbg("charset: %s", ct)
        encoding = re.search(r"charset=([\w-]+)\s*(:?;|$)", ct).group(1)
        return req.read().decode(encoding)

    else:
        dbg("encoding unknown")
        return req.read()


class GdataError(Exception):
    """Gdata query failed."""
    pass


def call_gdata(api, qs):
    """Make a request to the youtube gdata api."""
    qs = dict(qs)
    qs['key'] = g.api_key
    url = g.urls['gdata'] + api + '?' + urlencode(qs)

    try:
        data = g.opener.open(url).read().decode()

    except HTTPError as e:
        try:
            errdata = e.file.read().decode()
            error = json.loads(errdata)['error']['message']
            errmsg = 'Youtube Error %d: %s' % (e.getcode(), error)
        except:
            errmsg = str(e)
        raise GdataError(errmsg)

    return json.loads(data)


def new(url, basic=True, gdata=False, signature=True, size=False,
        callback=None):
    """ Return a new pafy instance given a url or video id.

    NOTE: The signature argument has been deprecated and now has no effect,
        it will be removed in a future version.

    Optional arguments:
        basic - fetch basic metadata and streams
        gdata - fetch gdata info (upload date, description, category)
        size - fetch the size of each stream (slow)(decrypts urls if needed)
        callback - a callback function to receive status strings

    If any of the first three above arguments are False, those data items will
    be fetched only when first called for.

    The defaults are recommended for most cases. If you wish to create
    many video objects at once, you may want to set basic to False, eg:

        video = pafy.new(basic=False)

    This will be quick because no http requests will be made on initialisation.

    Setting size to True will override the basic argument and force basic data
    to be fetched too (basic data is required to obtain Stream objects).

    """
    if not signature:
        logging.warning("signature argument has no effect and will be removed"
                        " in a future version.")

    return Pafy(url, basic, gdata, signature, size, callback)


def get_video_info(video_id, newurl=None):
    """ Return info for video_id.  Returns dict. """
    url = g.urls['vidinfo'] % video_id
    url = newurl if newurl else url
    info = fetch_decode(url)  # bytes
    info = parseqs(info)  # unicode dict
    dbg("Fetched video info%s", " (age ver)" if newurl else "")

    if info['status'][0] == "fail" and info['errorcode'][0] == '150' and \
            "confirm your age" in info['reason'][0]:
        # Video requires age verification
        dbg("Age verification video")
        new.callback("Age verification video")
        newurl = g.urls['age_vidinfo'] % (video_id, video_id)
        info = get_video_info(video_id, newurl)
        info.update({"age_ver": True})

    elif info['status'][0] == "fail":
        reason = info['reason'][0] or "Bad video argument"
        raise IOError("Youtube says: %s [%s]" % (reason, video_id))

    return info


def get_video_gdata(video_id):
    """ Return json string containing video metadata from gdata api. """
    new.callback("Fetching video gdata")
    query = {'part': 'id,snippet,statistics',
             'maxResults': 1,
             'id': video_id}
    gdata = call_gdata('videos', query)
    dbg("Fetched video gdata")
    new.callback("Fetched video gdata")
    return gdata


def extract_video_id(url):
    """ Extract the video id from a url, return video id as str. """
    idregx = re.compile(r'[\w-]{11}$')
    url = str(url)

    if idregx.match(url):
        return url # ID of video

    if '://' not in url:
        url = '//' + url
    parsedurl = urlparse(url)
    if parsedurl.netloc in ('youtube.com', 'www.youtube.com'):
        query = parse_qs(parsedurl.query)
        if 'v' in query and idregx.match(query['v'][0]):
            return query['v'][0]
    elif parsedurl.netloc in ('youtu.be', 'www.youtu.be'):
        vidid = parsedurl.path.split('/')[-1] if parsedurl.path else ''
        if idregx.match(vidid):
            return vidid

    err = "Need 11 character video id or the URL of the video. Got %s"
    raise ValueError(err % url)


class g(object):

    """ Class for holding constants needed throughout the module. """

    urls = {
        'gdata': "https://www.googleapis.com/youtube/v3/",
        'watchv': "http://www.youtube.com/watch?v=%s",
        'vidinfo': ('http://www.youtube.com/get_video_info?'
                    'video_id=%s&asv=3&el=detailpage&hl=en_US'),
        'playlist': ('http://www.youtube.com/list_ajax?'
                     'style=json&action_get_list=1&list=%s'),
        'age_vidinfo': ('http://www.youtube.com/get_video_info?video_id=%s&'
                        'eurl=https://youtube.googleapis.com/v/%s&sts=1588')
    }
    api_key = "AIzaSyCIM4EzNqi1in22f4Z3Ru3iYvLaY8tc3bo"
    user_agent = "pafy " + __version__
    UEFSM = 'url_encoded_fmt_stream_map'
    AF = 'adaptive_fmts'
    jsplayer = r';ytplayer\.config\s*=\s*({.*?});'
    lifespan = 60 * 60 * 5  # 5 hours
    opener = build_opener()
    opener.addheaders = [('User-Agent', user_agent)]
    cache = {}
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
        '167': ('640x480', 'webm', 'video', ''),
        '168': ('854x480', 'webm', 'video', ''),
        '169': ('1280x720', 'webm', 'video', ''),
        '170': ('1920x1080', 'webm', 'video', ''),
        '171': ('128k', 'ogg', 'audio', ''),
        '172': ('192k', 'ogg', 'audio', ''),
        '218': ('854x480', 'webm', 'video', 'VP8'),
        '219': ('854x480', 'webm', 'video', 'VP8'),
        '242': ('360x240', 'webm', 'video', 'VP9'),
        '243': ('480x360', 'webm', 'video', 'VP9'),
        '244': ('640x480', 'webm', 'video', 'VP9 low'),
        '245': ('640x480', 'webm', 'video', 'VP9 med'),
        '246': ('640x480', 'webm', 'video', 'VP9 high'),
        '247': ('720x480', 'webm', 'video', 'VP9'),
        '248': ('1920x1080', 'webm', 'video', 'VP9'),
        '249': ('48k', 'opus', 'audio', 'Opus'),
        '250': ('56k', 'opus', 'audio', 'Opus'),
        '251': ('128k', 'opus', 'audio', 'Opus'),
        '256': ('192k', 'm4a', 'audio', '6-channel'),
        '258': ('320k', 'm4a', 'audio', '6-channel'),
        '264': ('2560x1440', 'm4v', 'video', ''),
        '266': ('3840x2160', 'm4v', 'video', 'AVC'),
        '271': ('1920x1280', 'webm', 'video', 'VP9'),
        '272': ('3414x1080', 'webm', 'video', 'VP9'),
        '278': ('256x144', 'webm', 'video', 'VP9'),
        '298': ('1280x720', 'm4v', 'video', '60fps'),
        '299': ('1920x1080', 'm4v', 'video', '60fps'),
        '302': ('1280x720', 'webm', 'video', 'VP9'),
        '303': ('1920x1080', 'webm', 'video', 'VP9'),
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


def _extract_dash(dashurl):
    """ Download dash url and extract some data. """
    # pylint: disable = R0914
    dbg("Fetching dash page")
    dashdata = fetch_decode(dashurl)
    dbg("DASH list fetched")
    ns = "{urn:mpeg:DASH:schema:MPD:2011}"
    ytns = "{http://youtube.com/yt/2012/10/10}"
    tree = ElementTree.fromstring(dashdata)
    tlist = tree.findall(".//%sRepresentation" % ns)
    dashmap = []

    for x in tlist:
        baseurl = x.find("%sBaseURL" % ns)
        url = baseurl.text
        size = baseurl.attrib["%scontentLength" % ytns]
        bitrate = x.get("bandwidth")
        itag = uni(x.get("id"))
        width = uni(x.get("width"))
        height = uni(x.get("height"))
        type_ = re.search(r"(?:\?|&)mime=([\w\d\/]+)", url).group(1)
        dashmap.append(dict(bitrate=bitrate,
                            dash=True,
                            itag=itag,
                            width=width,
                            height=height,
                            url=url,
                            size=size,
                            type=type_))
    return dashmap


def _get_mainfunc_from_js(js):
    """ Return main signature decryption function from javascript as dict. """
    dbg("Scanning js for main function.")
    m = re.search(r'\.sig\|\|([a-zA-Z0-9$]+)\(', js)
    funcname = m.group(1)
    dbg("Found main function: %s", funcname)
    jsi = JSInterpreter(js)
    return jsi.extract_function(funcname)


def _decodesig(sig, js_url):
    """  Return decrypted sig given an encrypted sig and js_url key. """
    # lookup main function in Pafy.funcmap dict
    mainfunction = Pafy.funcmap[js_url]

    # fill in function argument with signature
    new.callback("Decrypting signature")
    solved = mainfunction([sig])
    dbg("Decrypted sig = %s...", solved[:30])
    new.callback("Decrypted signature")
    return solved


def remux(infile, outfile, quiet=False, muxer="ffmpeg"):
    """ Remux audio. """
    from subprocess import call, STDOUT
    muxer = muxer if isinstance(muxer, str) else "ffmpeg"

    for tool in set([muxer, "ffmpeg", "avconv"]):
        cmd = [tool, "-y", "-i", infile, "-acodec", "copy", "-vn", outfile]

        try:
            with open(os.devnull, "w") as devnull:
                call(cmd, stdout=devnull, stderr=STDOUT)

        except OSError:
            dbg("Failed to remux audio using %s", tool)

        else:
            os.unlink(infile)
            dbg("remuxed audio file using %s" % tool)

            if not quiet:
                sys.stdout.write("\nAudio remuxed.\n")

            break

    else:
        logging.warning("audio remux failed")
        os.rename(infile, outfile)


def cache(name):
    """ Returns a sub-cache dictionary under which global key, value pairs
    can be stored. Regardless of whether a dictionary already exists for
    the given name, the sub-cache is returned by reference.
    """
    if name not in g.cache:
        g.cache[name] = {}
    return g.cache[name]


def fetch_cached(url, encoding=None, dbg_ref="", file_prefix=""):
    """ Fetch url - from tmpdir if already retrieved. """
    tmpdir = os.path.join(tempfile.gettempdir(), "pafy")

    if not os.path.exists(tmpdir):
        os.makedirs(tmpdir)

    url_md5 = hashlib.md5(url.encode("utf8")).hexdigest()
    cached_filename = os.path.join(tmpdir, file_prefix + url_md5)

    if os.path.exists(cached_filename):
        dbg("fetched %s from cache", dbg_ref)

        with open(cached_filename) as f:
            retval = f.read()

        return retval

    else:
        data = fetch_decode(url, "utf8")  # unicode
        dbg("Fetched %s", dbg_ref)
        new.callback("Fetched %s" % dbg_ref)

        with open(cached_filename, "w") as f:
            f.write(data)

        # prune files after write
        prune_files(tmpdir, file_prefix)
        return data


def prune_files(path, prefix="", age_max=3600 * 24 * 14, count_max=4):
    """ Remove oldest files from path that start with prefix.

    remove files older than age_max, leave maximum of count_max files.
    """
    tempfiles = []

    if not os.path.isdir(path):
        return

    for f in os.listdir(path):
        filepath = os.path.join(path, f)

        if os.path.isfile(filepath) and f.startswith(prefix):
            age = time.time() - os.path.getmtime(filepath)

            if age > age_max:
                os.unlink(filepath)

            else:
                tempfiles.append((filepath, age))

    tempfiles = sorted(tempfiles, key=lambda x: x[1], reverse=True)

    for f in tempfiles[:-count_max]:
        os.unlink(f[0])


def get_js_sm(video_id):
    """ Fetch watchinfo page and extract stream map and js funcs if not known.

    This function is needed by videos with encrypted signatures.
    If the js url referred to in the watchv page is not a key in Pafy.funcmap,
    the javascript is fetched and functions extracted.

    Returns streammap (list of dicts), js url (str)  and funcs (dict)

    """
    watch_url = g.urls['watchv'] % video_id
    new.callback("Fetching watch page")
    watchinfo = fetch_decode(watch_url)  # unicode
    dbg("Fetched watch page")
    new.callback("Fetched watch page")
    m = re.search(g.jsplayer, watchinfo)
    myjson = json.loads(m.group(1))
    stream_info = myjson['args']
    dash_url = stream_info['dashmpd']
    sm = _extract_smap(g.UEFSM, stream_info, False)
    asm = _extract_smap(g.AF, stream_info, False)
    js_url = myjson['assets']['js']
    js_url = "https:" + js_url if js_url.startswith("//") else js_url
    mainfunc = Pafy.funcmap.get(js_url)

    if not mainfunc:
        dbg("Fetching javascript")
        new.callback("Fetching javascript")
        javascript = fetch_cached(js_url, encoding="utf8",
                                  dbg_ref="javascript", file_prefix="js-")
        mainfunc = _get_mainfunc_from_js(javascript)

    elif mainfunc:
        dbg("Using functions in memory extracted from %s", js_url)
        dbg("Mem contains %s js func sets", len(Pafy.funcmap))

    return (sm, asm), js_url, mainfunc, dash_url


def _make_url(raw, sig, quick=True):
    """ Return usable url. Set quick=False to disable ratebypass override. """
    if quick and "ratebypass=" not in raw:
        raw += "&ratebypass=yes"

    if "signature=" not in raw:

        if sig is None:
            raise IOError("Error retrieving url")

        raw += "&signature=" + sig

    return raw


class Stream(object):

    """ YouTube video stream class. """

    def __init__(self, sm, parent):
        """ Set initial values. """
        self._itag = sm['itag']
        # is_dash = "width" in sm and "height" in sm
        is_dash = "dash" in sm

        if self._itag not in g.itags:
            logging.warning("Unknown itag: %s", self._itag)
            return None

        self._mediatype = g.itags[self.itag][2]
        self._threed = 'stereo3d' in sm and sm['stereo3d'] == '1'

        # It will be None by default, for non-audio streams
        self._rawbitrate = None

        if is_dash:

            if sm['width'] != "None":  # dash video
                self._resolution = "%sx%s" % (sm['width'], sm['height'])
                self._quality = self._resolution
                self._dimensions = (int(sm['width']), int(sm['height']))

            else:  # dash audio
                self._resolution = "0x0"
                self._dimensions = (0, 0)
                self._rawbitrate = int(sm['bitrate'])
                # self._bitrate = uni(int(sm['bitrate']) // 1024) + "k"
                self._bitrate = g.itags[self.itag][0]
                self._quality = self._bitrate

            self._fsize = int(sm['size'])
            # self._bitrate = sm['bitrate']
            # self._rawbitrate = uni(int(self._bitrate) // 1024) + "k"

        else:  # not dash
            self._resolution = g.itags[self.itag][0]
            self._fsize = None
            self._bitrate = self._rawbitrate = None
            self._dimensions = tuple(self.resolution.split("-")[0].split("x"))
            self._dimensions = tuple([int(x) if x.isdigit() else x for x in
                                      self._dimensions])
            self._quality = self.resolution

        self._vidformat = sm['type'].split(';')[0]  # undocumented
        self._extension = g.itags[self.itag][1]
        self._title = parent.title
        self.encrypted = 's' in sm
        self._parent = parent
        self._filename = self.generate_filename()
        self._notes = g.itags[self.itag][3]
        self._url = None
        self._rawurl = sm['url']
        self._sig = sm['s'] if self.encrypted else sm.get("sig")
        self._active = False

        if self.mediatype == "audio" and not is_dash:
            self._dimensions = (0, 0)
            self._bitrate = self.resolution
            self._quality = self.bitrate
            self._resolution = "0x0"
            self._rawbitrate = int(sm["bitrate"])

    def generate_filename(self, meta=False):
        """ Generate filename. """
        ok = re.compile(r'[^/]')

        if os.name == "nt":
            ok = re.compile(r'[^\\/:*?"<>|]')

        filename = "".join(x if ok.match(x) else "_" for x in self._title)

        if meta:
            filename += "-%s-%s" % (self._parent.videoid, self._itag)

        filename += "." + self._extension
        return filename

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
        if not self._url:

            if self._parent.age_ver:

                if self._sig:
                    s = self._sig
                    self._sig = s[2:63] + s[82] + s[64:82] + s[63]

            elif self.encrypted:
                self._sig = _decodesig(self._sig, self._parent.js_url)

            self._url = _make_url(self._rawurl, self._sig)

        return self._url

    @property
    def url_https(self):
        """ Return https url. """
        return self.url.replace("http://", "https://")

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

    def cancel(self):
        """ Cancel an active download. """
        if self._active:
            self._active = False
            return True

    def download(self, filepath="", quiet=False, callback=lambda *x: None,
                 meta=False, remux_audio=False):
        """ Download.  Use quiet=True to supress output. Return filename.

        Use meta=True to append video id and itag to generated filename
        Use remax_audio=True to remux audio file downloads

        """
        # pylint: disable=R0912,R0914
        # Too many branches, too many local vars
        savedir = filename = ""

        if filepath and os.path.isdir(filepath):
            savedir, filename = filepath, self.generate_filename()

        elif filepath:
            savedir, filename = os.path.split(filepath)

        else:
            filename = self.generate_filename(meta=meta)

        filepath = os.path.join(savedir, filename)
        temp_filepath = filepath + ".temp"

        status_string = ('  {:,} Bytes [{:.2%}] received. Rate: [{:4.0f} '
                         'KB/s].  ETA: [{:.0f} secs]')

        if early_py_version:
            status_string = ('  {0:} Bytes [{1:.2%}] received. Rate:'
                             ' [{2:4.0f} KB/s].  ETA: [{3:.0f} secs]')

        response = g.opener.open(self.url)
        total = int(response.info()['Content-Length'].strip())
        chunksize, bytesdone, t0 = 16384, 0, time.time()

        fmode, offset = "wb", 0

        if os.path.exists(temp_filepath):
            if os.stat(temp_filepath).st_size < total:

                offset = os.stat(temp_filepath).st_size
                fmode = "ab"

        outfh = open(temp_filepath, fmode)

        if offset:
            # partial file exists, resume download
            resuming_opener = build_opener()
            resuming_opener.addheaders = [('User-Agent', g.user_agent),
                                          ("Range", "bytes=%s-" % offset)]
            response = resuming_opener.open(self.url)
            bytesdone = offset

        self._active = True

        while self._active:
            chunk = response.read(chunksize)
            outfh.write(chunk)
            elapsed = time.time() - t0
            bytesdone += len(chunk)
            if elapsed:
                rate = ((float(bytesdone) - float(offset)) / 1024.0) / elapsed
                eta = (total - bytesdone) / (rate * 1024)
            else: # Avoid ZeroDivisionError
                rate = 0
                eta = 0
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

        if self._active:

            if remux_audio and self.mediatype == "audio":
                remux(temp_filepath, filepath, quiet=quiet, muxer=remux_audio)

            else:
                os.rename(temp_filepath, filepath)

            return filepath

        else:  # download incomplete, return temp filepath
            outfh.close()
            return temp_filepath


class Pafy(object):

    """ Class to represent a YouTube video. """

    funcmap = {}  # keep functions as a class variable

    def __init__(self, video_url, basic=True, gdata=False,
                 signature=True, size=False, callback=None):
        """ Set initial values. """
        self.version = __version__
        self.videoid = extract_video_id(video_url)
        self.watchv_url = g.urls['watchv'] % self.videoid

        new.callback = callback or (lambda x: None)
        self._have_basic = False
        self._have_gdata = False

        self._description = None
        self._likes = None
        self._dislikes = None
        self._category = None
        self._published = None
        self._username = None

        self.sm = []
        self.asm = []
        self.dash = []
        self.js_url = None  # if js_url is set then has new stream map
        self._dashurl = None
        self.age_ver = False
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
        self.ciphertag = None  # used by Stream class in url property def
        self._duration = None
        self._keywords = None
        self._bigthumb = None
        self._viewcount = None
        self._bigthumbhd = None
        self._mix_pl = None
        self.expiry = None

        if basic:
            self.fetch_basic()

        if gdata:
            self._fetch_gdata()

        if size:
            for s in self.allstreams:
                # pylint: disable=W0104
                s.get_filesize()

    def fetch_basic(self):
        """ Fetch basic data and streams. """
        if self._have_basic:
            return

        self._fetch_basic()
        sm_ciphertag = "s" in self.sm[0]

        if self.ciphertag != sm_ciphertag:
            dbg("ciphertag mismatch")
            self.ciphertag = not self.ciphertag

        if self.ciphertag:
            dbg("Encrypted signature detected.")

            if not self.age_ver:
                smaps, js_url, mainfunc, dashurl = get_js_sm(self.videoid)
                Pafy.funcmap[js_url] = mainfunc
                self.sm, self.asm = smaps
                self.js_url = js_url
                dashsig = re.search(r"/s/([\w\.]+)", dashurl).group(1)
                dbg("decrypting dash sig")
                goodsig = _decodesig(dashsig, js_url)
                self._dashurl = re.sub(r"/s/[\w\.]+",
                                       "/signature/%s" % goodsig, dashurl)

            else:
                s = re.search(r"/s/([\w\.]+)", self._dashurl).group(1)
                s = s[2:63] + s[82] + s[64:82] + s[63]
                self._dashurl = re.sub(r"/s/[\w\.]+",
                                       "/signature/%s" % s, self._dashurl)

        if self._dashurl != 'unknown':
            self.dash = _extract_dash(self._dashurl)
        self._have_basic = 1
        self._process_streams()
        self.expiry = time.time() + g.lifespan

    def _fetch_basic(self, info_url=None):
        """ Fetch info url page and set member vars. """
        allinfo = get_video_info(self.videoid, newurl=info_url)

        if allinfo.get("age_ver"):
            self.age_ver = True

        new.callback("Fetched video info")

        def _get_lst(key, default="unknown", dic=allinfo):
            """ Dict get function, returns first index. """
            retval = dic.get(key, default)
            return retval[0] if retval != default else default

        self._title = _get_lst('title')
        self._dashurl = _get_lst('dashmpd')
        self._author = _get_lst('author')
        self._rating = float(_get_lst('avg_rating', 0.0))
        self._length = int(_get_lst('length_seconds', 0))
        self._viewcount = int(_get_lst('view_count'), 0)
        self._thumb = unquote_plus(_get_lst('thumbnail_url', ""))
        self._formats = [x.split("/") for x in _get_lst('fmt_list').split(",")]
        self._keywords = _get_lst('keywords', "").split(',')
        self._bigthumb = _get_lst('iurlsd', "")
        self._bigthumbhd = _get_lst('iurlsdmaxres', "")
        self.ciphertag = _get_lst("use_cipher_signature") == "True"
        self.sm = _extract_smap(g.UEFSM, allinfo, True)
        self.asm = _extract_smap(g.AF, allinfo, True)
        dbg("extracted stream maps")

    def _fetch_gdata(self):
        """ Extract gdata values, fetch gdata if necessary. """
        if self._have_gdata:
            return

        item = get_video_gdata(self.videoid)['items'][0]
        snippet = item['snippet']
        self._published = uni(snippet['publishedAt'])
        self._description = uni(snippet["description"])
        self._category = get_categoryname(snippet['categoryId'])
        # TODO: Make sure actual usename is not available through the api
        self._username = uni(snippet['channelTitle'])
        statistics = item["statistics"]
        self._likes = int(statistics["likeCount"])
        self._dislikes = int(statistics["dislikeCount"])
        self._have_gdata = 1

    def _process_streams(self):
        """ Create Stream object lists from internal stream maps. """
        if not self._have_basic:
            self.fetch_basic()

        streams = [Stream(z, self) for z in self.sm]
        streams = [x for x in streams if x.itag in g.itags]
        adpt_streams = [Stream(z, self) for z in self.asm]
        adpt_streams = [x for x in adpt_streams if x.itag in g.itags]
        dash_streams = [Stream(z, self) for z in self.dash]
        dash_streams = [x for x in dash_streams if x.itag in g.itags]
        audiostreams = [x for x in adpt_streams if x.bitrate]
        videostreams = [x for x in adpt_streams if not x.bitrate]
        dash_itags = [x.itag for x in dash_streams]
        audiostreams = [x for x in audiostreams if x.itag not in dash_itags]
        videostreams = [x for x in videostreams if x.itag not in dash_itags]
        audiostreams += [x for x in dash_streams if x.mediatype == "audio"]
        videostreams += [x for x in dash_streams if x.mediatype != "audio"]
        audiostreams = sorted(audiostreams, key=lambda x: x.rawbitrate,
                              reverse=True)
        videostreams = sorted(videostreams, key=lambda x: x.dimensions,
                              reverse=True)
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

    @property
    def mix(self):
        """ The playlist for the related YouTube mix. Returns a dict containing Pafy objects. """
        if self._mix_pl is None:
            try:
                self._mix_pl = get_playlist("RD" + self.videoid)
            except IOError:
                return None
        return self._mix_pl

    def _getbest(self, preftype="any", ftypestrict=True, vidonly=False):
        """
        Return the highest resolution video available.

        Select from video-only streams if vidonly is True
        """
        streams = self.videostreams if vidonly else self.streams

        if not streams:
            return None

        def _sortkey(x, key3d=0, keyres=0, keyftype=0):
            """ sort function for max(). """
            key3d = "3D" not in x.resolution
            keyres = int(x.resolution.split("x")[0])
            keyftype = preftype == x.extension
            strict = (key3d, keyftype, keyres)
            nonstrict = (key3d, keyres, keyftype)
            return strict if ftypestrict else nonstrict

        r = max(streams, key=_sortkey)

        if ftypestrict and preftype != "any" and r.extension != preftype:
            return None

        else:
            return r

    def getbestvideo(self, preftype="any", ftypestrict=True):
        """
        Return the best resolution video-only stream.

        set ftypestrict to False to return a non-preferred format if that
        has a higher resolution
        """
        return self._getbest(preftype, ftypestrict, vidonly=True)

    def getbest(self, preftype="any", ftypestrict=True):
        """
        Return the highest resolution video+audio stream.

        set ftypestrict to False to return a non-preferred format if that
        has a higher resolution
        """
        return self._getbest(preftype, ftypestrict, vidonly=False)

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


def get_categoryname(cat_id):
    """ Returns a list of video category names for one category ID. """
    timestamp = time.time()
    cat_cache = cache('categories')
    cached = cat_cache.get(cat_id, {})
    if cached.get('updated', 0) > timestamp - g.lifespan:
        return cached.get('title', 'unknown')
    # call videoCategories API endpoint to retrieve title
    query = {'id': cat_id,
             'part': 'snippet'}
    catinfo = call_gdata('videoCategories', query)
    try:
        for item in catinfo.get('items', []):
            title = item.get('snippet', {}).get('title', 'unknown')
            cat_cache[cat_id] = {'title':title, 'updated':timestamp}
            return title
        cat_cache[cat_id] = {'updated':timestamp}
        return 'unknown'
    except Exception:
        raise IOError("Error fetching category name for ID %s" % cat_id)


def set_categories(categories):
    """ Take a dictionary mapping video category IDs to name and retrieval
    time. All items are stored into cache node 'videoCategories', but
    for the ones with a retrieval time too long ago, the v3 API is queried
    before.
    """
    timestamp = time.time()
    idlist = [cid for cid, item in categories.items()
              if item.get('updated', 0) < timestamp - g.lifespan]
    if len(idlist) > 0:
        query = {'id': ','.join(idlist),
                 'part': 'snippet'}
        catinfo = call_gdata('videoCategories', query)
        try:
            for item in catinfo.get('items', []):
                cid = item['id']
                title = item.get('snippet', {}).get('title', 'unknown')
                categories[cid] = {'title':title, 'updated':timestamp}
        except Exception:
            raise IOError("Error fetching category name for IDs %s" % idlist)
    cache('categories').update(categories)


def load_cache(newcache):
    """Loads a dict into pafy's internal cache."""
    set_categories(newcache.get('categories', {}))


def dump_cache():
    """Returns pafy's cache for storing by program."""
    return g.cache


def extract_playlist_id(playlist_url):
    # Normal playlists start with PL, Mixes start with RD + first video ID
    idregx = re.compile(r'((?:RD|PL)[-_0-9a-zA-Z]+)$')

    playlist_id = None
    if idregx.match(playlist_url):
        playlist_id = playlist_url # ID of video

    if '://' not in playlist_url:
        playlist_url = '//' + playlist_url
    parsedurl = urlparse(playlist_url)
    if parsedurl.netloc in ('youtube.com', 'www.youtube.com'):
        query = parse_qs(parsedurl.query)
        if 'list' in query and idregx.match(query['list'][0]):
            playlist_id = query['list'][0]

    return playlist_id


def get_playlist(playlist_url, basic=False, gdata=False, signature=True,
                 size=False, callback=lambda x: None):
    """ Return a dict containing Pafy objects from a YouTube Playlist.

    The returned Pafy objects are initialised using the arguments to
    get_playlist() in the manner documented for pafy.new()

    """

    playlist_id = extract_playlist_id(playlist_url)

    if not playlist_id:
        err = "Unrecognized playlist url: %s"
        raise ValueError(err % playlist_url)

    url = g.urls["playlist"] % playlist_id

    allinfo = fetch_decode(url)  # unicode
    allinfo = json.loads(allinfo)

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
            start=v.get('start', 0.0),
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
            length_seconds=v.get('length_seconds'),
            end=v.get('end', v.get('length_seconds'))
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


def parseISO8591(duration):
    """ Parse ISO 8591 formated duration """
    regex = re.compile(r'PT((\d{1,3})H)?((\d{1,3})M)?((\d{1,2})S)?')
    if duration:
        duration = regex.findall(duration)
        if len(duration) > 0:
            _, hours, _, minutes, _, seconds = duration[0]
            duration = [seconds, minutes, hours]
            duration = [int(v) if len(v) > 0 else 0 for v in duration]
            duration = sum([60**p*v for p, v in enumerate(duration)])
        else:
            duration = 30
    else:
        duration = 30
    return duration


class Playlist(object):
    _items = None

    def __init__(self, playlist_url, basic, gdata, signature, size, callback):
        playlist_id = extract_playlist_id(playlist_url)

        if not playlist_id:
            err = "Unrecognized playlist url: %s"
            raise ValueError(err % playlist_url)

        query = {'part': 'snippet, contentDetails',
                'id': playlist_id}
        allinfo = call_gdata('playlists', query)

        pl = allinfo['items'][0]

        self.plid = playlist_id
        self.title = pl['snippet']['title']
        self.author = pl['snippet']['channelTitle']
        self.description = pl['snippet']['description']
        self ._len = pl['contentDetails']['itemCount']
        self._basic = basic
        self._gdata = gdata
        self._signature = signature
        self._size = size
        self._callback = callback

    def __len__(self):
        return self._len
    
    def __iter__(self):
        if self._items is not None:
            for  i in self._items:
                yield i
            return

        items = []

        # playlist items specific metadata
        query = {'part': 'snippet',
                'maxResults': 50,
                'playlistId': self.plid}

        while True:
            playlistitems = call_gdata('playlistItems', query)

            query2 = {'part':'contentDetails,snippet,statistics',
                      'maxResults': 50,
                      'id': ','.join(i['snippet']['resourceId']['videoId']
                          for i in playlistitems['items'])}
            wdata = call_gdata('videos', query2)

            for v, vextra in zip(playlistitems['items'], wdata['items']):
                vid_data = dict(
                    title=v['snippet']['title'],
                    author=v['snippet']['channelTitle'],
                    thumbnail=v['snippet'].get('thumbnails', {}
                        ).get('default', {}).get('url'),
                    description=v['snippet']['description'],
                    length_seconds=parseISO8591(
                        vextra['contentDetails']['duration']),
                    category=get_categoryname(vextra['snippet']['categoryId']),
                    views=vextra['statistics'].get('viewCount',0),
                    likes=vextra['statistics'].get('likeCount',0),
                    dislikes=vextra['statistics'].get('dislikeCount',0),
                    comments=vextra['statistics'].get('commentCount',0),
                )

                try:
                    pafy_obj = new(v['snippet']['resourceId']['videoId'],
                            basic=self._basic, gdata=self._gdata,
                            signature=self._signature, size=self._size,
                            callback=self._callback)

                except IOError as e:
                    self.callback("%s: %s" % (v['title'], e.message))
                    continue

                pafy_obj.populate_from_playlist(vid_data)
                items.append(pafy_obj)
                self._callback("Added video: %s" % vid_data['title'])
                yield pafy_obj

            if not playlistitems.get('nextPageToken'):
                break
            query['pageToken'] = playlistitems['nextPageToken']

        self._items = items


def get_playlist2(playlist_url, basic=False, gdata=False, signature=True,
                 size=False, callback=lambda x: None):
    """ Return a Playlist object from a YouTube Playlist.

    The returned Pafy objects are initialised using the arguments to
    get_playlist() in the manner documented for pafy.new()

    """

    return Playlist(playlist_url, basic, gdata, signature, size, callback)


def set_api_key(key):
    """Sets the api key to be used with youtube."""
    g.api_key = key
