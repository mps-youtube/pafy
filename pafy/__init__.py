from .pafy import get_playlist
from .pafy import new
from .pafy import __version__
from .pafy import __author__
from .pafy import __license__
import sys

if "test" not in sys.argv[0]:
    del pafy

del sys
