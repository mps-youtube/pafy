import sys

__version__ = "0.5.0"
__author__ = "np1"
__license__ = "LGPLv3"


# External api
from .pafy import new
from .pafy import set_api_key
from .pafy import load_cache, dump_cache
from .pafy import get_categoryname
from .pafy import backend
from .util import GdataError, call_gdata
from .playlist import get_playlist, get_playlist2

if "test" not in sys.argv[0]:
    del pafy

del sys
