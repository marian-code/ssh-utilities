"""Collection of modules mirroring API or remote module."""

from .local import LocalConnection
from ._os import Os
from ._builtins import Builtins
from ._pathlib import Pathlib
from ._shutil import Shutil
from ._subprocess import Subprocess

__all__ = ["LocalConnection", "Builtins", "Os", "Pathlib", "Shutil",
           "Subprocess"]
