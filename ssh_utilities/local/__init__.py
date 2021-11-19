"""Collection of modules mirroring API or remote module."""

# ! preserve this order otherwise import fail
from ._os import Os
from ._os_path import OsPath
from ._builtins import Builtins
from ._pathlib import Pathlib
from ._shutil import Shutil
from ._subprocess import Subprocess
from .local import LocalConnection

__all__ = ["LocalConnection", "Builtins", "Os", "Pathlib", "Shutil",
           "Subprocess", "OsPath"]
