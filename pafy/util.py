import json
import sys
import os

if sys.version_info[:2] >= (3, 0):
    # pylint: disable=E0611,F0401,I0011
    from urllib.error import HTTPError
    from urllib.parse import urlencode

else:
    from urllib2 import HTTPError
    from urllib import urlencode

from . import g


mswin = os.name == "nt"
not_utf8_environment = mswin or (sys.stdout.encoding and
                                 "UTF-8" not in sys.stdout.encoding)


class GdataError(Exception):
    """Gdata query failed."""
    pass


def call_gdata(api, qs):
    """Make a request to the youtube gdata api."""
    qs = dict(qs)
    qs['key'] = g.api_key
    url = g.urls['gdata'] + api + '?' + urlencode(qs)

    try:
        data = g.opener.open(url).read().decode('utf-8')
    except HTTPError as e:
        try:
            errdata = e.file.read().decode()
            error = json.loads(errdata)['error']['message']
            errmsg = 'Youtube Error %d: %s' % (e.getcode(), error)
        except:
            errmsg = str(e)
        raise GdataError(errmsg)

    return json.loads(data)


def utf8_replace(txt):
    """
    Replace unsupported characters in unicode string.

    :param txt: text to filter
    :type txt: str
    :returns: Unicode text without any characters unsupported by locale
    :rtype: str
    """
    sse = sys.stdout.encoding
    txt = txt.encode(sse, "replace").decode(sse)
    return txt


def xenc(stuff):
    """ Replace unsupported characters. """
    return utf8_replace(stuff) if not_utf8_environment else stuff
