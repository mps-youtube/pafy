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
    chanR = re.compile('.+channel\/([^\/]+)$')
    userR = re.compile('.+user\/([^\/]+)$')
    channel_id = None
    if chanR.match(channel_url):
        channel_id = chanR.search(channel_url).group(1)
    elif userR.match(channel_url):
        username = userR.search(channel_url).group(1)
        query = {'part': 'id',
                 'forUsername': username}
        allinfo = call_gdata('channels', query)
        if allinfo['items'] != []:
            channel_id = allinfo['items'][0]['id']
    return channel_id

def get_channel_videos(channel_url, basic=False, gdata=False,
                       size=False, callback=lambda x: None):
    if not channel_url:
        err = "Channel does not exist: %s"
        raise ValueError(err % channel_url)

    channel_id = extract_channel(channel_url)

    query1 = {'part':'id, snippet',
              'channelId':channel_id, 'order':'date',
              'maxResults':50}
    items = []
    while True:
        video_ids = []
        resp = call_gdata('search', query1)
        for i in resp['items']:
            if i['id']['kind'] == "youtube#video":
                video_ids.append(i['id']['videoId'])
        query2 = {'part':'contentDetails,snippet,statistics',
                  'id':','.join(video_ids)}
        vid_resp = call_gdata('videos', query2)
        for v, vextra in zip(resp['items'], vid_resp['items']):
            stats = vextra.get('statistics', {})
            vid_data = dict(
                title=vextra['snippet']['title'],
                author=vextra['snippet']['channelTitle'],
                thumbnail=vextra['snippet'].get('thumbnails', {}).get('default', {}).get('url'),
                description=vextra['snippet']['description'],
                length_seconds=parseISO8591(
                    vextra['contentDetails']['duration']),
                category=get_categoryname(vextra['snippet']['categoryId']),
                views=stats.get('viewCount', 0),
                likes=stats.get('likeCount', 0),
                dislikes=stats.get('dislikeCount', 0),
                comments=stats.get('commentCount', 0),
            )

            try:
                if v['id']['kind'] == "youtube#video":
                    pafy_obj = new(v['id']['videoId'],
                            basic=basic, gdata=gdata,
                            size=size, callback=callback)
            except IOError as e:
                callback("%s: %s" % (vextra['title'], e.message))
                continue

            pafy_obj.populate_from_playlist(vid_data)
            items.append(pafy_obj)
            callback("Added video: %s" % vid_data['title'])
#           yield pafy_obj
        try:
            next_page_token = resp['nextPageToken']
            query1['pageToken'] = next_page_token
        except:
            break
    return items

def get_channel_info(self):
    pass

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

class Channel:
    def __init__(self, channel_url, gdata):
        pass