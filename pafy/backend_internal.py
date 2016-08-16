import os
import hashlib
import tempfile
import json
import re
import sys
import time
import logging
from xml.etree import ElementTree

if sys.version_info[:2] >= (3, 0):
    # pylint: disable=E0611,F0401,I0011
    from urllib.parse import parse_qs, unquote_plus
    uni, pyver = str, 3

else:
    from urllib import unquote_plus
    from urlparse import parse_qs
    uni, pyver = unicode, 2

early_py_version = sys.version_info[:2] < (2, 7)

from . import g
from .pafy import fetch_decode, dbg, get_categoryname
from .backend_shared import BasePafy, BaseStream
from .jsinterp import JSInterpreter


funcmap = {}


class InternPafy(BasePafy):
    def __init__(self, *args, **kwargs):
        self.sm = []
        self.asm = []
        self.dash = []
        self.js_url = None  # if js_url is set then has new stream map
        self._dashurl = None
        self.age_ver = False
        self._formats = None
        self.ciphertag = None  # used by Stream class in url property def
        super(InternPafy, self).__init__(*args, **kwargs)


    def _fetch_basic(self):
        """ Fetch basic data and streams. """
        if self._have_basic:
            return

        allinfo = get_video_info(self.videoid, self.callback)

        self.callback("Fetched video info")

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

        sm_ciphertag = "s" in self.sm[0]

        if self.ciphertag != sm_ciphertag:
            dbg("ciphertag mismatch")
            self.ciphertag = not self.ciphertag

        watch_url = g.urls['watchv'] % self.videoid
        self.callback("Fetching watch page")
        watchinfo = fetch_decode(watch_url)  # unicode
        dbg("Fetched watch page")
        self.callback("Fetched watch page")
        self.age_ver = re.search(r'player-age-gate-content">', watchinfo) is not None

        if self.ciphertag:
            dbg("Encrypted signature detected.")

            if not self.age_ver:
                smaps, js_url, mainfunc = get_js_sm(watchinfo, self.callback)
                funcmap[js_url] = mainfunc
                self.sm, self.asm = smaps
                self.js_url = js_url
                dashsig = re.search(r"/s/([\w\.]+)", self._dashurl).group(1)
                dbg("decrypting dash sig")
                goodsig = _decodesig(dashsig, js_url, self.callback)
                self._dashurl = re.sub(r"/s/[\w\.]+",
                                       "/signature/%s" % goodsig, self._dashurl)

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


    def _fetch_gdata(self):
        """ Extract gdata values, fetch gdata if necessary. """
        if self._have_gdata:
            return

        item = self._get_video_gdata(self.videoid)['items'][0]
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
            self._fetch_basic()

        streams = [InternStream(z, self) for z in self.sm]
        streams = [x for x in streams if x.itag in g.itags]
        adpt_streams = [InternStream(z, self) for z in self.asm]
        adpt_streams = [x for x in adpt_streams if x.itag in g.itags]
        dash_streams = [InternStream(z, self) for z in self.dash]
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


class InternStream(BaseStream):
    def __init__(self, sm, parent):
        super(InternStream, self).__init__(parent)

        self._itag = sm['itag']
        # is_dash = "width" in sm and "height" in sm
        is_dash = "dash" in sm

        if self._itag not in g.itags:
            logging.warning("Unknown itag: %s", self._itag)
            return

        self._mediatype = g.itags[self.itag][2]
        self._threed = 'stereo3d' in sm and sm['stereo3d'] == '1'

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

            self._fsize = int(sm['size'] or 0)
            # self._bitrate = sm['bitrate']
            # self._rawbitrate = uni(int(self._bitrate) // 1024) + "k"

        else:  # not dash
            self._resolution = g.itags[self.itag][0]
            self._dimensions = tuple(self.resolution.split("-")[0].split("x"))
            self._dimensions = tuple([int(x) if x.isdigit() else x for x in
                                      self._dimensions])
            self._quality = self.resolution

        self._extension = g.itags[self.itag][1]
        self._title = parent.title
        self.encrypted = 's' in sm
        self._parent = parent
        self._filename = self.generate_filename()
        self._notes = g.itags[self.itag][3]
        self._rawurl = sm['url']
        self._sig = sm['s'] if self.encrypted else sm.get("sig")
        self._active = False

        if self.mediatype == "audio" and not is_dash:
            self._dimensions = (0, 0)
            self._bitrate = self.resolution
            self._quality = self.bitrate
            self._resolution = "0x0"
            self._rawbitrate = int(sm["bitrate"])

    @property
    def url(self):
        """ Return the url, decrypt if required. """
        if not self._url:

            if self._parent.age_ver:

                if self._sig:
                    s = self._sig
                    self._sig = s[2:63] + s[82] + s[64:82] + s[63]

            elif self.encrypted:
                self._sig = _decodesig(self._sig, self._parent.js_url,
                        self._parent.callback)

            self._url = _make_url(self._rawurl, self._sig)

        return self._url


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


