from .pafy import get_playlist
from .pafy import new
from .pafy import set_api_key
from .pafy import dump_cache
from .pafy import load_cache
from .pafy import get_categoryname
from .pafy import __version__
from .pafy import __author__
from .pafy import __license__
import sys

if "test" not in sys.argv[0]:
    del pafy

del sys
