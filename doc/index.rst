Pafy Documentation
******************
.. module:: Pafy

This is the documentation for pafy - a Python library to download YouTube content and retrieve metadata

A quick start intro with usage examples is available in the `README <http://github.com/mps-youtube/pafy/blob/develop/README.rst>`_

Development / Source code / Bug reporting: `github.com/mps-youtube/pafy <https://github.com/mps-youtube/pafy/>`_

API Keys
========

Specifying an API key is optional, as pafy includes one.  However, it is prefered that software calling pafy provides it's own API key, and the default may be removed in the future.

`Information from Google about obtaining an API key <https://developers.google.com/youtube/registering_an_application>`_

.. function:: pafy.set_api_key(key)

    "Sets the API key for pafy to use."

    :param key: API key to use


Pafy Objects and Stream Objects
===============================

Pafy objects relate to videos hosted on YouTube.  They hold metadata such as
*title*, *viewcount*, *author* and *video ID*

Stream objects relate to individual streams of a YouTube video. They hold
stream-specific data such as *resolution*, *bitrate* and *url*.  Each Pafy
object contains multiple stream objects.


Pafy Objects
============

Create a Pafy object using the :func:`pafy.new` function, giving a YouTube video URL as the argument.


.. function:: pafy.new(video_url[, basic=True][, gdata=False][, signature=True][, size=False][, callback=None])


    Creates a new Pafy object.  All optional arguments (apart from callback) are used to specify  which data items are fetched on initialisation.  

    :param url: The YouTube url or 11 character video id of the video
    :type url: str
    :param basic: fetch basic metadata and streams
    :type basic: bool
    :param gdata: fetch gdata info (upload date, description, category, username, likes, dislikes)
    :type gdata: bool
    :param signature: Note: The signature argument now has no effect and will be removed in a future version
    :type signature: bool
    :param size: fetch the size of each stream (slow)(decrypts urls if needed) 
    :type size: bool
    :param callback: a callback function to receive status strings
    :type callback: function
    :rtype: :class:`pafy.Pafy`

If any of **basic**, **gdata** or **size** are *False*, those data items will be fetched only when first called for.

The defaults are recommended for most cases. If you wish to create many video objects at once, you may want to set all to *False*, eg::

    vid = pafy.new(basic=False)

This will be quick because no http requests will be made on initialisation.

Setting **size** to *True* will override the **basic** argument and force basic data to be fetched too (basic data is required to obtain Stream objects)

Example::

    import pafy
    myvid = pafy.new("http://www.youtube.com/watch?v=dQw4w9WgXc")

Pafy Attributes
---------------

Once you have created a Pafy object using :func:`pafy.new`, several data
attributes are available

.. attribute:: Pafy.author

    The author of the video (*str*)

.. attribute:: Pafy.bigthumb (*str*)

    The url of the video's display image (not always available)

.. attribute:: Pafy.bigthumbhd

    The url of the video's larger display image (not always available) (*str*)

.. attribute:: Pafy.category

    The category of the video (*str*)

.. attribute:: Pafy.description

    The video description text (*str*)

.. attribute:: Pafy.dislikes

    The number of dislikes received for the video (*int*)

.. attribute:: Pafy.duration

    The duration of the stream (*string formatted as HH:MM:SS*)

.. attribute:: Pafy.keywords

    A list of the video's keywords (not always available) (*[str]*)

.. attribute:: Pafy.length

    The duration of the streams in seconds (*int*)

.. attribute:: Pafy.likes

    The number of likes received for the video (*int*)

.. attribute:: Pafy.published

    The upload date of the video (e.g., 2012-10-02 17:17:24) (*str*)

.. attribute:: Pafy.mix

    The mix playlist provided by youtube for this video (*dict*)

.. attribute:: Pafy.rating

    The rating of the video (0-5), (*float*)

.. attribute:: Pafy.thumb

    The url of the video's thumbnail image (*str*)

.. attribute:: Pafy.title

    The title of the video (*str*)

.. attribute:: Pafy.username

    The username of the uploader (*str*)

.. attribute:: Pafy.videoid

    The 11-character video id (*str*)

.. attribute:: Pafy.viewcount

    The viewcount of the video (*int*)

