import re
from . import g
from .pafy import new, get_categoryname, call_gdata, fetch_decode

def extract_channel(channel_url):
    # this recognizes only channel urls not sub urls like
    # https://www.youtube.com/user/foo/about
    # could be expanded easily if necessary
    # 2 regex are used since the channel id can be extracted out of the url for channels
    # but user "channel" need to be extracted
    # chanR=re.compile('(?:user|channel)\/([^\/]+)$')
    chanR=re.compile('.+channel\/([^\/]+)$')
    userR=re.compile('.+user\/([^\/]+)$')
    channel_id=None
    if chanR.match(channel_url):
        channel_id=chanR.search(channel_url).group(1)
    elif userR.match(channel_url):
        username=userR.search(channel_url).group(1)
        query = {'part': 'id',
                'forUsername': username}
        allinfo = call_gdata('channels', query)
        if allinfo['items']!=[]:
            channel_id=allinfo['items'][0]['id']
    return channel_id

def get_channel(channel_url, basic=False, gdata=False,
                 size=False, callback=lambda x: None):
    if not channel_url:
        err = "Channel does not exist: %s"
        raise ValueError(err % channel_url)

    channel_id=extract_channel(channel_url)

    video_links = []
    query = {'part':'snippet,id',
            'channelId':channel_id, 'order':'date','maxResults':25}
    while True:
        resp = call_gdata('search', query)

        for i in resp['items']:
            if i['id']['kind'] == "youtube#video":
                video_links.append(i['id']['videoId'])

        try:
            next_page_token = resp['nextPageToken']
            query['pageToken']=next_page_token
        except:
            break
    return video_links

class Channel:
    def __init__(self, channel_url, gdata):
        pass
