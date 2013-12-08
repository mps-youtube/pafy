.. image:: http://badge.fury.io/py/Pafy.png
    :target: https://pypi.python.org/pypi/Pafy
.. image:: https://pypip.in/d/Pafy/badge.png
    :target: https://pypi.python.org/pypi/Pafy


Features
--------

- Retreive metadata such as viewcount, duration, rating, author, thumbnail, keywords
- Download video or audio at requested resolution / bitrate / format / filesize
- Command line tool (ytdl) for downloading directly from the command line
- Retrieve the URL to stream the video in a player such as vlc or mplayer
- Works with age-restricted videos and non-embeddable videos
- Small, standalone, single importable module file (pafy.py)
- Select highest quality stream for download or streaming
- Download audio only (no video) in ogg or m4a format
- Download video only (no audio) in m4v format
- Works with Python 2.7 and 3.x
- No dependencies


Documentation
-------------

Full documentation is available at http://pythonhosted.org/Pafy

Usage Examples
--------------

Here is how to use the module in your own python code.  For command line tool
(ytdl) instructions, see further below::

    >>> import pafy

create a video instance from a YouTube url::

    >>> url = "http://www.youtube.com/watch?v=cyMHZVT91Dw"
    >>> video = pafy.new(url)

get certain attributes::
    
    >>> video.title
    u'Rick Astley Sings Live - Never Gonna Give You Up - This Morning'


    >>> video.rating
    4.93608852755

    >>> video.length
    355

display video metadata::

    >>> print video

    Title: Rick Astley Sings Live - Never Gonna Give You Up - This Morning
    Author: Ryan915
    ID: cyMHZVT91Dw
    Duration: 00:05:55
    Rating: 4.93608852755
    Views: 672583
    Thumbnail: https://i1.ytimg.com/vi/cyMHZVT91Dw/default.jpg
    Keywords: Rick, Astley, Sings, Live, on, This, Morning, Never, Gonna, You...  

show regular formats for a video (video files with audio)::

    >>> streams = video.streams
    >>> for s in streams:
    >>>     print s.resolution, s.extension

    480x854 webm
    480x854 flv
    360x640 webm
    360x640 flv
    360x640 mp4
    240x400 flv
    320x240 3gp
    144x176 3gp


show all formats, file-sizes and their download url::

    >>> for s in streams:
    >>>     print s.resolution, s.extension, s.get_filesize(), s.url

    480x854 webm 56858674 http://r12--sn-aoh8kier.c.youtube.com/videoplayback?expire=1369...
    480x854 flv 53066081 http://r11---sn-aoh8kier.c.youtube.com/videoplayback?expire=1369...
    360x640 webm 34775366 http://r11---sn-aoh8kier.c.youtube.com/videoplayback?expire=1369...
    360x640 flv 32737100 http://r11---sn-aoh8kier.c.youtube.com/videoplayback?expire=1369...
    360x640 mp4 25919932 http://r11---sn-aoh8kier.c.youtube.com/videoplayback?expire=1369...
    240x400 flv 14341366 http://r11---sn-aoh8kier.c.youtube.com/videoplayback?expire=1369...
    320x240 3gp 11083585 http://r11---sn-aoh8kier.c.youtube.com/videoplayback?expire=1369...
    144x176 3gp 3891135 http://r11---sn-aoh8kier.c.youtube.com/videoplayback?expire=1369...


get best resolution regardless of file format::

    >>> best = video.getbest()
    >>> best.resolution, best.extension

    ('480x854', 'webm')


get best resolution for a particular file format:
(mp4, webm, flv or 3gp)::

    >>> best = video.getbest(preftype="mp4")
    >>> best.resolution, best.extension

    ('360x640', 'mp4')


get best resolution for a particular file format, or return
different format if it has the best resolution::

    >>> best = video.getbest(preftype="mp4", ftypestrict=False)
    >>> best.resolution, best.extension

    ('480x854', 'webm')


get url, for download or streaming in mplayer / vlc etc::
    
    >>> best.url

    'http://r12---sn-aig7kner.c.youtube.com/videoplayback?expire=1369...