An example of accessing this video metadata is shown below::

    import pafy
    v = pafy.new("dQw4w9WgXcQ")
    print(v.title)
    print(v.duration)
    print(v.rating)
    print(v.author)
    print(v.length)
    print(v.keywords)
    print(v.thumb)
    print(v.videoid)
    print(v.viewcount)

Which will result in this output::

    Rick Astley - Never Gonna Give You Up
    00:03:33
    4.75177729422
    RickAstleyVEVO
    213
    ['Rick', 'Astley', 'Sony', 'BMG', 'Music', 'UK', 'Pop']
    https://i1.ytimg.com/vi/dQw4w9WgXcQ/default.jpg
    dQw4w9WgXcQ
    69788014

Pafy Methods
------------

The :func:`Pafy.getbest`, :func:`Pafy.getbestaudio` and :func:`Pafy.getbestvideo` methods are a quick way to access the highest quality streams for a particular video without needing to query the stream lists.

.. function:: Pafy.getbest([preftype="any"][, ftypestrict=True])

    Selects the stream with the highest resolution.  This will return a
    "normal" stream (ie. one with video and audio)

    :param preftype: Preferred type, set to *mp4*, *webm*, *flv*, *3gp* or *any*
    :type preftype: str
    :param ftypestrict: Set to *False* to return a type other than that specified in preftype if it has a higher resolution
    :type ftypestrict: boolean
    :rtype: :class:`pafy.Stream`


.. function:: Pafy.getbestaudio([preftype="any"][, ftypestrict=True])

    Selects the audio stream with the highest bitrate.

    :param preftype: Preferred type, set to *ogg* or *m4a* or *any*
    :type preftype: str
    :param ftypestrict: Set to *False* to return a type other than that specified in preftype if that has the highest bitrate
    :type ftypestrict: boolean
    :rtype: :class:`pafy.Stream`


.. function:: Pafy.getbestvideo([preftype="any"][, ftypestrict=True])

    Selects the video-only stream with the highest resolution.  This will return a
    "video" stream (ie. one with no audio)

    :param preftype: Preferred type, set to *m4v*, *webm* or *any*
    :type preftype: str
    :param ftypestrict: Set to *False* to return a type other than that specified in preftype if it has a higher resolution
    :type ftypestrict: boolean
    :rtype: :class:`pafy.Stream`


Stream Lists
------------

A Pafy object provides multiple stream lists.  These are:

.. attribute:: Pafy.streams

    A list of regular streams (streams containing both audio and video)

.. attribute:: Pafy.audiostreams

    A list of audio-only streams; aac streams (.m4a) and ogg vorbis streams (.ogg) if available

.. attribute:: Pafy.videostreams

    A list of video-only streams (Note: these streams have no audio data)

.. attribute:: Pafy.oggstreams

    A list of ogg vorbis encoded audio streams (Note: may be empty for some videos)

.. attribute:: Pafy.m4astreams

    A list of aac encoded audio streams

.. attribute:: Pafy.allstreams

    A list of all available streams


An example of accessing stream lists::

    >>> import pafy
    >>> v = pafy.new("cyMHZVT91Dw")
    >>> v.audiostreams
    [audio:m4a@48k, audio:m4a@128k, audio:m4a@256k]
    >>> v.streams
    [normal:webm@640x360, normal:mp4@640x360, normal:flv@320x240, normal:3gp@320x240, normal:3gp@176x144]
    >>> v.allstreams
    [normal:webm@640x360, normal:mp4@640x360, normal:flv@320x240, normal:3gp@320x240, normal:3gp@176x144, video:m4v@854x480, video:m4v@640x360, video:m4v@426x240, video:m4v@256x144, audio:m4a@48k, audio:m4a@128k, audio:m4a@256k]
    

Stream Objects
==============

.. class:: pafy.Stream

After you have created a :class:`Pafy` object using :func:`new`, you
can then access the streams using one of the `Stream Lists`_, or by calling
:func:`Pafy.getbest` or :func:`Pafy.getbestaudio` on the object.


Stream Attributes
-----------------

    A Stream object can be used to access the following attributes


.. attribute:: Stream.url

    The direct access URL of the stream.  This can be used to stream the media
    in mplayer or vlc, or for downloading with wget or curl.  To download
    directly, use the :func:`Stream.download` method.

.. attribute:: Stream.url_https

    The direct access HTTPS URL of the stream.
    
