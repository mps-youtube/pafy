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

__version__ = "0.3.05"
__author__ = "nagev"
__license__ = "GPLv3"

import re
import sys
import time
import json
import logging
import urllib
import urllib2
from urlparse import parse_qs

logging.basicConfig(level=logging.INFO)

def dojsfunc2(f1argname, f2arg1, f2arg2, f2name, f2bod, sig):
    f2parts = f2bod.split(";")
    newvarname = ""
    newvarval = 0
    for part in f2parts:
        # newvar is an index of sig
        if re.match(r'var\s(\w)=(\w)\[(\d+)\]', part):
            match = re.match(r'var\s(\w)=(\w)\[(\d+)\]', part)
            newvarname = match.group(1)
            if match.group(2) == f1argname:
                newvarval = sig[int(match.group(3))]
            else:
                raise RuntimeError("no match in f2 for part: %s" % part)
        # a[n]=a[b%a.length]
        elif re.match(r'(\w)\[(\d+)\]=(\w)\[(\w)\%(\w)\.length\]', part):
            match = re.match(r'(\w)\[(\d+)\]=(\w)\[(\w)\%(\w)\.length\]', part)
            if match.group(1) == f1argname and match.group(3) == f1argname and\
                match.group(4) == 'b' and match.group(5) == f1argname:
                index = int(match.group(2))
                newchar = sig[(int(f2arg2) % len(sig))]
                sig = sig[:index] + newchar + sig[index + 1:]
            else:
                raise RuntimeError("no match in f2 for part: %s" % part)
        # a[b]=c
        elif re.match(r'(\w)\[(\w)\]=(\w)', part):
            match = re.match(r'(\w)\[(\w)\]=(\w)', part)
            if match.group(1) == f1argname and match.group(2) == 'b' and\
                match.group(3) == newvarname:
                index = int(f2arg2)
                sig = sig[:index] + str(newvarval) + sig[index + 1:]
            else:
                raise RuntimeError("no match in f2 for part: %s" % part)
        elif re.match(r'return\sa', part):
            return sig
        else:
            raise RuntimeError("no match in f2 for part: %s" % part)
            
def dojs(sig, f1arg, f1bod, f2name=None, f2arg=None, f2bod=None):
    # split js function components
    f1parts = f1bod.split(";")
    for part in f1parts:
        # split, do nothing
        if re.match(r'%s=%s\.split\(""\)' % (f1arg, f1arg), part):
            pass
        # call secondary function
        elif re.match(r'%s=%s\((\w+),(\w+)\)' % (f1arg, f2name), part):
            match = re.match(r'%s=%s\((\w+),(\w+)\)' % (f1arg, f2name), part)
            f2arg1, f2arg2 = match.group(1), match.group(2)
            sig = dojsfunc2(f1arg, f2arg1, f2arg2, f2name, f2bod, sig)
        # reverse        
        elif re.match(r'%s=%s\.reverse\(\)' % (f1arg, f1arg), part):
            sig = sig[::-1]
        # slice
        elif re.match(r'%s=%s\.slice\((\d+)\)' % (f1arg, f1arg), part):
            match = re.match(r'%s=%s\.slice\((\d+)\)' % (f1arg, f1arg), part)
            sliceval = int(match.group(1))
            sig = sig[sliceval:]
        # return
        elif re.match(r'return %s\.join\(""\)' % f1arg, part):
            return sig
        else:
            raise RuntimeError("no match for %s" % part)

def _decodesig(s, js):
    logging.debug("sig length: %s" % len(s))
    match = re.search(r'g.sig\|\|(\w+)\(g.s\)', js)
    f1name = match.group(1)
    match = re.search(r'function %s\((\w+)\)\{([^\{]+)\}' % f1name, js)
    f1arg = match.group(1)
    f1bod = match.group(2)
    match = re.search(r'(\w+)\(\w+,\d+\)', f1bod)
    if match:
        f2name = match.group(1)
        match = re.search(r'(function %s\((\w+,\w+)\)\{([^\{]+)\})' % f2name,
               js)
        f2 = match.group(1)
        f2arg = match.group(2)
        f2bod = match.group(3)
        return dojs(s, f1arg, f1bod, f2name, f2arg, f2bod)
    else:
        return dojs(s, f1arg, f1bod)

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

    def __init__(self, streammap, opener, title="ytvid", js=None):
        if not streammap.get("sig", ""):
            logging.debug("Decrypting sig: %s" % streammap['s'])
            streammap['sig'] = [_decodesig(streammap['s'][0], js)]
            logging.debug("Calculated decrypted sig: %s" % streammap['sig'][0])
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
        print (u"-Downloading '{}' [{:,} Bytes]".format(self.filename,
            total)).encode('UTF-8')
        status_string = ('  {:,} Bytes [{:.2%}] received. Rate: [{:4.0f} '
                         'kbps].  ETA: [{:.0f} secs]')
        chunksize, bytesdone, t0 = 1024, 0, time.time()
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
        try:
            vidid = re.search(r'v=([a-zA-Z0-9-_]*)', video_url).group(1)
        except:
            raise RuntimeError("bad video url")
        infoUrl += vidid + "&asv=3&el=detailpage&hl=en_US"
        self.urls = []
        opener = urllib2.build_opener()
        ua = ("Mozilla/5.0 (compatible; MSIE 9.0; Windows NT 6.1; WOW64;"
              "Trident/5.0)")
        opener.addheaders = [('User-Agent', ua)]
        self.keywords = ""
        logging.debug("requested info page: %s" % infoUrl)
        self.rawinfo = opener.open(infoUrl).read()
        logging.debug("got info")
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
        js = None
        if not smap[0].get("sig", ""):  # vevo!
            watchurl = "https://www.youtube.com/watch?v=" + vidid
            logging.debug("request watch?v page: %s" % watchurl)
            watchinfo = opener.open(watchurl).read()
            logging.debug("got watch?v page")
            match = re.search(r';ytplayer.config = ({.*?});', watchinfo)
            try:
                myjson = json.loads(match.group(1))
            except:
                raise NameError('Problem handling this video')
            args = myjson['args']
            streamMap = args['url_encoded_fmt_stream_map'].split(",")
            html5player = myjson['assets']['js']
            logging.debug("getting js url: %s" % html5player)
            js = opener.open(html5player).read()
            logging.debug("got js from %s" % html5player)
            smap = [parse_qs(sm) for sm in streamMap]
        self.streams = [Stream(sm, opener, self.title, js) for sm in smap]

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
