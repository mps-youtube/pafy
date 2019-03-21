import sys
import re
import json
import itertools

from . import g
from .pafy import new, get_categoryname, call_gdata, fetch_decode


if sys.version_info[:2] >= (3, 0):
    # pylint: disable=E0611,F0401,I0011
    from urllib.parse import parse_qs, urlparse
    pyver = 3
else:
    from urlparse import parse_qs, urlparse
    pyver = 2


def extract_playlist_id(playlist_url):
    # Normal playlists start with PL, Mixes start with RD + first video ID,
    # Liked videos start with LL, Uploads start with UU,
    # Favorites lists start with FL
    # Album playlists start with OL
    idregx = re.compile(r'((?:RD|PL|LL|UU|FL|OL)[-_0-9a-zA-Z]+)$')

    playlist_id = None
    if idregx.match(playlist_url):
        playlist_id = playlist_url  # ID of video

    if '://' not in playlist_url:
        playlist_url = '//' + playlist_url
    parsedurl = urlparse(playlist_url)
    if parsedurl.netloc in ('youtube.com', 'www.youtube.com'):
        query = parse_qs(parsedurl.query)
        if 'list' in query and idregx.match(query['list'][0]):
            playlist_id = query['list'][0]

    return playlist_id


def get_playlist(playlist_url, basic=False, gdata=False,
                 size=False, callback=None):
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
                           size=size,
                           callback=callback)

        except IOError as e:
            if callback:
                callback("%s: %s" % (v['title'], e.message))
            continue

        pafy_obj.populate_from_playlist(vid_data)
        playlist['items'].append(dict(pafy=pafy_obj,
                                      playlist_meta=vid_data))
        if callback:
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
    def __init__(self, playlist_url, basic, gdata, size, callback):
        playlist_id = extract_playlist_id(playlist_url)

        if not playlist_id:
            err = "Unrecognized playlist url: %s"
            raise ValueError(err % playlist_url)

        self.plid = playlist_id
        self._title = None
        self._author = None
        self._description = None
        self._len = None
        self._thumbnail = None
        self._basic = basic
        self._gdata = gdata
        self._size = size
        self._callback = callback
        self._pageToken = None
        self._have_basic = False
        self._items = []

    @classmethod
    def from_dict(cls, pl, basic, gdata, size, callback):
        t = cls(pl['id'],  basic, gdata, size, callback)
        t._title = pl['title']
        t._author = pl['author']
        t._description = pl['description']
        t._len = pl['len']
        t._thumbnail = pl['thumbnail']
        t._have_basic = True
        return t

    @classmethod
    def from_url(cls, url, basic, gdata, size, callback):
        t = cls(url,  basic, gdata, size, callback)
        t._fetch_basic()
        return t

    @property
    def title(self):
        if not self._have_basic:
            self._fetch_basic()

        return self._title

    @property
    def author(self):
        if not self._have_basic:
            self._fetch_basic()

        return self._author

    @property
    def description(self):
        if not self._have_basic:
            self._fetch_basic()

        return self._description

    @property
    def thumbnail(self):
        if not self._have_basic:
            self._fetch_basic()

        return self._thumbnail

    def __len__(self):
        if not self._have_basic:
            self._fetch_basic()

        return self._len

    def __iter__(self):
        for i in self._items:
            yield i

        # playlist items specific metadata
        query = {'part': 'snippet',
                 'maxResults': 50,
                 'playlistId': self.plid}

        # Use -1 to represent having reached the last page
        while self._pageToken != -1:
            if self._pageToken:
                query['pageToken'] = self._pageToken
            playlistitems = call_gdata('playlistItems', query)

            query2 = {'part': 'contentDetails,snippet,statistics',
                      'maxResults': 50,
                      'id': ','.join(i['snippet']['resourceId']['videoId']
                                     for i in playlistitems['items'])}
            wdata = call_gdata('videos', query2)

            index = len(self._items)
            for v in wdata['items']:
                vid_data = dict_for_playlist(v)

                try:
                    pafy_obj = new(v['id'],
                                   basic=False, gdata=False,
                                   size=self._size, callback=self._callback)

                except IOError as e:
                    if self._callback:
                        self._callback("%s: %s" % (v['title'], e.message))
                    continue

                pafy_obj.populate_from_playlist(vid_data)
                self._items.append(pafy_obj)
                if self._callback:
                    self._callback("Added video: %s" % vid_data['title'])

            self._pageToken = playlistitems.get('nextPageToken', -1)
            if self._pageToken == -1:
                self._len = len(self._items)

            # Do not yield until self._items and self._pageToken are set
            for i in self._items[index:]:
                if self._basic:
                    i._fetch_basic()
                if self._gdata:
                    i._fetch_gdata()

                yield i

    def __getitem__(self, index):
        if index < len(self._items):
            return self._items[index]

        try:
            return next(itertools.islice(self, index, None))
        except StopIteration:
            raise IndexError('index out of range')

    def __repr__(self):
        if not self._have_basic:
            self._fetch_basic()

        info = [("Type", "Playlist"),
                ("Title", self._title),
                ("Author", self._author),
                ("Description", self._description),
                ("Length", self.__len__())]

        nfo = "\n".join(["%s: %s" % i for i in info])

        return nfo.encode("utf8", "replace") if pyver == 2 else nfo

    def _fetch_basic(self):
        query = {'part': 'snippet, contentDetails',
                 'id': self.plid}
        allinfo = call_gdata('playlists', query)

        pl = allinfo['items'][0]

        self._title = pl['snippet']['title']
        self._author = pl['snippet']['channelTitle']
        self._description = pl['snippet']['description']
        self._len = pl['contentDetails']['itemCount']
        try:
            self._thumbnail = pl['snippet']['thumbnails']['standard']['url']
        except KeyError:
            self._thumbnail = None
        self._have_basic = True


def get_playlist2(playlist_url, basic=False, gdata=False,
                  size=False, callback=None):
    """ Return a Playlist object from a YouTube Playlist.

    The returned Pafy objects are initialised using the arguments to
    get_playlist() in the manner documented for pafy.new()

    """

    return Playlist.from_url(playlist_url, basic, gdata, size, callback)


def dict_for_playlist(v):
    """Returns a dict which can be used to initialise Pafy Object for playlist

    """

    stats = v.get('statistics', {})
    vid_data = dict(
        title=v['snippet']['title'],
        author=v['snippet']['channelTitle'],
        thumbnail=v['snippet'].get('thumbnails', {})
                              .get('default', {}).get('url'),
        description=v['snippet']['description'],
        length_seconds=parseISO8591(
                       v['contentDetails']['duration']),
        category=get_categoryname(v['snippet']['categoryId']),
        views=stats.get('viewCount', 0),
        likes=stats.get('likeCount', 0),
        dislikes=stats.get('dislikeCount', 0),
        comments=stats.get('commentCount', 0),
    )

    return vid_data
