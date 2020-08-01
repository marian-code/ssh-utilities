"""Module implementing local connection functionality.

Has the same API as remote version.
"""

from .base import ConnectionABC
from .utils import lprint
import shutil
from .constants import Y, G, C, R
import os
from typing import TYPE_CHECKING, Union, List, Optional, IO
from pathlib import Path
import logging
import subprocess

if TYPE_CHECKING:
    from .path import SSHPath
    SPath = Union[str, Path, SSHPath]

__all__ = ["LocalConnection"]


class LocalConnection(ConnectionABC):
    """Emulates SSHConnection class on local PC."""

    def __init__(self, address, username, password=None, sshKey=None,
                 line_rewrite=True, warn_on_login=False, server_name=None,
                 logger=None):

        self.username = username

        if server_name is None:
            from socket import gethostname
            self.server_name = gethostname().upper()
        else:
            self.server_name = server_name.upper()

        if logger is None:
            self.log = logging.getLogger()
        else:
            self.log = logger

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
        out = subprocess.run(args, capture_output=capture_output, check=check,
                             cwd=cwd, encoding=encoding)

        if capture_output and not suppress_out:
            lprint(quiet)(f"{C}Printing local output\n{'-' * 111}{R}")
            lprint(quiet)(out.stdout)
            lprint(quiet)(f"{C}{'-' * 111}{R}\n")

        return out

    def copy_files(self, files: List[str], remote_path: "SPath",
                   local_path: "SPath", direction: str, quiet: bool = False):

        with self.context_timeit(quiet):
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
                      include="all", remove_after: bool = True,
                      quiet: bool = False):
        # TODO include parameter is not used!!!
        remote_path = self._path2str(remote_path)
        local_path = self._path2str(local_path)

        if remove_after:
            shutil.move(remote_path, local_path)
        else:
            shutil.copytree(remote_path, local_path)

    def upload_tree(self, local_path: "SPath", remote_path: "SPath",
                    remove_after: bool = True, quiet: bool = False):
        remote_path = self._path2str(remote_path)
        local_path = self._path2str(local_path)

        if remove_after:
            shutil.move(local_path, remote_path)
        else:
            shutil.copytree(local_path, remote_path)

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
             encoding: Optional[str] = "utf-8", bufsize: int = -1) -> IO:
        return open(filename, mode, encoding=encoding)

    # ! DEPRECATED
    @staticmethod
    def sendCommand(command: str, suppress_out: bool, quiet: bool = True):
        return subprocess.run([command], capture_output=True).stdout

    sendFiles = copy_files
    send_files = copy_files
    downloadTree = download_tree
    uploadTree = upload_tree
