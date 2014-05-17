from .pafy import get_playlist
from .pafy import new
import sys

__version__ = "0.3.43"
__author__ = "nagev"
__license__ = "GPLv3"

if "test" not in sys.argv[0]:
    del pafy

del sys

__all__ = "get_playlist new".split()
