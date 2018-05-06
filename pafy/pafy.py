# -*- coding: utf-8 -*-

"""
pafy.py.

Python library to download YouTube content and retrieve metadata

https://github.com/np1/pafy

Copyright (C)  2013-2014 np1

This program is free software: you can redistribute it and/or modify it under
the terms of the GNU Lesser General Public License as published by the Free
Software Foundation, either version 3 of the License, or (at your option) any
later version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY
WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
PARTICULAR PURPOSE.  See the GNU Lesser General Public License for more details.

You should have received a copy of the GNU Lesser General Public License along
with this program.  If not, see <http://www.gnu.org/licenses/>.

"""

import sys
import os
import logging
import time
import re

if sys.version_info[:2] >= (3, 0):
    # pylint: disable=E0611,F0401,I0011
    from urllib.error import HTTPError

else:
    from urllib2 import HTTPError

from . import g
from .util import call_gdata

Pafy = None

# Select which backend to use
backend = "internal"
if os.environ.get("PAFY_BACKEND") != "internal":
    try:
        import youtube_dl
        backend = "youtube-dl"
    except ImportError:
        raise ImportError(
               "pafy: youtube-dl not found; you can use the internal backend by "
               "setting the environmental variable PAFY_BACKEND to \"internal\". "
               "It is not enabled by default because it is not as well maintained "
               "as the youtube-dl backend.")

if os.environ.get("pafydebug") == "1":
    logging.basicConfig(level=logging.DEBUG)


dbg = logging.debug


def fetch_decode(url, encoding=None):
    """ Fetch url and decode. """
    try:
        req = g.opener.open(url)
    except HTTPError as e:
        if e.getcode() == 503:
            time.sleep(.5)
            return fetch_decode(url, encoding)
        else:
            raise

    ct = req.headers['content-type']

    if encoding:
        return req.read().decode(encoding)

    elif "charset=" in ct:
        dbg("charset: %s", ct)
        encoding = re.search(r"charset=([\w-]+)\s*(:?;|$)", ct).group(1)
        return req.read().decode(encoding)

    else:
        dbg("encoding unknown")
        return req.read()


def new(url, basic=True, gdata=False, size=False,
        callback=None, ydl_opts=None):
    """ Return a new pafy instance given a url or video id.

    NOTE: The signature argument has been deprecated and now has no effect,
        it will be removed in a future version.

    Optional arguments:
        basic - fetch basic metadata and streams
        gdata - fetch gdata info (upload date, description, category)
        size - fetch the size of each stream (slow)(decrypts urls if needed)
        callback - a callback function to receive status strings

    If any of the first three above arguments are False, those data items will
    be fetched only when first called for.

    The defaults are recommended for most cases. If you wish to create
    many video objects at once, you may want to set basic to False, eg:

        video = pafy.new(basic=False)

    This will be quick because no http requests will be made on initialisation.

    Setting size to True will override the basic argument and force basic data
    to be fetched too (basic data is required to obtain Stream objects).

    """
    global Pafy
    if Pafy is None:
        if backend == "internal":
           from .backend_internal import InternPafy as Pafy
        else:
           from .backend_youtube_dl import YtdlPafy as Pafy

    return Pafy(url, basic, gdata, size, callback, ydl_opts=ydl_opts)


def cache(name):
    """ Returns a sub-cache dictionary under which global key, value pairs
    can be stored. Regardless of whether a dictionary already exists for
    the given name, the sub-cache is returned by reference.
    """
    if name not in g.cache:
        g.cache[name] = {}
    return g.cache[name]


def get_categoryname(cat_id):
    """ Returns a list of video category names for one category ID. """
    timestamp = time.time()
    cat_cache = cache('categories')
    cached = cat_cache.get(cat_id, {})
    if cached.get('updated', 0) > timestamp - g.lifespan:
        return cached.get('title', 'unknown')
    # call videoCategories API endpoint to retrieve title
    query = {'id': cat_id,
             'part': 'snippet'}
    catinfo = call_gdata('videoCategories', query)
    try:
        for item in catinfo.get('items', []):
            title = item.get('snippet', {}).get('title', 'unknown')
            cat_cache[cat_id] = {'title':title, 'updated':timestamp}
            return title
        cat_cache[cat_id] = {'updated':timestamp}
        return 'unknown'
    except Exception:
        raise IOError("Error fetching category name for ID %s" % cat_id)


def set_categories(categories):
    """ Take a dictionary mapping video category IDs to name and retrieval
    time. All items are stored into cache node 'videoCategories', but
    for the ones with a retrieval time too long ago, the v3 API is queried
    before.
    """
    timestamp = time.time()
    idlist = [cid for cid, item in categories.items()
              if item.get('updated', 0) < timestamp - g.lifespan]
    if len(idlist) > 0:
        query = {'id': ','.join(idlist),
                 'part': 'snippet'}
        catinfo = call_gdata('videoCategories', query)
        try:
            for item in catinfo.get('items', []):
                cid = item['id']
                title = item.get('snippet', {}).get('title', 'unknown')
                categories[cid] = {'title':title, 'updated':timestamp}
        except Exception:
            raise IOError("Error fetching category name for IDs %s" % idlist)
    cache('categories').update(categories)


def load_cache(newcache):
    """Loads a dict into pafy's internal cache."""
    set_categories(newcache.get('categories', {}))


def dump_cache():
    """Returns pafy's cache for storing by program."""
    return g.cache


def set_api_key(key):
    """Sets the api key to be used with youtube."""
    g.api_key = key
