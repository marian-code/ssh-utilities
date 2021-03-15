"""Module collecting shutil-like remote methods."""

import logging
import os
import shutil
from os.path import join as jn
from typing import TYPE_CHECKING, List

from typing_extensions import Literal

from ..abc import ShutilABC
from ..constants import LG, C, G, R
from ..utils import ProgressBar
from ..utils import bytes_2_human_readable as b2h
from ..utils import context_timeit, file_filter, lprint
from ._connection_wrapper import check_connections

if TYPE_CHECKING:
    from typing_extensions import TypedDict

    from ..typeshed import _CALLBACK, _DIRECTION, _GLOBPAT, _SPATH
    from .remote import SSHConnection

    _COPY_FILES = TypedDict("_COPY_FILES", {"dst": str, "src": str,
                                            "size": int})

__all__ = ["Shutil"]

log = logging.getLogger(__name__)


class Shutil(ShutilABC):
    """Class with remote versions of shutil methods.

    See also
    --------
    :class:`ssh_utilities.local.Shutil`
        local version of class with same API
    """

    def __init__(self, connection: "SSHConnection") -> None:
        self.c = connection

    @check_connections(exclude_exceptions=ValueError)
    def copy_files(self, files: List[str], remote_path: "_SPATH",
                   local_path: "_SPATH", *, direction: "_DIRECTION",
                   follow_symlinks: bool = True, quiet: bool = False):

        with context_timeit(quiet):
            for f in files:
                if direction == "get":
                    src = jn(self.c._path2str(remote_path), f)
                    dst = jn(self.c._path2str(local_path), f)
                elif direction == "put":
                    dst = jn(self.c._path2str(remote_path), f)
                    src = jn(self.c._path2str(local_path), f)
                else:
                    raise ValueError(f"{direction} is not valid direction. "
                                     f"Choose 'put' or 'get'")

                self.copyfile(src, dst, direction=direction,
                              follow_symlinks=follow_symlinks, callback=None,
                              quiet=quiet)

    @check_connections(exclude_exceptions=(FileNotFoundError, ValueError,
                                           IsADirectoryError))
    def copyfile(self, src: "_SPATH", dst: "_SPATH", *,
                 direction: "_DIRECTION", follow_symlinks: bool = True,
                 callback: "_CALLBACK" = None, quiet: bool = True):

        def _dummy_callback(_1: float, _2: float):
            """Dummy callback function."""
            pass

        callback = callback if callback else _dummy_callback

        lprnt = lprint(quiet=quiet)

        if direction == "get":
            lprnt(f"{G}Copying from remote:{R} {self.c.server_name}@{src}{LG}"
                  f"\n-->           local:{R} {dst}")

            if os.path.isdir(self.c._path2str(dst)):
                raise IsADirectoryError("dst argument must be full path "
                                        "not a directory")

            if follow_symlinks:
                src = self.c.os.path.realpath(src)
                dst = os.path.realpath(dst)

            try:
                self.c.sftp.get(src, dst, callback)
            except IOError as e:
                raise FileNotFoundError(f"File you are trying to get "
                                        f"does not exist: {e}")

        elif direction == "put":
            lprnt(f"{G}Copying from local:{R} {src}\n"
                  f"{LG} -->       remote: {self.c.server_name}@{dst}")

            if self.c.os.isdir(dst):
                raise IsADirectoryError("dst argument must be full path "
                                        "not a directory")

            if follow_symlinks:
                src = os.path.realpath(src)
                dst = self.c.os.path.realpath(dst)

            self.c.sftp.put(src, dst, callback)
        else:
            raise ValueError(f"{direction} is not valid direction. "
                             f"Choose 'put' or 'get'")

    def copy(self, src: "_SPATH", dst: "_SPATH", *, direction: "_DIRECTION",
             follow_symlinks: bool = True, callback: "_CALLBACK" = None,
             quiet: bool = True):

        if direction == "get":
            if os.path.isdir(self.c._path2str(dst)):
                dst = jn(dst, os.path.basename(self.c._path2str(src)))

        elif direction == "put" and self.c.os.isdir(dst):
            dst = jn(dst, os.path.basename(self.c._path2str(src)))

        self.copyfile(src, dst, direction=direction,
                      follow_symlinks=follow_symlinks, callback=callback,
                      quiet=quiet)

    copy2 = copy

    @check_connections(exclude_exceptions=(FileNotFoundError, OSError))
    def rmtree(self, path: "_SPATH", ignore_errors: bool = False,
               quiet: bool = True):

        sn = self.c.server_name
        path = self.c._path2str(path)

        with context_timeit(quiet):
            lprint(quiet)(f"{G}Recursively removing dir:{R} {sn}@{path}")

            try:
                for root, _, files in self.c.os.walk(path, followlinks=True):
                    for f in files:
                        f = jn(root, f)
                        lprint(quiet)(f"{G}removing file:{R} {sn}@{f}")
                        if self.c.os.isfile(f):
                            self.c.sftp.remove(f)
                    if self.c.os.isdir(root):
                        self.c.sftp.rmdir(root)

                if self.c.os.isdir(path):
                    self.c.sftp.rmdir(path)
            except FileNotFoundError as e:
                if ignore_errors:
                    log.warning("Directory does not exist")
                else:
                    raise FileNotFoundError(e)

    @check_connections(exclude_exceptions=FileNotFoundError)
    def download_tree(
        self, remote_path: "_SPATH", local_path: "_SPATH",
        include: "_GLOBPAT" = None, exclude: "_GLOBPAT" = None,
        remove_after: bool = False,
        quiet: Literal[True, False, "stats", "progress"] = False
    ):

        dst = self.c._path2str(local_path)
        src = self.c._path2str(remote_path)

        if not self.c.os.isdir(remote_path):
            raise FileNotFoundError(f"{remote_path} you are trying to download"
                                    f"from does not exist")

        lprnt = lprint(quiet=True if quiet in (True, "stats") else False)
        allow_file = file_filter(include, exclude)

        copy_files: List["_COPY_FILES"] = []
        dst_dirs = []

        lprnt(f"{C}Building directory structure for download from remote...\n")

        # create a list of directories and files to copy
        for root, _, files in self.c.os.walk(src, followlinks=True):

            lprnt(f"{G}Searching remote directory:{R} "
                  f"{self.c.server_name}@{root}", up=1)

            # record directories that need to be created on local side
            directory = root.replace(src, "")
            if directory.startswith("/"):
                directory = directory.replace("/", "")
            dst_dirs.append(jn(dst, directory))

            for f in files:
                dst_file = jn(dst, directory, f)

                if not allow_file(dst_file):
                    continue

                copy_files.append({
                    "dst": dst_file,
                    "src": jn(root, f),
                    "size": self.c.os.lstat(jn(root, f)).st_size
                })

        # file number and size statistics
        n_files = len(copy_files)
        total = sum([f["size"] for f in copy_files])

        lprnt(f"\n|--> {C}Total number of files to copy:{R} {n_files}")
        lprnt(f"|--> {C}Total size of files to copy:{R} {b2h(total)}")

        # create directories on local side to copy to
        lprnt(f"\n{C}Creating directory structure on local side...")
        for d in dst_dirs:
            os.makedirs(d, exist_ok=True)

        # copy
        lprnt(f"\n{C}Copying...{R}\n")

        # get lenghts of path strings so when overwriting no artifacts are
        # produced if previous path is longer than new one
        max_src = max([len(c["src"]) for c in copy_files])
        max_dst = max([len(c["dst"]) for c in copy_files])

        q = True if quiet in (True, "progress") else False
        with ProgressBar(total=total, quiet=q) as t:
            for cf in copy_files:

                t.write(f"{G}Copying remote:{R} {self.c.server_name}@"
                        f"{cf['src']:<{max_src}}"
                        f"\n{G}     --> local:{R} {cf['dst']:<{max_dst}}")

                try:
                    self.c.sftp.get(cf["src"], cf["dst"],
                                    callback=t.update_bar)
                except IOError as e:
                    raise IOError(
                        f"The file {cf['src']} could not be copied to "
                        f"{cf['dst']}. This is probably due to permission "
                        f"error: {e}")

        lprnt("")

        if remove_after:
            self.rmtree(src)

    @check_connections(exclude_exceptions=FileNotFoundError)
    def upload_tree(
        self, local_path: "_SPATH", remote_path: "_SPATH",
        include: "_GLOBPAT" = None, exclude: "_GLOBPAT" = None,
        remove_after: bool = False,
        quiet: Literal[True, False, "stats", "progress"] = False
    ):

        src = self.c._path2str(local_path)
        dst = self.c._path2str(remote_path)

        if not os.path.isdir(local_path):
            raise FileNotFoundError(f"{local_path} you are trying to upload "
                                    f"does not exist")

        lprnt = lprint(quiet=True if quiet in (True, "stats") else False)
        allow_file = file_filter(include, exclude)

        copy_files: List["_COPY_FILES"] = []
        dst_dirs = []

        lprnt(f"{C}Building directory structure for upload to remote...\n")

        # create a list of directories and files to copy
        for root, _, files in os.walk(src, followlinks=True):

            lprnt(f"{G}Searching local directory:{R} {root}", up=1)

            # skip hidden dirs
            if root[0] == ".":
                continue

            # record directories that need to be created on remote side
            directory = root.replace(src, "")
            if directory.startswith("/"):
                directory = directory.replace("/", "", 1)
            dst_dirs.append(jn(dst, directory))

            for f in files:
                dst_file = jn(dst, directory, f)

                if not allow_file(dst_file):
                    continue

                copy_files.append({
                    "dst": dst_file,
                    "src": jn(root, f),
                    "size": os.path.getsize(jn(root, f))
                })

        # file number and size statistics
        n_files = len(copy_files)
        total = float(sum([f["size"] for f in copy_files]))

        lprnt(f"\n|--> {C}Total number of files to copy:{R} {n_files}")
        lprnt(f"|--> {C}Total size of files to copy: {R} {b2h(total)}")

        # create directories on remote side to copy to
        lprnt(f"\n{C}Creating directory structure on remote side...")
        for d in dst_dirs:
            self.c.os.makedirs(d, exist_ok=True,
                               quiet=True if quiet else False)

        # copy
        lprnt(f"\n{C}Copying...{R}\n")

        # get lenghts of path strings so when overwriting no artifacts are
        # produced if previous path is longer than new one
        max_src = max([len(c["src"]) for c in copy_files])
        max_dst = max([len(c["dst"]) for c in copy_files])

        q = True if quiet in (True, "progress") else False
        with ProgressBar(total=total, quiet=q) as t:
            for cf in copy_files:

                t.write(f"{G}Copying local:{R} {cf['src']:<{max_src}}\n"
                        f"{G}   --> remote:{R} {self.c.server_name}@"
                        f"{cf['dst']:<{max_dst}}")

                try:
                    self.c.sftp.put(cf["src"], cf["dst"],
                                    callback=t.update_bar)
                except IOError as e:
                    raise IOError(
                        f"The file {cf['src']} could not be copied to "
                        f"{cf['dst']}. This is probably due to permission "
                        f"error: {e}")

        lprnt("")

        if remove_after:
            shutil.rmtree(src)
