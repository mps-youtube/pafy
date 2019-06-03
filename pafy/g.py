import sys
if sys.version_info[:2] >= (3, 0):
    # pylint: disable=E0611,F0401,I0011
    from urllib.request import build_opener
else:
    from urllib2 import build_opener

from . import __version__

urls = {
    'gdata': "https://www.googleapis.com/youtube/v3/",
    'watchv': "http://www.youtube.com/watch?v=%s",
    'playlist': ('http://www.youtube.com/list_ajax?'
                 'style=json&action_get_list=1&list=%s'),
    'thumb': "http://i.ytimg.com/vi/%s/default.jpg",
    'bigthumb': "http://i.ytimg.com/vi/%s/mqdefault.jpg",
    'bigthumbhd': "http://i.ytimg.com/vi/%s/hqdefault.jpg",

    # For internal backend
    'vidinfo': ('https://www.youtube.com/get_video_info?video_id=%s&'
                'eurl=https://youtube.googleapis.com/v/%s&sts=%s'),
    'embed': "https://youtube.com/embed/%s"
}
api_key = "AIzaSyCIM4EzNqi1in22f4Z3Ru3iYvLaY8tc3bo"
user_agent = "pafy " + __version__
lifespan = 60 * 60 * 5  # 5 hours
opener = build_opener()
opener.addheaders = [('User-Agent', user_agent)]
cache = {}
def_ydl_opts = {'quiet': True, 'prefer_insecure': False, 'no_warnings': True}

# The following are specific to the internal backend
UEFSM = 'url_encoded_fmt_stream_map'
AF = 'adaptive_fmts'
jsplayer = r';ytplayer\.config\s*=\s*({.*?});'
itags = {
    '5': ('320x240', 'flv', "normal", ''),
    '17': ('176x144', '3gp', "normal", ''),
    '18': ('640x360', 'mp4', "normal", ''),
    '22': ('1280x720', 'mp4', "normal", ''),
    '34': ('640x360', 'flv', "normal", ''),
    '35': ('854x480', 'flv', "normal", ''),
    '36': ('320x240', '3gp', "normal", ''),
    '37': ('1920x1080', 'mp4', "normal", ''),
    '38': ('4096x3072', 'mp4', "normal", '4:3 hi-res'),
    '43': ('640x360', 'webm', "normal", ''),
    '44': ('854x480', 'webm', "normal", ''),
    '45': ('1280x720', 'webm', "normal", ''),
    '46': ('1920x1080', 'webm', "normal", ''),
    '82': ('640x360-3D', 'mp4', "normal", ''),
    '83': ('640x480-3D', 'mp4', 'normal', ''),
    '84': ('1280x720-3D', 'mp4', "normal", ''),
    '100': ('640x360-3D', 'webm', "normal", ''),
    '102': ('1280x720-3D', 'webm', "normal", ''),
    '133': ('426x240', 'm4v', 'video', ''),
    '134': ('640x360', 'm4v', 'video', ''),
    '135': ('854x480', 'm4v', 'video', ''),
    '136': ('1280x720', 'm4v', 'video', ''),
    '137': ('1920x1080', 'm4v', 'video', ''),
    '138': ('4096x3072', 'm4v', 'video', ''),
    '139': ('48k', 'm4a', 'audio', ''),
    '140': ('128k', 'm4a', 'audio', ''),
    '141': ('256k', 'm4a', 'audio', ''),
    '160': ('256x144', 'm4v', 'video', ''),
    '167': ('640x480', 'webm', 'video', ''),
    '168': ('854x480', 'webm', 'video', ''),
    '169': ('1280x720', 'webm', 'video', ''),
    '170': ('1920x1080', 'webm', 'video', ''),
    '171': ('128k', 'ogg', 'audio', ''),
    '172': ('192k', 'ogg', 'audio', ''),
    '218': ('854x480', 'webm', 'video', 'VP8'),
    '219': ('854x480', 'webm', 'video', 'VP8'),
    '242': ('360x240', 'webm', 'video', 'VP9'),
    '243': ('480x360', 'webm', 'video', 'VP9'),
    '244': ('640x480', 'webm', 'video', 'VP9 low'),
    '245': ('640x480', 'webm', 'video', 'VP9 med'),
    '246': ('640x480', 'webm', 'video', 'VP9 high'),
    '247': ('720x480', 'webm', 'video', 'VP9'),
    '248': ('1920x1080', 'webm', 'video', 'VP9'),
    '249': ('48k', 'opus', 'audio', 'Opus'),
    '250': ('56k', 'opus', 'audio', 'Opus'),
    '251': ('128k', 'opus', 'audio', 'Opus'),
    '256': ('192k', 'm4a', 'audio', '6-channel'),
    '258': ('320k', 'm4a', 'audio', '6-channel'),
    '264': ('2560x1440', 'm4v', 'video', ''),
    '266': ('3840x2160', 'm4v', 'video', 'AVC'),
    '271': ('1920x1280', 'webm', 'video', 'VP9'),
    '272': ('3414x1080', 'webm', 'video', 'VP9'),
    '278': ('256x144', 'webm', 'video', 'VP9'),
    '298': ('1280x720', 'm4v', 'video', '60fps'),
    '299': ('1920x1080', 'm4v', 'video', '60fps'),
    '302': ('1280x720', 'webm', 'video', 'VP9'),
    '303': ('1920x1080', 'webm', 'video', 'VP9'),
}
