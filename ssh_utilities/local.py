"""Module implementing local connection functionality.

Has the same API as remote version.
"""

import logging
import os
import shutil
import subprocess
from pathlib import Path
from socket import gethostname
from typing import IO, TYPE_CHECKING, List, Optional, Union

from typing_extensions import Literal

from .base import ConnectionABC
from .constants import C, G, R, Y
from .utils import context_timeit, file_filter, lprint

if TYPE_CHECKING:
    from .path import SSHPath
    SPath = Union[str, Path, SSHPath]
    GlobPat = Optional[str]

__all__ = ["LocalConnection"]

LOGGER = logging.getLogger(__name__)


class LocalConnection(ConnectionABC):
    """Emulates SSHConnection class on local PC."""

    _osname: Literal["nt", "posix", "java", ""] = ""

    def __init__(self, address: Optional[str], username: str,
                 password: Optional[str] = None,
                 rsa_key_file: Optional[Union[str, Path]] = None,
                 line_rewrite: bool = True, warn_on_login: bool = False,
                 server_name: Optional[str] = None,
                 logger: logging.Logger = None) -> None:

        # set login credentials
        self.password = password
        self.address = address
        self.username = username
        self.rsa_key_file = rsa_key_file

        self.server_name = server_name if server_name else gethostname()
        self.server_name = self.server_name.upper()

        self.log = logger if logger else LOGGER

        self.local = True

    def __str__(self) -> str:
        return self.to_str("LocalConnection", self.server_name, None,
                           self.username, None)

    @staticmethod
    def close(*, quiet: bool):
        """Close emulated local connection."""
        lprint(quiet)(f"{G}Closing local connection")

    @staticmethod
    def ssh_log(log_file="paramiko.log", level="WARN"):
        lprint()(f"{Y}Local sessions are not logged!")

    @staticmethod
    def run(args: List[str], *, suppress_out: bool, quiet: bool = True,
            capture_output: bool = False, check: bool = False,
            cwd: Optional[Union[str, Path]] = None, encoding: str = "utf-8"
            ) -> subprocess.CompletedProcess:
        out = subprocess.run(args, encoding=encoding, stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE, check=check, cwd=cwd)

        if capture_output and not suppress_out:
            lprint(quiet)(f"{C}Printing local output\n{'-' * 111}{R}")
            lprint(quiet)(out.stdout)
            lprint(quiet)(f"{C}{'-' * 111}{R}\n")

        return out

    @staticmethod
    def copy_files(files: List[str], remote_path: "SPath",
                   local_path: "SPath", direction: str, quiet: bool = False):

        with context_timeit(quiet):
            for f in files:
                file_remote = Path(remote_path) / f
                file_local = Path(local_path) / f

                if direction == "get":
                    shutil.copy2(file_remote, file_local)
                elif direction == "put":
                    shutil.copy2(file_local, file_remote)
                else:
                    raise ValueError(f"{direction} is not valid direction. "
                                     f"Choose 'put' or 'get'")

    def download_tree(self, remote_path: "SPath", local_path: "SPath",
                      include: "GlobPat" = None, exclude: "GlobPat" = None,
                      remove_after: bool = True, quiet: bool = False):

        def _cpy(src: str, dst: str):
            if allow_file(src):
                shutil.copy2(src, dst)

        allow_file = file_filter(include, exclude)

        remote_path = self._path2str(remote_path)
        local_path = self._path2str(local_path)

        if remove_after:
            shutil.move(remote_path, local_path, copy_function=_cpy)
        else:
            shutil.copytree(remote_path, local_path, copy_function=_cpy)

    def upload_tree(self, local_path: "SPath", remote_path: "SPath",
                    include: "GlobPat" = None, exclude: "GlobPat" = None,
                    remove_after: bool = True, quiet: bool = False):

        self.download_tree(local_path, remote_path, include=include,
                           exclude=exclude, remove_after=remove_after,
                           quiet=quiet)

    @staticmethod
    def isfile(path: "SPath") -> bool:
        return os.path.isfile(path)

    @staticmethod
    def isdir(path: "SPath") -> bool:
        return os.path.isdir(path)

    def Path(self, path: "SPath") -> Path:
        return Path(self._path2str(path))

    @staticmethod
    def mkdir(path: "SPath", mode: int = 511, exist_ok: bool = True,
              parents: bool = True, quiet: bool = True):
        Path(path).mkdir(mode=mode, parents=parents, exist_ok=exist_ok)

    @staticmethod
    def rmtree(path: "SPath", ignore_errors: bool = False,
               quiet: bool = True):
        shutil.rmtree(path, ignore_errors=ignore_errors)

    @staticmethod
    def listdir(path: "SPath") -> List[str]:
        return os.listdir(path)

    @staticmethod
    def open(filename: "SPath", mode: str = "r",
             encoding: Optional[str] = None,
             bufsize: int = -1, errors: Optional[str] = None
             ) -> IO:
        encoding = encoding if encoding else "utf-8"
        errors = errors if errors else "strict"

        return open(filename, mode, encoding=encoding, errors=errors)

    @property
    def osname(self) -> Literal["nt", "posix", "java"]:
        if not self._osname:
            self._osname = os.name

        return self._osname

    # ! DEPRECATED
    @staticmethod
    def sendCommand(command: str, suppress_out: bool, quiet: bool = True):
        return subprocess.run([command], stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE).stdout

    sendFiles = copy_files  # type: ignore
    send_files = copy_files  # type: ignore
    downloadTree = download_tree
    uploadTree = upload_tree