def get_video_info(video_id, callback, newurl=None):
    """ Return info for video_id.  Returns dict. """
    # TODO: see if there is a way to avoid retrieving the embed page
    #       just for this, or to use it for more. This was coppied from
    #       youtube-dl.
    embed_webpage = fetch_decode(g.urls['embed'])
    sts = re.search(r'sts"\s*:\s*(\d+)', embed_webpage).group(1)

    url = g.urls['vidinfo'] % (video_id, video_id, sts)
    url = newurl if newurl else url
    info = fetch_decode(url)  # bytes
    info = parseqs(info)  # unicode dict
    dbg("Fetched video info%s", " (age ver)" if newurl else "")

    if info['status'][0] == "fail":
        reason = info['reason'][0] or "Bad video argument"
        raise IOError("Youtube says: %s [%s]" % (reason, video_id))

    return info


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
        size = baseurl.get("%scontentLength" % ytns)
        bitrate = x.get("bandwidth")
        itag = uni(x.get("id"))
        width = uni(x.get("width"))
        height = uni(x.get("height"))
        dashmap.append(dict(bitrate=bitrate,
                            dash=True,
                            itag=itag,
                            width=width,
                            height=height,
                            url=url,
                            size=size))
    return dashmap


def _get_mainfunc_from_js(js):
    """ Return main signature decryption function from javascript as dict. """
    dbg("Scanning js for main function.")
    m = re.search(r'\.sig\|\|([a-zA-Z0-9$]+)\(', js)
    funcname = m.group(1)
    dbg("Found main function: %s", funcname)
    jsi = JSInterpreter(js)
    return jsi.extract_function(funcname)


def _decodesig(sig, js_url, callback):
    """  Return decrypted sig given an encrypted sig and js_url key. """
    # lookup main function in funcmap dict
    mainfunction = funcmap[js_url]

    # fill in function argument with signature
    callback("Decrypting signature")
    solved = mainfunction([sig])
    dbg("Decrypted sig = %s...", solved[:30])
    callback("Decrypted signature")
    return solved


def fetch_cached(url, callback, encoding=None, dbg_ref="", file_prefix=""):
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
        callback("Fetched %s" % dbg_ref)

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


def get_js_sm(watchinfo, callback):
    """ Fetch watchinfo page and extract stream map and js funcs if not known.

    This function is needed by videos with encrypted signatures.
    If the js url referred to in the watchv page is not a key in funcmap,
    the javascript is fetched and functions extracted.

    Returns streammap (list of dicts), js url (str)  and funcs (dict)

    """
    m = re.search(g.jsplayer, watchinfo)
    myjson = json.loads(m.group(1))
    stream_info = myjson['args']
    sm = _extract_smap(g.UEFSM, stream_info, False)
    asm = _extract_smap(g.AF, stream_info, False)
    js_url = myjson['assets']['js']
    js_url = "https:" + js_url if js_url.startswith("//") else js_url
    mainfunc = funcmap.get(js_url)

    if not mainfunc:
        dbg("Fetching javascript")
        callback("Fetching javascript")
        javascript = fetch_cached(js_url, callback, encoding="utf8",
                                  dbg_ref="javascript", file_prefix="js-")
        mainfunc = _get_mainfunc_from_js(javascript)

    elif mainfunc:
        dbg("Using functions in memory extracted from %s", js_url)
        dbg("Mem contains %s js func sets", len(funcmap))

    return (sm, asm), js_url, mainfunc


def _make_url(raw, sig, quick=True):
    """ Return usable url. Set quick=False to disable ratebypass override. """
    if quick and "ratebypass=" not in raw:
        raw += "&ratebypass=yes"

    if "signature=" not in raw:

        if sig is None:
            raise IOError("Error retrieving url")

        raw += "&signature=" + sig

    return raw
