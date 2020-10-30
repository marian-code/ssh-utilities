"""Remote working substitutions for some python modules.

Includes: `os`, `pathlib`, `shutil`, `subprocess` and `open` from python
builtins. Only a subset of API from each module is supported.
"""

from .remote import SSHConnection
from ._subprocess import PIPE, STDOUT, DEVNULL
from ._os import Os
from ._builtins import Builtins
from ._pathlib import Pathlib
from ._shutil import Shutil
from ._subprocess import Subprocess

__all__ = ["SSHConnection", "PIPE", "STDOUT", "DEVNULL", "Builtins", "Os",
           "Pathlib", "Shutil", "Subprocess"]