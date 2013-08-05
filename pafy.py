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
    if len(s) == 92:
        return s[25] + s[3:25] + s[0] + s[26:42] + s[79] + s[43:79] + s[91] + \
                s[80:83]
    elif len(s) == 90:
        return s[25] + s[3:25] + s[2] + s[26:40] + s[77] + s[41:77] + s[89] + \
                s[78:81]
    elif len(s) == 88:
        return s[48] + s[81:67:-1] + s[82] + s[66:62:-1] + s[85] + s[61:48:-1]\
                + s[67] + s[47:12:-1] + s[3] + s[11:3:-1] + s[2] + s[12]
    elif len(s) == 87:
        return s[4:23] + s[86] + s[24:85]
    elif len(s) == 86:
        return s[83:85] + s[26] + s[79:46:-1] + s[85] + s[45:36:-1] + s[30] + \
                s[35:30:-1] + s[46] + s[29:26:-1] + s[82] + s[25:1:-1]
    elif len(s) == 85:
        return s[2:8] + s[0] + s[9:21] + s[65] + s[22:65] + s[84] + s[66:82] +\
                s[21]
    elif len(s) == 84:
        return s[83:36:-1] + s[2] + s[35:26:-1] + s[3] + s[25:3:-1] + s[26]
    elif len(s) == 83:
        return s[:15] + s[80] + s[16:80] + s[15]
    elif len(s) == 82:
        return s[36] + s[79:67:-1] + s[81] + s[66:40:-1] + s[33] + s[39:36:-1]\
                + s[40] + s[35] + s[0] + s[67] + s[32:0:-1] + s[34]
    elif len(s) == 81:
        return s[56] + s[79:56:-1] + s[41] + s[55:41:-1] + s[80] + s[40:34:-1]\
                + s[0] + s[33:29:-1] + s[34] + s[28:9:-1] + s[29] + s[8:0:-1] + s[9]
    elif len(s) == 79:
        return s[54] + s[77:54:-1] + s[39] + s[53:39:-1] + s[78] + s[38:34:-1]\
                + s[0] + s[33:29:-1] + s[34] + s[28:9:-1] + s[29] + s[8:0:-1] + s[9]
    else:
        raise NameError("Unable to decode video url - sig len %s" % len(s))

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

    def get_filesize(self):
        opener = self._opener
        return int(opener.open(self.url).headers['content-length'])

    def download(self, progress=True, filepath=""):
        response = self._opener.open(self.url)
        total = int(response.info().getheader('Content-Length').strip())
        print u"-Downloading '{}' [{:,} Bytes]".format(self.filename, total)
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
            watchurl = "https://www.youtube.com/watch?v=" + vidid
            watchinfo = opener.open(watchurl).read()
            match = re.search(r';ytplayer.config = ({.*?});', watchinfo)
            try:
                myjson = json.loads(match.group(1))
            except:
                raise NameError('Problem handling this video')
            args = myjson['args']
            streamMap = args['url_encoded_fmt_stream_map'].split(",")
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