Download video and show progress::

    >>> best.download(quiet=False)
    -Downloading 'Rick Astley Sings Live - Never Gonna Give You Up - This Morning.webm' [56,858,674 Bytes]

      56,858,674 Bytes [100.00%] received. Rate: [ 720 kbps].  ETA: [0 secs]    
    Done


Download video, use specific filepath::

    >>> myfilename = "/tmp/" + best.title + "." + best.extension
    >>> best.download(filepath=myfilename)


Get audio-only streams (m4a and/or ogg vorbis)
(use video.videostreams to get video-only streams)::

    >>> audiostreams = video.audiostreams
    >>> for a in audiostreams:
    >>>     print(a.quality, a.extension, a.get_filesize())

    ('48k', 'm4a', 2109164)
    ('128k', 'm4a', 5630839)
    ('256k', 'm4a', 11302824)


Download the 3rd audio stream from the above list::

    >>> audiostreams[2].download()

Get the best quality audio stream::

    >>> bestaudio = video.getbestaudio()
    >>> bestaudio.bitrate

    '256k'


Download the best quality audio file::

    >>> bestaudio.download()

show ALL formats for a video (video+audio, video-only and audio-only)::

    >>> allstreams = video.allstreams
    >>> for s in allstreams:
    >>>     print(s.quality, s.extension, s.mediatype)

    ('1280x720', 'mp4', 'a/v')
    ('640x360', 'webm', 'a/v')
    ('640x360', 'mp4', 'a/v')
    ('320x240', 'flv', 'a/v')
    ('320x240', '3gp', 'a/v')
    ('176x144', '3gp', 'a/v')
    ('1920x1080', 'm4v', 'video')
    ('1280x720', 'm4v', 'video')
    ('854x480', 'm4v', 'video')
    ('640x360', 'm4v', 'video')
    ('426x240', 'm4v', 'video')
    ('256x144', 'm4v', 'video')
    ('48k', 'm4a', 'audio')
    ('128k', 'm4a', 'audio')
    ('256k', 'm4a', 'audio')
    ('128k', 'ogg', 'audio')
    ('256k', 'ogg', 'audio')



Command Line Tool (ytdl) Usage
------------------------------


::

    usage: ytdl [-h] [-i] [-s]
                [-t {audio,video,normal,all} [{audio,video,normal,all} ...]]
                [-n N] [-b] [-a]
                url

    YouTube Download Tool

    positional arguments:
      url                   YouTube video URL to download

    optional arguments:
      -h, --help            show this help message and exit
      -i                    Display vid info
      -s                    Display available streams
      -t {audio,video,normal,all} [{audio,video,normal,all} ...]
                            Stream types to display
      -n N                  Specify stream to download by stream number (use -s to
                            list available streams)
      -b                    Download the best quality video (ignores -n)
      -a                    Download the best quality audio (ignores -n)


YTDL Examples
-------------

Download best available resolution (-b)::

    ytdl "http://www.youtube.com/watch?v=cyMHZVT91Dw" -b


Download best available audio stream (-a):
(note; the full url is not required, just the video id will suffice)::

    ytdl cyMHZVT91Dw -a


get video info (-i)::

    ytdl cyMHZVT91Dw -i

list available dowload streams::

    ytdl cyMHZVT91Dw
 
    Stream Type    Format Quality         Size            
    ------ ----    ------ -------         ----            
    1      normal  webm   [640x360]       33 MB           
    2      normal  mp4    [640x360]       24 MB           
    3      normal  flv    [320x240]       13 MB           
    4      normal  3gp    [320x240]       10 MB           
    5      normal  3gp    [176x144]        3 MB           
    6      audio   m4a    [48k]            2 MB           
    7      audio   m4a    [128k]           5 MB           
    8      audio   m4a    [256k]          10 MB     

 
Download mp4 640x360 (ie. stream number 2)::

    ytdl cyMHZVT91Dw -n2

Download m4a audio stream at 256k bitrate::

    ytdl cyMHZVT91Dw -n8


