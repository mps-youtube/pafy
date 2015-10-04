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

__version__ = "0.4.1"
__author__ = "np1"
__license__ = "LGPLv3"


import re
import os
import sys
import time
import json
import logging


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

import youtube_dl


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
            raise e

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


def get_video_gdata(video_id):
    """ Return json string containing video metadata from gdata api. """
    new.callback("Fetching video gdata")
    query = {'part': 'id,snippet,statistics',
             'maxResults': 1,
             'id': video_id,
             'key': g.api_key}
    url = g.urls['gdata'] + '?' + urlencode(query)
    gdata = fetch_decode(url)  # unicode
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
        'gdata': "https://www.googleapis.com/youtube/v3/videos",
        'watchv': "http://www.youtube.com/watch?v=%s",
        'vidcat': "https://www.googleapis.com/youtube/v3/videoCategories",
        'playlist': ('http://www.youtube.com/list_ajax?'
                     'style=json&action_get_list=1&list=%s'),
        'thumb': "http://i.ytimg.com/vi/%s/default.jpg",
        'bigthumb': "http://i.ytimg.com/vi/%s/sddefault.jpg",
        'bigthumbhd': "http://i.ytimg.com/vi/%s/hddefault.jpg",
    }
    api_key = "AIzaSyCIM4EzNqi1in22f4Z3Ru3iYvLaY8tc3bo"
    user_agent = "pafy " + __version__
    lifespan = 60 * 60 * 5  # 5 hours
    opener = build_opener()
    opener.addheaders = [('User-Agent', user_agent)]
    cache = {}
    ydl_opts = {'quiet': True, 'prefer_insecure': True, 'no_warnings':True}


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


