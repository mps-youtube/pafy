#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function
import pafy

url = "http://www.youtube.com/watch?v=cyMHZVT91Dw"

# create a video instance

video = pafy.new(url)

# get certain attributes

print("\n\n")
print("Title, Rating, Length, Upload date, Uploader")
print("--------------------------------------------")
print(video.title)
print(video.rating)  # out of 5
print(video.length)  # seconds
print(video.published)
print(video.author)
print("\n")

# get video metadata

print("Video meta info...")
print("------------------")
print(video)
print("\n")

# show all formats for a video:

print("All available formats...")
print("------------------------")
streams = video.streams
print([(s.resolution, s.extension) for s in streams])
print("\n")

# show all formats and their download/stream url:

print("All available streams...")
print("------------------------")
for s in streams:
    print(s.resolution, s.extension, s.url[:60] + "...")
print("\n")

# get best resolution regardless of file format

print("Best available quality...")
print("-------------------------")
best = video.getbest()
print(best.resolution, best.extension)
print("\n")

# get best resolution for a specified file format
# (mp4, webm, flv or 3gp)

print("Best available mp4 quality...")
print("-----------------------------")
best = video.getbest(preftype="mp4")
print(best.resolution, best.extension)
print("\n")

# get best resolution for specified file format, or return a different format
# if one happens to have a better resolution than the specified format

print("Best available quality, mp4 if exists as best")
print("---------------------------------------------")
best = video.getbest(preftype="mp4", ftypestrict=False)
print(best.resolution, best.extension)
print("\n")

# get url - for download or for streaming in mplayer / vlc

print("Best available quality url")
print("--------------------------")
print(best.url[:60] + "...")
print("\n")

# download video, show progress

print("Download video, show progress")
print("-----------------------------")
print("Uncomment line in example.py source file to enable")
#best.download(quiet=False)
print("\n")

# download, specify output filepath

print("Download video, specify filepath")
print("--------------------------------")
print("Uncomment line in example.py source file to enable")
filename = "/tmp/" + best.title + best.extension
#best.download(quiet=False, filepath=filename)
