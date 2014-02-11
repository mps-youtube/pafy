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

list available streams for a video::

    >>> streams = video.streams
    >>> for s in streams:
    >>>     print(s)

    normal:webm@640x360
    normal:mp4@640x360
    normal:flv@320x240
    normal:3gp@320x240
    normal:3gp@176x144


show all formats, file-sizes and their download url::

    >>> for s in streams:
    >>>     print s.resolution, s.extension, s.get_filesize(), s.url

    ('640x360', 'webm', 34775366, 'http://r20---sn-aiglln7e.googlevideo.com/v..
    ('640x360', 'mp4', 25027697, 'http://r20---sn-aiglln7e.googlevideo.com/v..
    ('320x240', 'flv', 15363436, 'http://r20---sn-aiglln7e.googlevideo.com/v..
    ('320x240', '3gp', 10097332, 'http://r20---sn-aiglln7e.googlevideo.com/v..
    ('176x144', '3gp', 3659867, 'http://r20---sn-aiglln7e.googlevideo.com/v..    


get best resolution regardless of file format::

    >>> best = video.getbest()
    >>> best.resolution, best.extension

    ('480x854', 'webm')


get best resolution for a particular file format:
(mp4, webm, flv or 3gp)::

    >>> best = video.getbest(preftype="mp4")
    >>> best.resolution, best.extension

    ('360x640', 'mp4')


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


Get audio-only streams (m4a and/or ogg vorbis)::

    >>> audiostreams = video.audiostreams
    >>> for a in audiostreams:
    >>>     print(a.bitrate, a.extension, a.get_filesize())

    ('48k', 'm4a', 2109164)
    ('128k', 'm4a', 5630839)


Download the 2nd audio stream from the above list::

    >>> audiostreams[1].download()

Get the best quality audio stream::

    >>> bestaudio = video.getbestaudio()
    >>> bestaudio.bitrate

    '256k'


Download the best quality audio file::

    >>> bestaudio.download()

show ALL formats for a video (video+audio, video-only and audio-only)::

    >>> allstreams = video.allstreams
    >>> for s in allstreams:
    >>>     print(s.mediatype, s.extension, s.quality)

    ('normal', 'webm', '640x360')
    ('normal', 'mp4', '640x360')
    ('normal', 'flv', '320x240')
    ('normal', '3gp', '320x240')
    ('normal', '3gp', '176x144')
    ('video', 'm4v', '854x480')
    ('video', 'm4v', '640x360')
    ('video', 'm4v', '426x240')
    ('video', 'm4v', '256x144')
    ('audio', 'm4a', '48k')
    ('audio', 'm4a', '128k')


Installation
------------

Pafy can be installed using `pip <http://www.pip-installer.org>`_::

    sudo pip install pafy

or use a `virtualenv <http://virtualenv.org>`_ if you don't want to install it system-wide::

    virtualenv venv
    source venv/bin/activate
    pip install pafy

Alternatively you can just grab the pafy.py file and import it in your python
code::

    wget https://raw.github.com/np1/pafy/master/pafy.py


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


ytdl Examples
-------------

Download best available resolution (-b)::

    ytdl -b "http://www.youtube.com/watch?v=cyMHZVT91Dw"


Download best available audio stream (-a):
(note; the full url is not required, just the video id will suffice)::

    ytdl -a cyMHZVT91Dw


get video info (-i)::

    ytdl -i cyMHZVT91Dw

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

    ytdl -n2 cyMHZVT91Dw

Download m4a audio stream at 256k bitrate::

    ytdl -n8 cyMHZVT91Dw