class Stream(object):

    """ YouTube video stream class. """

    _fsize = None

    def __init__(self, info, parent):
        """ Set initial values. """
        self._info = info
        self._parent = parent
        self._filename = self.generate_filename()

    def generate_filename(self, meta=False):
        """ Generate filename. """
        ok = re.compile(r'[^/]')

        if os.name == "nt":
            ok = re.compile(r'[^\\/:*?"<>|]')

        filename = "".join(x if ok.match(x) else "_" for x in self.title)

        if meta:
            filename += "-%s-%s" % (self._parent.videoid, self.itag)

        filename += "." + self.extension
        return filename

    @property
    def rawbitrate(self):
        """ Return raw bitrate value. """
        return self._info.get('abr', 0) * 1024

    @property
    def threed(self):
        """ Return bool, True if stream is 3D. """
        #TODO Figure out how to implement this with youtube-dl
        return False

    @property
    def itag(self):
        """ Return itag value of stream. """
        return self._info['format_id']

    @property
    def resolution(self):
        """ Return resolution of stream as str. 0x0 if audio. """
        height = self._info.get('height') or 0
        width = self._info.get('width') or 0
        return str(width) + 'x' + str(height)

    @property
    def dimensions(self):
        """ Return dimensions of stream as tuple.  (0, 0) if audio. """
        height = self._info.get('height') or 0
        width = self._info.get('width') or 0
        return width, height

    @property
    def quality(self):
        """ Return quality of stream (bitrate or resolution).

        eg, 128k or 640x480 (str)
        """
        if self.rawbitrate:
            quality = self.bitrate
        else:
            quality = self.resolution
        return quality

    @property
    def title(self):
        """ Return YouTube video title as a string. """
        return self._parent.title

    @property
    def extension(self):
        """ Return appropriate file extension for stream (str).

        Possible values are: 3gp, m4a, m4v, mp4, webm, ogg
        """
        return self._info['ext']

    @property
    def bitrate(self):
        """ Return bitrate of an audio stream. """
        return str(self._info.get('abr', 0)) + 'k'

    @property
    def mediatype(self):
        """ Return mediatype string (normal, audio or video).

        (normal means a stream containing both video and audio.)
        """
        if (self._info.get('acodec') != 'none' and
                self._info.get('vcodec') == 'none'):
            return 'audio'
        elif (self._info.get('acodec') == 'none' and
                self._info.get('vcodec') != 'none'):
            return 'video'
        else:
            return 'normal'

    @property
    def notes(self):
        """ Return additional notes regarding the stream format. """
        return self._info.get('format_note') or ''

    @property
    def filename(self):
        """ Return filename of stream; derived from title and extension. """
        return self._filename

    @property
    def url(self):
        """ Return the url, decrypt if required. """
        return self._info.get('url')

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

        # Faster method
        if 'filesize' in self._info:
            return self._info['filesize']

        # Fallback
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
                rate = ((bytesdone - offset) / 1024) / elapsed
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

        self._ydl_info = None
        self._streams = []
        self._oggstreams = []
        self._m4astreams = []
        self._allstreams = []
        self._videostreams = []
        self._audiostreams = []

        self._title = None
        self._rating = None
        self._length = None
        self._author = None
        self._duration = None
        self._keywords = None
        self._bigthumb = None
        self._viewcount = None
        self._bigthumbhd = None
        self._mix_pl = None
        self.expiry = None
        self.playlist_meta = None

        if basic:
            self._fetch_basic()

        if gdata:
            self._fetch_gdata()

        if size:
            for s in self.allstreams:
                # pylint: disable=W0104
                s.get_filesize()

    def _fetch_basic(self):
        """ Fetch basic data and streams. """
        if self._have_basic:
            return

        with youtube_dl.YoutubeDL(g.ydl_opts) as ydl:
            try:
                self._ydl_info = ydl.extract_info(self.videoid, download=False)
            # Turn into an IOError since that is what pafy previously raised
            except youtube_dl.utils.DownloadError as e:
                raise IOError(str(e).replace('YouTube said', 'Youtube says'))

        new.callback("Fetched video info")

        self._title = self._ydl_info['title']
        self._author = self._ydl_info['uploader']
        self._rating = self._ydl_info['average_rating']
        self._length = self._ydl_info['duration']
        self._viewcount = self._ydl_info['view_count']
        self._likes = self._ydl_info['like_count']
        self._dislikes = self._ydl_info['dislike_count']
        self._username = self._ydl_info['uploader_id']
        self._category = self._ydl_info['categories'][0]
        if self._ydl_info['height'] >= 480:
            self._bigthumb = g.urls['bigthumb'] % self.videoid
        if self._ydl_info['height'] >= 720:
            self._bigthumbhd = g.urls['bigthumbhd'] % self.videoid

        self.expiry = time.time() + g.lifespan

        self._have_basic = True

    def _fetch_gdata(self):
        """ Extract gdata values, fetch gdata if necessary. """
        if self._have_gdata:
            return

        gdata = get_video_gdata(self.videoid)
        item = json.loads(gdata)['items'][0]
        snippet = item['snippet']
        self._published = uni(snippet['publishedAt'])
        self._description = uni(snippet["description"])
        self._keywords = [uni(i) for i in snippet['tags']]
        self._have_gdata = True

    def _process_streams(self):
        """ Create Stream object lists from internal stream maps. """

        if not self._have_basic:
            self._fetch_basic()

        allstreams = [Stream(z, self) for z in self._ydl_info['formats']]
        self._streams = [i for i in allstreams if i.mediatype == 'normal']
        self._audiostreams = [i for i in allstreams if i.mediatype == 'audio']
        self._videostreams = [i for i in allstreams if i.mediatype == 'video']
        self._m4astreams = [i for i in allstreams if i.extension == 'm4a']
        self._oggstreams = [i for i in allstreams if i.extension == 'ogg']
        self._allstreams = allstreams


    def __repr__(self):
        """ Print video metadata. Return utf8 string. """
        if self._have_basic:
            keys = "Title Author ID Duration Rating Views Thumbnail"
            keys = keys.split(" ")
            keywords = ", ".join(self.keywords)
            info = {"Title": self.title,
                    "Author": self.author,
                    "Views": self.viewcount,
                    "Rating": self.rating,
                    "Duration": self.duration,
                    "ID": self.videoid,
                    "Thumbnail": self.thumb}

            nfo = "\n".join(["%s: %s" % (k, info.get(k, "")) for k in keys])

        else:
            nfo = "Pafy object: %s [%s]" % (self.videoid,
                                            self.title[:45] + "..")

        return nfo.encode("utf8", "replace") if pyver == 2 else nfo

    @property
    def streams(self):
        """ The streams for a video. Returns list."""
        if not self._streams:
            self._process_streams()

        return self._streams

    @property
    def allstreams(self):
        """ All stream types for a video. Returns list. """
        if not self._allstreams:
            self._process_streams()

        return self._allstreams

    @property
    def audiostreams(self):
        """ Return a list of audio Stream objects. """
        if not self._audiostreams:
            self._process_streams()

        return self._audiostreams

    @property
    def videostreams(self):
        """ The video streams for a video. Returns list. """
        if not self._videostreams:
            self._process_streams()

        return self._videostreams

    @property
    def oggstreams(self):
        """ Return a list of ogg encoded Stream objects. """
        if not self._oggstreams:
            self._process_streams()

        return self._oggstreams

    @property
    def m4astreams(self):
        """ Return a list of m4a encoded Stream objects. """
        if not self._m4astreams:
            self._process_streams()

        return self._m4astreams

    @property
    def title(self):
        """ Return YouTube video title as a string. """
        if not self._title:
            self._fetch_basic()

        return self._title

    @property
    def author(self):
        """ The uploader of the video. Returns str. """
        if not self._author:
            self._fetch_basic()

        return self._author

    @property
    def rating(self):
        """ Rating for a video. Returns float. """
        if not self._rating:
            self._fetch_basic()

        return self._rating

    @property
    def length(self):
        """ Length of a video in seconds. Returns int. """
        if not self._length:
            self._fetch_basic()

        return self._length

    @property
    def viewcount(self):
        """ Number of views for a video. Returns int. """
        if not self._viewcount:
            self._fetch_basic()

        return self._viewcount

    @property
    def bigthumb(self):
        """ Large thumbnail image url. Returns str. """
        self._fetch_basic()
        return self._bigthumb

    @property
    def bigthumbhd(self):
        """ Extra large thumbnail image url. Returns str. """
        self._fetch_basic()
        return self._bigthumbhd

    @property
    def thumb(self):
        """ Thumbnail image url. Returns str. """
        return g.urls['thumb'] % self.videoid

    @property
    def duration(self):
        """ Duration of a video (HH:MM:SS). Returns str. """
        if not self._length:
            self._fetch_basic()

        self._duration = time.strftime('%H:%M:%S', time.gmtime(self._length))
        self._duration = uni(self._duration)

        return self._duration

    @property
    def keywords(self):
        """ Return keywords as list of str. """
        if not self._keywords:
            self._fetch_gdata()

        return self._keywords

    @property
    def category(self):
        """ YouTube category of the video. Returns string. """
        if not self._category:
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
        if not self._username:
            self._fetch_basic()

        return self._username

    @property
    def published(self):
        """ The upload date and time of the video. Returns string. """
        if not self._published:
            self._fetch_gdata()

        return self._published.replace(".000Z", "").replace("T", " ")

    @property
    def likes(self):
        """ The number of likes for the video. Returns int. """
        if not self._likes:
            self._fetch_basic()

        return self._likes

    @property
    def dislikes(self):
        """ The number of dislikes for the video. Returns int. """
        if not self._dislikes:
            self._fetch_basic()

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
        self.playlist_meta = pl_data


def get_categoryname(cat_id):
    """ Returns a list of video category names for one category ID. """
    timestamp = time.time()
    cat_cache = cache('categories')
    cached = cat_cache.get(cat_id, {})
    if cached.get('updated', 0) > timestamp - g.lifespan:
        return cached.get('title', 'unknown')
    # call videoCategories API endpoint to retrieve title
    url = g.urls['vidcat']
    query = {'id': cat_id,
             'part': 'snippet',
             'key': g.api_key}
    url += "?" + urlencode(query)
    catinfo = json.loads(fetch_decode(url))
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
        url = g.urls['vidcat']
        query = {'id': ','.join(idlist),
                 'part': 'snippet',
                 'key': g.api_key}
        url += "?" + urlencode(query)
        catinfo = json.loads(fetch_decode(url))
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


def get_playlist(playlist_url, basic=False, gdata=False, signature=True,
                 size=False, callback=lambda x: None):
    """ Return a dict containing Pafy objects from a YouTube Playlist.

    The returned Pafy objects are initialised using the arguments to
    get_playlist() in the manner documented for pafy.new()

    """
    # pylint: disable=R0914
    # too many local vars

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


def set_api_key(key):
    """Sets the api key to be used with youtube."""
    g.api_key = key