.. attribute:: Stream.bitrate

    The bitrate of the stream - if it is an audio stream, otherwise None,
    This is a string of the form *"192k"*. 

.. attribute:: Stream.dimensions

    A 2-tuple (x, y) representing the resolution of a video stream.

.. attribute:: Stream.extension

    The format of the stream, will be one of: ``'ogg'``, ``'m4a'``, ``'mp4'``,
    ``'flv'``, ``'webm'``, ``'3gp'``

.. attribute:: Stream.mediatype

    A string attribute that is ``'normal'``, ``'audio'`` or ``'video'``, 
    depending on the content of the stream

.. attribute:: Stream.quality

    The resolution or the bitrate of the stream, depending on whether the
    stream is video or audio respectively

.. attribute:: Stream.resolution

    The resolution of a video as a string, eg: "820x640".  Note if the stream
    is 3D this will be appended; eg: "820x640-3D".  

    For audio streams, this will be set to "0x0"

.. attribute:: Stream.rawbitrate

    The bitrate of an audio stream, *int*
    
    For video streams, this will be set to *None*

.. attribute:: Stream.threed

    True if the stream is a 3D video (*boolean*)

.. attribute:: Stream.title

    The title of the video, this will be the same as :attr:`Pafy.title`

.. attribute:: Stream.notes

    Any additional notes regarding the stream (eg, 6-channel surround) *str*
   

An example of accessing Stream attributes::

    >>> import pafy
    >>> v = pafy.new("cyMHZVT91Dw")
    >>> v.audiostreams
    [audio:m4a@48k, audio:m4a@128k, audio:m4a@256k]
    >>> mystream = v.audiostreams[2]
    >>> mystream.rawbitrate
    255940
    >>> mystream.bitrate
    '256k'
    >>> mystream.url
    'http://r20---sn-aigllnes.c.youtube.com/videoplayback?ipbits=8&clen=1130...


Stream Methods
--------------




.. function:: Stream.get_filesize()     

    Returns the filesize of a stream

.. function:: Stream.download([filepath=""][, quiet=False][, callback=None][, meta=False][, remux_audio=False])

    Downloads the stream object, returns the path of the downloaded file.

    :param filepath: The filepath to use to save the stream, defaults to (sanitised) *title.extension* if ommitted
    :type filepath: string
    :param quiet: If True, supress output of the download progress
    :type quiet: boolean
    :param callback: Call back function to use for receiving download progress
    :type callback: function or None
    :param meta: If True, video id and itag are appended to filename
    :type meta: bool
    :param remux_audio: If True, remux audio file downloads (fixes some compatibility issues with file format, requires ffmpeg/avconv)
    :type remux_audio: bool
    :rtype: str
    
    If a callback function is provided, it will be called repeatedly for each chunk downloaded.  It must be a function that takes the following five arguments;

    - total bytes in stream, *int*
    - total bytes downloaded, *int*
    - ratio downloaded (0-1), *float*
    - download rate (kbps), *float*
    - ETA in seconds, *float*


:func:`Stream.download` example
-------------------------------

Example of using stream.download()::

    import pafy
    v = pafy.new("cyMHZVT91Dw")
    s = v.getbest()
    print("Size is %s" % s.get_filesize())
    filename = s.download()  # starts download

Will download to the current working directory and output the following progress statistics::

    Size is 34775366
    1,015,808 Bytes [2.92%] received. Rate: [ 640 kbps].  ETA: [51 secs] 

Download using *callback* example::

    import pafy

    # callback function, this callback simply prints the bytes received,
    # ratio downloaded and eta.
    def mycb(total, recvd, ratio, rate, eta):
        print(recvd, ratio, eta)

    p = pafy.new("cyMHZVT91Dw")
    ba = p.getbestaudio()
    filename = ba.download(quiet=True, callback=mycb)

The output of this will appear as follows, while the file is downloading::

    (16384, 0.001449549245392125, 20.05230682669207)
    (32768, 0.00289909849078425, 16.88200659636641)
    (49152, 0.004348647736176375, 15.196503182407469)
    (65536, 0.0057981969815685, 14.946467230009146)
    (81920, 0.007247746226960625, 15.066431667096913)
    (98304, 0.00869729547235275, 14.978577915171627)
    (114688, 0.010146844717744874, 14.529802172976945)
    (131072, 0.011596393963137, 14.31917945870373)
    ...
    

Playlist Retrieval
==================


