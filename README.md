PAFY
====

Python API for YouTube

by nagev


Features:
---------

 - Download any stream for a particular video
 - Select best quality stream for download
 - Retreive metadata such as viewcount, duration, rating, author, thumbnail, keywords
 - Retrieve all availabe streams for a YouTube video (all resolutions and formats)
 - Retrieve the Download URL to download or stream the video
 - Small, standalone, single importable module file.
 - Works with age-restricted videos and non-embeddable videos
 - No dependencies


Usage Examples:
---------------

Here is how to use the module in your own python code:

```python

>>> from pafy import Pafy
>>> url = "http://www.youtube.com/watch?v=cyMHZVT91Dw"


    # create a video instance
    
>>> video = Pafy(url)


    # get certain attributes
    
>>> video.title
u'Rick Astley Sings Live - Never Gonna Give You Up - This Morning'


>>> video.rating
4.93608852755

>>> video.length
355

    # display video metadata
    
>>> print video
Title: Rick Astley Sings Live - Never Gonna Give You Up - This Morning
Author: Ryan915
ID: cyMHZVT91Dw
Duration: 00:05:55
Rating: 4.93608852755
Views: 672583
Thumbnail: https://i1.ytimg.com/vi/cyMHZVT91Dw/default.jpg
Keywords: Rick, Astley, Sings, Live, on, This, Morning, Never, Gonna, Gunna, Give, You,...


    # show all formats for a video:
    
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


    # show all formats and their download url:

>>> for s in streams:
>>>     print s.resolution, s.extension, s.url
480x854 webm http://r12--sn-aoh8kier.c.youtube.com/videoplayback?expire=1369...
480x854 flv http://r11---sn-aoh8kier.c.youtube.com/videoplayback?expire=1369...
360x640 webm http://r11---sn-aoh8kier.c.youtube.com/videoplayback?expire=1369...
360x640 flv http://r11---sn-aoh8kier.c.youtube.com/videoplayback?expire=1369...
360x640 mp4 http://r11---sn-aoh8kier.c.youtube.com/videoplayback?expire=1369...
240x400 flv http://r11---sn-aoh8kier.c.youtube.com/videoplayback?expire=1369...
320x240 3gp http://r11---sn-aoh8kier.c.youtube.com/videoplayback?expire=1369...
144x176 3gp http://r11---sn-aoh8kier.c.youtube.com/videoplayback?expire=1369...


    # get best resolution regardless of file format:
    
>>> best = video.getbest()
>>> best.resolution, best.extension
('480x854', 'webm')


    # get best resolution for a particular file format:
    # (mp4, webm, flv or 3gp)
    
>>> best = video.getbest(preftype="mp4")
>>> best.resolution, best.extension
('360x640', 'mp4')


    # get best resolution for a particular file format, or return
    # a different format if it has the best resolution
    
>>> best = video.getbest(preftype="mp4", ftypestrict=False)
>>> best.resolution, best.extension
('480x854', 'webm')


    # get url, for download or streaming in mplayer / vlc etc
    
>>> best.url
'http://r12---sn-aig7kner.c.youtube.com/videoplayback?expire=1369...


    # Download video and show progress:
    
>>> best.download(progress=True)
-Downloading 'Rick Astley Sings Live - Never Gonna Give You Up - This Morning.webm' [56,858,674 Bytes]
Traceback (most recent call last):ed. Rate: [1095 kbps].  ETA: [33 secs]  


    # Download video, use specific filepath:
    
>>> myfilename = "/tmp/" + best.title + "." + best.extension
>>> best.download(progress=False, filepath=myfilename)
-Downloading 'Rick Astley Sings Live - Never Gonna Give You Up - This Morning.webm' [56,858,674 Bytes]
Done
```




