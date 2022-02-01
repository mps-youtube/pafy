import os
import re
import sys
import time
import logging
import subprocess

if sys.version_info[:2] >= (3, 0):
    # pylint: disable=E0611,F0401,I0011
    from urllib.request import urlopen, build_opener
    from urllib.error import HTTPError, URLError
    from urllib.parse import parse_qs, urlparse
    uni, pyver = str, 3

else:
    from urllib2 import urlopen, build_opener, HTTPError, URLError
    from urlparse import parse_qs, urlparse
    uni, pyver = unicode, 2

early_py_version = sys.version_info[:2] < (2, 7)

from . import __version__, g
from .pafy import call_gdata
from .playlist import get_playlist2
from .util import xenc

dbg = logging.debug


def extract_video_id(url):
    """ Extract the video id from a url, return video id as str. """
    idregx = re.compile(r'[\w-]{11}$')
    url = str(url).strip()

    if idregx.match(url):
        return url # ID of video

    if '://' not in url:
        url = '//' + url
    parsedurl = urlparse(url)
    if parsedurl.netloc in ('youtube.com', 'www.youtube.com', 'm.youtube.com', 'gaming.youtube.com'):
        query = parse_qs(parsedurl.query)
        if 'v' in query and idregx.match(query['v'][0]):
            return query['v'][0]
    elif parsedurl.netloc in ('youtu.be', 'www.youtu.be'):
        vidid = parsedurl.path.split('/')[-1] if parsedurl.path else ''
        if idregx.match(vidid):
            return vidid

    err = "Need 11 character video id or the URL of the video. Got %s"
    raise ValueError(err % url)


class BasePafy(object):

    """ Class to represent a YouTube video. """

    def __init__(self, video_url, basic=True, gdata=False,
                 size=False, callback=None, ydl_opts=None):
        """ Set initial values. """
        self.version = __version__
        self.videoid = extract_video_id(video_url)
        self.watchv_url = g.urls['watchv'] % self.videoid

        self.callback = callback
        self._have_basic = False
        self._have_gdata = False

        self._description = None
        self._likes = None
        self._category = None
        self._published = None
        self._username = None

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
        self._bestthumb = None
        self._mix_pl = None
        self.expiry = None

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
        raise NotImplementedError


    def _fetch_gdata(self):
        """ Extract gdata values, fetch gdata if necessary. """
        raise NotImplementedError


    def _get_video_gdata(self, video_id):
        """ Return json string containing video metadata from gdata api. """
        if self.callback:
            self.callback("Fetching video gdata")
        query = {'part': 'id,snippet,statistics',
                 'maxResults': 1,
                 'id': video_id}
        gdata = call_gdata('videos', query)
        dbg("Fetched video gdata")
        if self.callback:
            self.callback("Fetched video gdata")
        return gdata


    def _process_streams(self):
        """ Create Stream object lists from internal stream maps. """
        raise NotImplementedError


    def __repr__(self):
        """ Print video metadata. Return utf8 string. """
        if self._have_basic:
            info = [("Title", self.title),
                    ("Author", self.author),
                    ("ID", self.videoid),
                    ("Duration", self.duration),
                    ("Rating", self.rating),
                    ("Views", self.viewcount),
                    ("Thumbnail", self.thumb)]

            nfo = "\n".join(["%s: %s" % i for i in info])

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
    def mix(self):
        """ The playlist for the related YouTube mix. Returns a Playlist object. """
        if self._mix_pl is None:
            try:
                self._mix_pl = get_playlist2("RD" + self.videoid)
            except IOError:
                return None
        return self._mix_pl

    def _sortvideokey(self, x, key3d=0, keyres=0, keyftype=0, preftype="any", ftypestrict=True):
        """ Sort function. """
        key3d = "3D" not in x.resolution
        keyres = int(x.resolution.split("x")[0])
        keyftype = preftype == x.extension
        strict, nonstrict = (key3d, keyftype, keyres), (key3d, keyres, keyftype)
        return strict if ftypestrict else nonstrict

    def _getvideo(self, preftype="any", ftypestrict=True, vidonly=False, quality="max"):
        """
        Return the highest/lowest resolution video available.

        Select from video-only streams if vidonly is True
        """
        streams = self.videostreams if vidonly else self.streams

        if not streams:
            return None

        if quality == "max":
        	r = max(streams, key=lambda x:self._sortvideokey(x, preftype=preftype, ftypestrict=ftypestrict))
        elif quality == "min":
        	r = min(streams, key=lambda x:self._sortvideokey(x, preftype=preftype, ftypestrict=ftypestrict))
        else:
            return None

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
        return self._getvideo(preftype, ftypestrict, vidonly=True, quality="max")

    def getworstvideo(self, preftype="any", ftypestrict=True):
    	""" Return the worst resolution video-only stream. """
    	return self._getvideo(preftype, ftypestrict, vidonly=True, quality="min")

    def getbest(self, preftype="any", ftypestrict=True):
        """
        Return the highest resolution video+audio stream.

        set ftypestrict to False to return a non-preferred format if that
        has a higher resolution
        """
        return self._getvideo(preftype, ftypestrict, vidonly=False, quality="max")

    def getworst(self, preftype="any", ftypestrict=True):
    	""" Return the lowest resolution video+audio stream. """
    	return self._getvideo(preftype, ftypestrict, vidonly=False, quality="min")

    def _sortaudiokey(self, x, keybitrate=0, keyftype=0, preftype="any", ftypestrict=True):
        """ Sort function. """
        keybitrate = int(x.rawbitrate)
        keyftype = preftype == x.extension
        strict, nonstrict = (keyftype, keybitrate), (keybitrate, keyftype)
        return strict if ftypestrict else nonstrict

    def getbestaudio(self, preftype="any", ftypestrict=True):
        """ Return the highest bitrate audio Stream object."""
        if not self.audiostreams:
            return None

        r = max(self.audiostreams, key=lambda x:self._sortaudiokey(x, preftype=preftype, ftypestrict=ftypestrict))

        if ftypestrict and preftype != "any" and r.extension != preftype:
            return None

        else:
            return r

    def getworstaudio(self, preftype="any", ftypestrict=True):
        """ Return the lowest bitrate audio Stream object."""
        if not self.audiostreams:
            return None

        r = min(self.audiostreams, key=lambda x:self._sortaudiokey(x, preftype=preftype, ftypestrict=ftypestrict))

        if ftypestrict and preftype != "any" and r.extension != preftype:
            return None

        else:
            return r

    @classmethod
    def _content_available(cls, url):
        try:
            response = urlopen(url)
        except HTTPError:
            return False
        else:
            return response.getcode() < 300

    def getbestthumb(self):
        """ Return the best available thumbnail."""
        if not self._bestthumb:
            part_url = "http://i.ytimg.com/vi/%s/" % self.videoid
            # Thumbnail resolution sorted in descending order
            thumbs = ("maxresdefault.jpg",
                      "sddefault.jpg",
                      "hqdefault.jpg",
                      "mqdefault.jpg",
                      "default.jpg")
            for thumb in thumbs:
                url = part_url + thumb
                if self._content_available(url):
                    return url

        return self._bestthumb

    def populate_from_playlist(self, pl_data):
        """ Populate Pafy object with items fetched from playlist data. """
        self._title = pl_data.get("title")
        self._author = pl_data.get("author")
        self._length = int(pl_data.get("length_seconds", 0))
        self._rating = pl_data.get("rating", 0.0)
        self._viewcount = "".join(re.findall(r"\d", "{0}".format(pl_data.get("views", "0"))))
        self._viewcount = int(self._viewcount)
        self._description = pl_data.get("description")