The :func:`pafy.get_playlist` function is initialised with similar arguments to :func:`pafy.new` and will return a dict containing metadata and :class:`Pafy` objects as listed in the YouTube playlist.

.. function:: pafy.get_playlist(playlist_url[, basic=False][, gdata=False][, signature=False][, size=False][, callback=None])


    :param playlist_url: The YouTube playlist url
    :type playlist_url: str
    :param basic: fetch basic metadata and streams
    :type basic: bool
    :param gdata: fetch gdata info (upload date, description, category, username, likes, dislikes)
    :type gdata: bool
    :param signature: fetch data required to decrypt urls, if encrypted
    :type signature: bool
    :param size: fetch the size of each stream (slow)(decrypts urls if needed) 
    :type size: bool
    :param callback: a callback function to receive status strings
    :type callback: function
    :rtype: dict

The returned dict contains the following keys:

    **playlist_id**: the id of the playlist

    **likes**: the number of likes for the playlist

    **dislikes**: the number of dislikes for the playlist

    **title**: the title of the playlist

    **author**: the author of the playlist

    **description**: the description of the playlist

    **items**: a list of dicts with each dict representing a video and containing the following keys:
        
        **pafy**: The :class:`Pafy` object for this video, initialised with the arguments given to :func:`pafy.get_playlist`

        **playlist_meta**: a dict of various video-specific metadata fetched from the playlist data, including:

            **added**, 
            **likes**,
            **dislikes**,
            **thumbnail**,
            **is_cc**,
            **is_hd**,
            **user_id**,
            **cc_license**,
            **privacy**,
            **category_id**

:func:`pafy.get_playlist` example
---------------------------------

    >>> import pafy
    >>> plurl = "https://www.youtube.com/playlist?list=PL634F2B56B8C346A2"
    >>> playlist = pafy.get_playlist(plurl)
    >>> 
    >>> playlist['title']
    u'Rick Astley playlist'
    >>> 
    >>> playlist['author']
    u'Deborah Back'
    >>>
    >>> len(playlist['items'])
    43
    >>>
    >>> playlist['items'][21]['pafy']
    Title: Body and Soul - Rick astley
    Author: jadiafa
    ID: QtHnEJ8UArY
    Duration: 00:04:11
    Rating: 5.0
    Views: 18855
    Thumbnail: http://i1.ytimg.com/vi/QtHnEJ8UArY/default.jpg
    Keywords: Rick, astely, body, and, soul, pop
    >>>
    >>> playlist['items'][21]['pafy'].audiostreams
    [audio:m4a@128k]
    >>>
    >>> playlist['items'][21]['pafy'].getbest()
    normal:webm@640x360
    >>>
    >>> playlist['items'][21]['pafy'].getbest().url
    u'http://r4---sn-4g57knzr.googlevideo.com/videoplayback?ipbits=0&ratebypas...'


The :func:`pafy.get_playlist2` serves the same purpose as the :func:`pafy.get_playlist`, but uses version 3 of youtube's api, making it able to retrieve playlists of over 200 items. It also provides a different interface, returning a :class:`pafy.Playlist` instead of a dictionary.

.. function:: pafy.get_playlist2(playlist_url[, basic=False][, gdata=False][, signature=False][, size=False][, callback=None])

    :param playlist_url: The YouTube playlist url
    :type playlist_url: str
    :param basic: fetch basic metadata and streams
    :type basic: bool
    :param gdata: fetch gdata info (upload date, description, category, username, likes, dislikes)
    :type gdata: bool
    :param signature: fetch data required to decrypt urls, if encrypted
    :type signature: bool
    :param size: fetch the size of each stream (slow)(decrypts urls if needed) 
    :type size: bool
    :param callback: a callback function to receive status strings
    :type callback: function
    :rtype: :class:`pafy.Playlist`

Playlist Attributes
-------------------

Once you have retrieved a playlist with :func:`pafy.get_playlist2` you can iterate over it to get the Pafy objects for the items in it, or use `len(playlist)` to get its length. In addition, you can access the following attributes:

.. attribute:: Pafy.plid

    The ID of the playlist (*str*)

.. attribute:: Pafy.title

    The title of the playlist (*str*)

.. attribute:: Pafy.author

    The author of the playlist (*str*)

.. attribute:: Pafy.description

    The description of the playlist (*str*)

