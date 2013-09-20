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

__version__ = "0.3.08"
__author__ = "nagev"
__license__ = "GPLv3"

import re
import sys
import time
import json
import logging

def decode_if_py3(data):
    return data.decode("UTF-8")

if sys.version_info[:2] >= (3, 0):
    from urllib.request import build_opener
    from urllib.parse import parse_qs, unquote_plus
else:
    decode_if_py3 = lambda x: x
    from urllib2 import build_opener
    from urllib import unquote_plus
    from urlparse import parse_qs

logging.basicConfig(level=logging.DEBUG)

def _extract_function_from_js(name, js):
    # Find a function called `name` and extract components
    m = re.search(r'function %s\(((?:\w+,?)+)\)\{([^}]+)\}' % name, js)
    return {'name': name, 'parameters': m.group(1).split(","),
        'body': m.group(2) }

def _getval(val, argsdict): # resolves variable values. preserves int literals
    m = re.match(r'(\d+)', val)
    if m:
        return(int(m.group(1)))
    elif val in argsdict:
        return argsdict[val]
    else:
        raise RuntimeError("Error val %s from dict %s" % (val, argsdict))

def _get_func_from_call(caller_function, name, arguments, js):
    newfunction = _extract_function_from_js(name, js)
    newfunction['args'] = {}
    for n, arg in enumerate(arguments):
        value = _getval(arg, caller_function['args'])
        param = newfunction['parameters'][n]
        newfunction['args'][param] = value
    return newfunction

def _solve(f, js):
    # solve basic javascript function
    parts = f['body'].split(";")
    for part in parts:
        logging.debug("Working on part: %s" % part)
        # split or join, do nothing
        m = re.match(r'(\w+)=(\w+)\.(?:split|join)\(""\)', part)
        if m and m.group(1) == m.group(2):
            continue
        m = re.match(r'(\w+)=(\w+)\(((?:\w+,?)+)\)', part)
        if m: # a function call
            lhs, funcname, args = m.group(*range(1,4))
            newfunc = _get_func_from_call(f, funcname, args.split(","), js)
            f['args'][lhs] = _solve(newfunc, js) # recursive call
            continue
        m = re.match(r'var\s(\w+)=(\w+)\[(\w+)\]', part)
        if m: # new var is an index of another var; eg: var a = b[c]
            b, c = [_getval(x, f['args']) for x in m.group(*range(2,4))]
            f['args'][m.group(1)] = b[c]
            continue
        m = re.match(r'(\w+)\[(\w+)\]=(\w+)\[(\w+)\%(\w+)\.length\]', part)
        if m: # a[b]=c[d%e.length]
            vals = m.group(*range(1,6))
            a, b, c, d, e = [_getval(x, f['args']) for x in vals]
            f['args'][m.group(1)] = a[:b] + c[d % len(e)] + a[b + 1:] 
            continue
        m = re.match(r'(\w+)\[(\w+)\]=(\w+)', part)
        if m: # a[b]=c
            a, b, c = [_getval(x, f['args']) for x in m.group(*range(1,4))]
            f['args'][m.group(1)] = a[:b] + c + a[b + 1:] # a[b] = c
            continue
        m= re.match(r'return (\w+)(\.join\(""\))?', part)
        if m: # return
            return f['args'][m.group(1)]
        m = re.match(r'(\w+)=(\w+)\.reverse\(\)', part)
        if m: # reverse        
            f['args'][m.group(1)] = _getval(m.group(2), f['args'])[::-1]
            continue
        m = re.match(r'(\w+)=(\w+)\.slice\((\w+)\)', part)
        if m:  # slice a=b.slice(c)
            a, b, c = [_getval(x, f['args']) for x in m.group(*range(1,4))]
            f['args'][m.group(1)] = b[c:]
            continue
        raise RuntimeError("no match for %s" % part)

