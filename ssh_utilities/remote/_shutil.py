"""Module collecting shutil-like remote methods."""

import logging
import os
import shutil
from os.path import join as jn
from stat import S_ISDIR, S_ISLNK
from typing import TYPE_CHECKING, List

from typing_extensions import Literal

from ..base import ShutilABC
from ..constants import LG, C, G, R
from ..utils import ProgressBar
from ..utils import bytes_2_human_readable as b2h
from ..utils import context_timeit, file_filter, lprint
from ._connection_wrapper import check_connections

if TYPE_CHECKING:
    from typing_extensions import TypedDict

    from ..typeshed import _CALLBACK, _DIRECTION, _GLOBPAT, _SPATH, _WALK
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
        """Send files in the chosen direction local <-> remote.

        Parameters
        ----------
        files: List[str]
            list of files to upload/download
        remote_path: "_SPATH"
            path to remote directory with files
        local_path: "_SPATH"
            path to local directory with files
        direction: str
            get for download and put for upload
        quiet: bool
            if True informative messages are suppresssed
        """
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
        """Send files in the chosen direction local <-> remote.

        Parameters
        ----------
        src: "_SPATH"
            path to the file
        dst: "_SPATH"
            path to copy into
        direction: str
            'get' for download and 'put' for upload
        follow_symlinks: bool
            resolve symlinks when looking for file, by default True
        callback: Callable[[float, float], Any]
            callback function that recives two arguments: amount done and total
            amount to be copied
        quiet: bool
            if True informative messages are suppresssed

        Raises
        ------
        FileNotFoundError
            if `src` is not file
        IsADirectoryError
            if dst is a targer directory not full path
        ValueError
            if direction is not `put` or `get`
        """
        def _dummy_callback(_1: float, _2: float):
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
        """Send files in the chosen direction local <-> remote.

        Parameters
        ----------
        src: "_SPATH"
            path to the file
        dst: "_SPATH"
            path to copy into
        direction: str
            'get' for download and 'put' for upload
        follow_symlinks: bool
            resolve symlinks when looking for file, by default True
        callback: Callable[[float, float], Any]
            callback function that recives two arguments: amount done and total
            amount to be copied
        quiet: bool
            if True informative messages are suppresssed

        Warnings
        --------
        Unlike shutil this function cannot preserve file permissions (`copy`)
        or file metadata (`copy2`)

        Raises
        ------
        FileNotFoundError
            if `src` is not file
        ValueError
            if direction is not `put` or `get`
        """
        if direction == "get":
            if os.path.isdir(self.c._path2str(dst)):
                dst = jn(dst, os.path.basename(self.c._path2str(src)))

        elif direction == "put":
            if self.c.os.isdir(dst):
                dst = jn(dst, os.path.basename(self.c._path2str(src)))

        self.copyfile(src, dst, direction=direction,
                      follow_symlinks=follow_symlinks, callback=callback,
                      quiet=quiet)

    copy2 = copy

    @check_connections(exclude_exceptions=FileNotFoundError)
    def rmtree(self, path: "_SPATH", ignore_errors: bool = False,
               quiet: bool = True):
        """Recursively remove directory tree.

        Parameters
        ----------
        path: "_SPATH"
            directory to be recursively removed
        ignore_errors: bool
            if True only log warnings do not raise exception
        quiet: bool
            if True informative messages are suppresssed

        Raises
        ------
        FileNotFoundError
            if some part of deleting filed
        """
        sn = self.c.server_name
        path = self.c._path2str(path)

        with context_timeit(quiet):
            lprint(quiet)(f"{G}Recursively removing dir:{R} {sn}@{path}")

            try:
                for root, _, files in self._sftp_walk(path):
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
        """Download directory tree from remote.

        Remote directory must exist otherwise exception is raised.

        Parameters
        ----------
        remote_path: "_SPATH"
            path to directory which should be downloaded
        local_path: "_SPATH"
            directory to copy to, must be full path!
        remove_after: bool
            remove remote copy after directory is uploaded
        include: _GLOBPAT
            glob pattern of files to include in copy, can be used
            simultaneously with exclude, default is None = no filtering
        exclude: _GLOBPAT
            glob pattern of files to exclude in copy, can be used
            simultaneously with include, default is None = no filtering
        quiet:  Literal[True, False, "stats", "progress"]
            if `True` informative messages are suppresssed if `False` all is
            printed, if `stats` all statistics except progressbar are
            suppressed if `progress` only progressbar is suppressed

        Warnings
        --------
        both paths must be full: <some_remote_path>/my_directory ->
        <some_local_path>/my_directory

        Raises
        ------
        FileNotFoundError
            when remote directory does not exist
        """
        dst = self.c._path2str(local_path)
        src = self.c._path2str(remote_path)

        if not self.c.os.isdir(remote_path):
            raise FileNotFoundError(f"{remote_path} you are trying to download"
                                    f"from does not exist")

        lprnt = lprint(quiet=True if quiet or quiet == "stats" else False)
        allow_file = file_filter(include, exclude)

        copy_files: List["_COPY_FILES"] = []
        dst_dirs = []

        lprnt(f"{C}Building directory structure for download from remote...\n")

        # create a list of directories and files to copy
        for root, _, files in self._sftp_walk(src):

            lprnt(f"{G}Searching remote directory:{R} "
                  f"{self.c.server_name}@{root}", up=1)

            # record directories that need to be created on local side
            directory = root.replace(src, "")
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

        q = True if quiet or quiet == "progress" else False
        with ProgressBar(total=total, quiet=q) as t:
            for f in copy_files:

                t.write(f"{G}Copying remote:{R} {self.c.server_name}@"
                        f"{f['src']:<{max_src}}"
                        f"\n{G}     --> local:{R} {f['dst']:<{max_dst}}")

                self.c.sftp.get(f["src"], f["dst"], callback=t.update_bar)

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
        """Upload directory tree to remote.

        Local path must exist otherwise, exception is raised.

        Parameters
        ----------
        local_path: "_SPATH"
            path to directory which should be uploaded
        remote_path: "_SPATH"
            directory to copy to, must be full path!
        remove_after: bool
            remove local copy after directory is uploaded
        include: _GLOBPAT
            glob pattern of files to include in copy, can be used
            simultaneously with exclude, default is None = no filtering
        exclude: _GLOBPAT
            glob pattern of files to exclude in copy, can be used
            simultaneously with include, default is None = no filtering
        quiet:  Literal[True, False, "stats", "progress"]
            if `True` informative messages are suppresssed if `False` all is
            printed, if `stats` all statistics except progressbar are
            suppressed if `progress` only progressbar is suppressed

        Warnings
        --------
        both paths must be full: <some_local_path>/my_directory ->
        <some_remote_path>/my_directory

        Raises
        ------
        FileNotFoundError
            when local directory does not exist
        """
        src = self.c._path2str(local_path)
        dst = self.c._path2str(remote_path)

        if not os.path.isdir(local_path):
            raise FileNotFoundError(f"{local_path} you are trying to upload "
                                    f"does not exist")

        lprnt = lprint(quiet=True if quiet or quiet == "stats" else False)
        allow_file = file_filter(include, exclude)

        copy_files: List["_COPY_FILES"] = []
        dst_dirs = []

        lprnt(f"{C}Building directory structure for upload to remote...\n")

        # create a list of directories and files to copy
        for root, _, files in os.walk(src):

            lprnt(f"{G}Searching local directory:{R} {root}", up=1)

            # skip hidden dirs
            if root[0] == ".":
                continue

            # record directories that need to be created on remote side
            directory = root.replace(src, "")
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
            self.c.os.makedirs(d, exist_ok=True, quiet=quiet)

        # copy
        lprnt(f"\n{C}Copying...{R}\n")

        # get lenghts of path strings so when overwriting no artifacts are
        # produced if previous path is longer than new one
        max_src = max([len(c["src"]) for c in copy_files])
        max_dst = max([len(c["dst"]) for c in copy_files])

        q = True if quiet or quiet == "progress" else False
        with ProgressBar(total=total, quiet=q) as t:
            for cf in copy_files:

                t.write(f"{G}Copying local:{R} {cf['src']:<{max_src}}\n"
                        f"{G}   --> remote:{R} {self.c.server_name}@"
                        f"{cf['dst']:<{max_dst}}")

                self.c.sftp.put(cf["src"], cf["dst"], callback=t.update_bar)

        lprnt("")

        if remove_after:
            shutil.rmtree(src)

    @check_connections()
    def _sftp_walk(self, remote_path: "_SPATH") -> "_WALK":
        """Recursive directory listing."""
        remote_path = self.c._path2str(remote_path)
        path = remote_path
        files = []
        folders = []
        for f in self.c.sftp.listdir_attr(remote_path):
            # if is symlink get real files and check its stats
            if S_ISLNK(f.st_mode):
                s = self.c.os.stat(jn(remote_path, f.filename))
                if S_ISDIR(s.st_mode):
                    folders.append(f.filename)
                else:
                    files.append(f.filename)
            elif S_ISDIR(f.st_mode):
                folders.append(f.filename)
            else:
                files.append(f.filename)

        yield path, folders, files

        for folder in folders:
            new_path = jn(remote_path, folder)
            for x in self._sftp_walk(new_path):
                yield x
