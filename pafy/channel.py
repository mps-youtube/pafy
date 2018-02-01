import re
from .pafy import call_gdata
from .playlist import Playlist
from .backend_shared import pyver


def get_channel(channel_url, basic=False, gdata=False,
                size=False, callback=None):
    """Return a Channel object

    The returned Pafy and Playlist objects are initialised using the arguments
    to get_channel() in the manner documented for pafy.new()

    """

    return Channel.from_url(channel_url, basic, gdata, size, callback)


class Channel(object):
    def __init__(self, channel_url, basic, gdata, size, callback):

        self._channel_url = channel_url
        self._channel_id = None
        self._title = None
        self._description = None
        self._logo = None
        self._subscriberCount = None
        self._uploads = None
        self._basic = basic
        self._gdata = gdata
        self._size = size
        self._callback = callback
        self._playlists = None
        self._subscriptions = None
        self._have_basic = False

    @classmethod
    def from_dict(cls, ch, basic, gdata, size, callback):
        t = cls(ch['id'], basic, gdata, size, callback)
        t._channel_id = ch['id']
        t._title = ch['title']
        t._description = ch['description']
        t._logo = ch['logo']
        t._subscriberCount = ch['subscriberCount']
        t._uploads = ch['uploads']
        t._have_basic = True

        return t

    @classmethod
    def from_url(cls, url, basic, gdata, size, callback):
        t = cls(url, basic, gdata, size, callback)
        t._fetch_basic()
        return t

    @property
    def channel_id(self):
        if not self._have_basic:
            self._fetch_basic()
        return self._channel_id

    @property
    def title(self):
        if not self._have_basic:
            self._fetch_basic()
        return self._title

    @property
    def description(self):
        if not self._have_basic:
            self._fetch_basic()
        return self._description

    @property
    def logo(self):
        if not self._have_basic:
            self._fetch_basic()
        return self._logo

    @property
    def subscriberCount(self):
        if not self._have_basic:
            self._fetch_basic()
        return self._subscriberCount

    @property
    def uploads(self):
        if not self._uploads:
            self._fetch_basic()
        if type(self._uploads) != Playlist:
            self._uploads = Playlist.from_url(self._uploads, self._basic,
                                              self._gdata, self._size,
                                              self._callback)

        return self._uploads

    @property
    def playlists(self):
        if self._playlists is not None:
            for playlist in self._playlists:
                yield playlist
            return

        playlists = []

        query = {'part': 'snippet,contentDetails',
                 'maxResults': 50,
                 'channelId': self.channel_id}

        while True:
            playlistList = call_gdata('playlists', query)

            for pl in playlistList['items']:
                try:
                    thumbnail = pl['snippet']['thumbnails']['standard']['url']
                except KeyError:
                    thumbnail = None
                pl_data = dict(
                    id=pl['id'],
                    title=pl['snippet']['title'],
                    author=pl['snippet']['channelTitle'],
                    description=pl['snippet']['description'],
                    thumbnail=thumbnail,
                    len=pl['contentDetails']['itemCount']
                )

                pl_obj = Playlist.from_dict(pl_data, self._basic, self._gdata,
                                            self._size, self._callback)
                playlists.append(pl_obj)
                if self._callback:
                    self._callback("Added playlist: %s" % pl_data['title'])
                yield pl_obj

            if not playlistList.get('nextPageToken'):
                break
            query['pageToken'] = playlistList['nextPageToken']

        self._playlists = playlists

    @property
    def subscriptions(self):
        if self._subscriptions is not None:
            for sub in self._subscriptions:
                yield sub
            return

        subscriptions = []
        query = {'part': 'snippet',
                 'maxResults': 50,
                 'channelId': self.channel_id}

        while True:
            subs_data = call_gdata('subscriptions', query)
            sub_ids = []

            for sub in subs_data['items']:
                sub_ids.append(sub['snippet']['resourceId']['channelId'])

            query2 = {'part': 'snippet, contentDetails, statistics',
                      'id': ','.join(sub_ids),
                      'maxResults': 50}

            data = call_gdata('channels', query2)

            for ch in data['items']:
                channel_data = dict(
                    id=ch['id'],
                    title=ch['snippet']['title'],
                    description=ch['snippet']['description'],
                    logo=ch['snippet']['thumbnails']['default']['url'],
                    subscriberCount=ch['statistics']['subscriberCount'],
                    uploads=ch['contentDetails']['relatedPlaylists']['uploads']
                )
                sub_obj = Channel.from_dict(channel_data, self._basic,
                                            self._gdata, self._size,
                                            self._callback)
                subscriptions.append(sub_obj)
                yield sub_obj

            if not subs_data.get('nextPageToken'):
                break
            query['pageToken'] = subs_data['nextPageToken']

        self._subscriptions = subscriptions

    def __repr__(self):
        if not self._have_basic:
            self._fetch_basic()

        info = [("Type", "Channel"),
                ("Title", self.title),
                ("Description", self.description),
                ("SubscriberCount", self.subscriberCount)]

        nfo = "\n".join(["%s: %s" % i for i in info])

        return nfo.encode("utf8", "replace") if pyver == 2 else nfo

    def _fetch_basic(self):
        query = None
        chanR = re.compile('.+channel\/([^\/]+)$')
        userR = re.compile('.+user\/([^\/]+)$')
        channel_id = None
        channel_url = self._channel_url
        if chanR.match(channel_url):
            channel_id = chanR.search(channel_url).group(1)
        elif userR.match(channel_url):
            username = userR.search(channel_url).group(1)
            query = {'part': 'snippet, contentDetails, statistics',
                     'forUsername': username}
        elif len(channel_url) == 24 and channel_url[:2] == 'UC':
            channel_id = channel_url
        else:
            username = channel_url
            query = {'part': 'snippet, contentDetails, statistics',
                     'forUsername': username}

        if query is None:
            query = {'part': 'snippet, contentDetails, statistics',
                     'id': channel_id}
        allinfo = call_gdata('channels', query)

        try:
            ch = allinfo['items'][0]
        except IndexError:
            err = "Unrecognized channel id, url or name : %s"
            raise ValueError(err % channel_url)

        self._channel_id = ch['id']
        self._title = ch['snippet']['title']
        self._description = ch['snippet']['description']
        self._logo = ch['snippet']['thumbnails']['default']['url']
        self._subscriberCount = ch['statistics']['subscriberCount']
        self._uploads = ch['contentDetails']['relatedPlaylists']['uploads']
        self._have_basic = True