def _decodesig(sig, js):
    # get main function name from a function call
    m = re.search(r'\w\.sig\|\|(\w+)\(\w+\.\w+\)', js)
    funcname = m.group(1)
    function = _extract_function_from_js(funcname, js)
    if not len(function['parameters']) == 1:
        raise RuntimeError("Main sig js function has more than one arg: %s" %
            function['parameters'])
    function['args'] = {function['parameters'][0]: sig}
    return _solve(function, js)

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
            logging.debug("Decrypting sig: %s" % streammap['s'][0])
            streammap['sig'] = [_decodesig(streammap['s'][0], js)]
            logging.debug("Calculated decrypted sig: %s" % streammap['sig'][0])
        self.url = streammap['url'][0] + '&signature=' + streammap['sig'][0]
        self.vidformat = streammap['type'][0].split(';')[0]
        self.resolution = self.resolutions[streammap['itag'][0]][0]
        self.extension = self.resolutions[streammap['itag'][0]][1]
        self.itag = streammap['itag'][0]
        self.title = title
        self.filename = self.title + "." + self.extension
        self.filesize = None
        self._opener = opener

    def get_filesize(self):
        if not self.filesize:
            opener = self._opener
            self.filesize = int(opener.open(self.url).headers['content-length'])
        return self.filesize

    def download(self, filepath="", quiet=False, callback=None):
        status_string = ('  {:,} Bytes [{:.2%}] received. Rate: [{:4.0f} '
                         'kbps].  ETA: [{:.0f} secs]')
        response = self._opener.open(self.url)
        total = int(response.info()['Content-Length'].strip())
        chunksize, bytesdone, t0 = 16384, 0, time.time()
        outfh = open(filepath or self.filename, 'wb')
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


class Pafy():

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

    def _setmetadata(self, allinfo):
        f = lambda x: allinfo[x][0]
        self.title = f('title')
        self.author = f('author')
        self.videoid = f('video_id')
        self.rating = float(f('avg_rating'))
        self.length = int(f('length_seconds'))
        self.viewcount = int(f('view_count'))
        self.thumb = unquote_plus(f('thumbnail_url'))
        self.duration = time.strftime('%H:%M:%S', time.gmtime(self.length))
        self.formats = f('fmt_list').split(",")
        self.formats = [x.split("/") for x in self.formats]
        if 'keywords' in allinfo:
            self.keywords = f('keywords').split(',')
        if allinfo.get('iurlsd'):
            self.bigthumb = f('iurlsd')
        if allinfo.get('iurlmaxres'):
            self.bigthumbhd = f('iurlmaxres')
        return

    def __init__(self, video_url):
        infoUrl = 'https://www.youtube.com/get_video_info?video_id='
        m = re.search(r'\bv=([a-zA-Z0-9-_]{11})', video_url)
        if not m:
            m = re.search(r'\b([a-zA-Z0-9-_]{11})', video_url)
        if not m:
            error = "Need 11 character video id or the URL of the video. Got %s"
            raise RuntimeError(error % video_url)
        vidid = m.group(1)
        infoUrl += vidid + "&asv=3&el=detailpage&hl=en_US"
        opener = build_opener()
        ua = ("Mozilla/5.0 (compatible; MSIE 9.0; Windows NT 6.1; WOW64;"
              "Trident/5.0)")
        opener.addheaders = [('User-Agent', ua)]
        self.keywords = ""
        allinfo = parse_qs(decode_if_py3(opener.open(infoUrl).read()))
        if allinfo['status'][0] == "fail":
            reason = allinfo['reason'][0] or "Bad video argument"
            raise RuntimeError("Youtube says: %s" % reason)
        self._setmetadata(allinfo)
        streamMap = allinfo['url_encoded_fmt_stream_map'][0].split(',')
        smap = [parse_qs(sm) for sm in streamMap]
        js = None
        if not smap[0].get("sig", ""):  # vevo!
            watchurl = "https://www.youtube.com/watch?v=" + vidid
            watchinfo = opener.open(watchurl).read().decode("UTF-8")
            m = re.search(r';ytplayer.config = ({.*?});', watchinfo)
            try:
                myjson = json.loads(m.group(1))
            except:
                raise RuntimeError('Problem handling this video')
            args = myjson['args']
            streamMap = args['url_encoded_fmt_stream_map'].split(",")
            html5player = myjson['assets']['js']
            js = opener.open(html5player).read().decode("UTF-8")
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
