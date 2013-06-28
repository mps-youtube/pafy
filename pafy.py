#!/usr/bin/python

''' Python API for YouTube
    Copyright (C)  2013 nagev

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.  '''

__version__ = "0.2"
__author__ = "nagev"
__license__ = "GPLv3"

import re
import sys
import time
import json
import urllib
import urllib2
from urlparse import parse_qs

def _decrypt_signature(s):
    " copied this function from youtube-dl source. thanks!"
    (a, b) = s.split('.')
    if len(a) != 43 or len(b) != 43:
        sys.exit("failed (" + str(len(a)) + ", " + str(len(b)) + ")")
    b = ''.join([b[:8],a[0],b[9:18],b[-4],b[19:39], b[18]])[0:40]
    a = a[-40:]
    s_dec = '.'.join((a,b))[::-1]
    return s_dec

class Stream():
    resolutions = {
        '5': ('240x400', 'flv'),
        '17': ('144x176', '3gp'),
        '18': ('360x640', 'mp4'),
        '22': ('720x1280', 'mp4'),
        '34': ('360x640', 'flv'),
        '35': ('480x854', 'flv'),
        '36': ('320x240', '3gp'),
        '37': ('1080x1920', 'mp4'),
        '38': ('3072x4096', 'superHD'),
        '43': ('360x640', 'webm'),
        '44': ('480x854', 'webm'),
        '45': ('720x1280', 'webm'),
        '46': ('1080x1920', 'webm'),
        '82': ('640x360-3D', 'mp4'),
        '84': ('1280x720-3D', 'mp4'),
        '100': ('640x360-3D', 'webm'),
        '102': ('1280x720-3D', 'webm')}

    def __init__(self, streammap, opener, title="ytvid"):
        if not streammap.get("sig", ""):
            streammap['sig'] = [_decrypt_signature(streammap['s'][0])]
        self.url = streammap['url'][0] + '&signature=' + streammap['sig'][0]
        self.vidformat = streammap['type'][0].split(';')[0]
        self.resolution = self.resolutions[streammap['itag'][0]][0]
        self.extension = self.resolutions[streammap['itag'][0]][1]
        self.itag = streammap['itag'][0]
        self.title = title
        self.filename = self.title + "." + self.extension
        self._opener = opener

    def download(self, progress=True, filepath=""):
        response = self._opener.open(self.url)
        total = int(response.info().getheader('Content-Length').strip())
        print "-Downloading '{}' [{:,} Bytes]".format(self.filename, total)
        status_string = ('  {:,} Bytes [{:.2%}] received. Rate: [{:4.0f} '
                         'kbps].  ETA: [{:.0f} secs]')
        chunksize, bytesdone, t0 = 16834, 0, time.time()
        outfh = open(filepath or self.filename, 'wb')
        while 1:
            chunk = response.read(chunksize)
            elapsed = time.time() - t0
            outfh.write(chunk)
            bytesdone += len(chunk)
            if not chunk:
                outfh.close()
                break
            if progress:
                rate = (bytesdone / 1024) / elapsed
                eta = (total - bytesdone) / (rate * 1024)
                display = (bytesdone, bytesdone * 1.0 / total, rate, eta)
                status = status_string.format(*display)
                sys.stdout.write("\r" + status + ' ' * 4 + "\r")
                sys.stdout.flush
        print "\nDone"


class Pafy():

    def __len__(self):
        return self.length

    def __repr__(self):
        out = ""
        keys = "Title Author ID Duration Rating Views Thumbnail Keywords"
        keys = keys.split(" ")
        keywords = ", ".join(self.keywords).decode("utf8")
        length = time.strftime('%H:%M:%S', time.gmtime(self.length))
        info = dict(Title=self.title,
                    Author=self.author,
                    Views=self.viewcount,
                    Rating=self.rating,
                    Duration=length,
                    ID=self.videoid,
                    Thumbnail=self.thumb,
                    Keywords=keywords)
        for k in keys:
            try:
                out += "%s: %s\n" % (k, info[k])
            except KeyError:
                pass
        return out.encode("utf8", "ignore")

    def __init__(self, video_url):
        infoUrl = 'https://www.youtube.com/get_video_info?video_id='
        vidid = re.search(r'v=([a-zA-Z0-9-_]*)', video_url).group(1)
        infoUrl += vidid + "&asv=3&el=detailpage&hl=en_US"
        self.urls = []
        opener = urllib2.build_opener()
        ua = ("Mozilla/5.0 (compatible; MSIE 9.0; Windows NT 6.1; WOW64;"
              "Trident/5.0)")
        opener.addheaders = [('User-Agent', ua)]
        self.keywords = ""
        self.rawinfo = opener.open(infoUrl).read()
        origUrl = "https://www.youtube.com/watch?v=" + vidid
        self.origrawinfo = opener.open(origUrl).read()
        match = re.search(r';ytplayer.config = ({.*?});', self.origrawinfo)
        try:
            myjson = json.loads(match.group(1))
        except:
            raise NameError('Problem handling this video')
        args = myjson['args']
        urlefsm = args['url_encoded_fmt_stream_map'].split(",")
        self.allinfo = parse_qs(self.rawinfo)
        self.title = self.allinfo['title'][0].decode('utf-8')
        self.author = self.allinfo['author'][0]
        self.videoid = self.allinfo['video_id'][0]
        if 'keywords' in self.allinfo:
            self.keywords = self.allinfo['keywords'][0].split(',')
        self.rating = float(self.allinfo['avg_rating'][0])
        self.length = int(self.allinfo['length_seconds'][0])
        self.duration = time.strftime('%H:%M:%S', time.gmtime(self.length))
        self.viewcount = int(self.allinfo['view_count'][0])
        self.thumb = urllib.unquote_plus(self.allinfo['thumbnail_url'][0])
        self.formats = self.allinfo['fmt_list'][0].split(",")
        self.formats = [x.split("/") for x in self.formats]
        if self.allinfo.get('iurlsd'):
            self.bigthumb = self.allinfo['iurlsd'][0]
        if self.allinfo.get('iurlmaxres'):
            self.bigthumbhd = self.allinfo['iurlmaxres'][0]
        streamMap = self.allinfo['url_encoded_fmt_stream_map'][0].split(',')
        smap = [parse_qs(sm) for sm in streamMap]
        if not smap[0].get("sig", ""):  # vevo!
            streamMap = urlefsm
            smap = [parse_qs(sm) for sm in streamMap]
        self.streams = [Stream(sm, opener, self.title) for sm in smap]

    def getbest(self, preftype="any", ftypestrict=True):
        # set ftypestrict to False to use a non preferred format if that
        # has a higher resolution
        def _sortkey(x, key3d=0, keyres=0, keyftype=0):
            key3d = "3D" not in x.resolution
            keyres = int(x.resolution.split("x")[0])
            keyftype = preftype == x.extension
            if ftypestrict:
                return (key3d, keyftype, keyres)
            else:
                return (key3d, keyres, keyftype)
        return max(self.streams, key=_sortkey)