class BaseStream(object):

    """ YouTube video stream class. """

    def __init__(self, parent):
        """ Set initial values. """
        self._itag = None
        self._mediatype = None
        self._threed = None
        self._rawbitrate = None
        self._resolution = None
        self._quality = None
        self._dimensions = None
        self._bitrate = None
        self._extension = None
        self.encrypted = None
        self._notes = None
        self._url = None
        self._rawurl = None

        self._parent = parent
        self._filename = None
        self._fsize = None
        self._active = False

    def generate_filename(self, meta=False, max_length=None):
        """ Generate filename. """
        ok = re.compile(r'[^/]')

        if os.name == "nt":
            ok = re.compile(r'[^\\/:*?"<>|]')

        filename = "".join(x if ok.match(x) else "_" for x in self.title)

        if meta:
            filename += " - %s - %s" % (self._parent.videoid, self.itag)

        if max_length:
            max_length = max_length + 1 + len(self.extension)
            if len(filename) > max_length:
                filename = filename[:max_length-3] + '...'

        filename += "." + self.extension
        return xenc(filename)

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
        return self._parent.title

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
        if not self._filename:
            self._filename = self.generate_filename()
        return self._filename

    @property
    def url(self):
        """ Return the url, decrypt if required. """
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

    def download(self, filepath="", quiet=False, progress="Bytes",
                           callback=None, meta=False, remux_audio=False):
        """ Download.  Use quiet=True to supress output. Return filename.

        Use meta=True to append video id and itag to generated filename
        Use remax_audio=True to remux audio file downloads

        """
        # pylint: disable=R0912,R0914
        # Too many branches, too many local vars
        savedir = filename = ""

        if filepath and os.path.isdir(filepath):
            savedir, filename = filepath, self.generate_filename(max_length=256-len('.temp'))

        elif filepath:
            savedir, filename = os.path.split(filepath)

        else:
            filename = self.generate_filename(meta=meta, max_length=256-len('.temp'))

        filepath = os.path.join(savedir, filename)
        temp_filepath = filepath + ".temp"

        progress_available = ["KB", "MB", "GB"]
        if progress not in progress_available:
            progress = "Bytes"

        status_string = get_status_string(progress)

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
            else:  # Avoid ZeroDivisionError
                rate = 0
                eta = 0

            progress_stats = (get_size_done(bytesdone, progress),
                              bytesdone * 1.0 / total, rate, eta)

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


def remux(infile, outfile, quiet=False, muxer="ffmpeg"):
    """ Remux audio. """
    muxer = muxer if isinstance(muxer, str) else "ffmpeg"

    for tool in set([muxer, "ffmpeg", "avconv"]):
        cmd = [tool, "-y", "-i", infile, "-acodec", "copy", "-vn", outfile]

        try:
            with open(os.devnull, "w") as devnull:
                subprocess.call(cmd, stdout=devnull, stderr=subprocess.STDOUT)

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


def get_size_done(bytesdone, progress):
    _progress_dict = {'KB': 1024.0, 'MB': 1048576.0, 'GB': 1073741824.0}
    return round(bytesdone/_progress_dict.get(progress, 1.0), 2)


def get_status_string(progress):
    status_string = ('  {:,} ' + progress + ' [{:.2%}] received. Rate: [{:4.0f} '
                     'KB/s].  ETA: [{:.0f} secs]')

    if early_py_version:
        status_string = ('  {0:} ' + progress + ' [{1:.2%}] received. Rate:'
                         ' [{2:4.0f} KB/s].  ETA: [{3:.0f} secs]')

    return status_string
