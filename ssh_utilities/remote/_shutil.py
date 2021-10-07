"""Module collecting shutil-like remote methods."""

import logging
import os
import shutil
from typing import (IO, TYPE_CHECKING, Any, Callable, List, NoReturn, Optional,
                    Sequence, Set, Union)

try:
    from typing import Literal  # type: ignore - python >= 3.8
except ImportError:
    from typing_extensions import Literal  # python < 3.8

from ..abstract import ShutilABC
from ..constants import LG, C, G, R
from ..utils import ProgressBar
from ..utils import bytes_2_human_readable as b2h
from ..utils import context_timeit, deprecation_warning, file_filter, lprint
from ._connection_wrapper import check_connections

if TYPE_CHECKING:
    from paramiko.sftp_file import SFTPFile

    try:
        from typing import TypedDict  # type: ignore - python >= 3.8
    except ImportError:
        from typing_extensions import TypedDict  # python < 3.8

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

    def ignore_patterns(self, *paterns: Sequence[str]
                        ) -> Callable[[Any, Sequence[str]], Set[str]]:
        return file_filter(None, exclude=paterns)

    @check_connections
    def copyfileobj(self, fsrc: Union[IO, "SFTPFile"], fdst: Union[IO, "SFTPFile"], *,
                    direction: "_DIRECTION", length: Optional[int] = None):

        # faster but any errors will be thrown only at file close
        if isinstance(fsrc, SFTPFile):
            fsrc.set_pipelined(True)
        if isinstance(fdst, SFTPFile):
            fdst.set_pipelined(True)

        if length is None:
            length = 32768

        if length < 0:
            fdst.write(fsrc.read())
        else:
            while True:
                data = fsrc.read(length)
                fdst.write(data)
                if len(data) == 0:
                    break

    @deprecation_warning("copyfile",
                         "With for-loop you can archieve the same effect")
    @check_connections(exclude_exceptions=ValueError)
    def copy_files(self, files: List[str], remote_path: "_SPATH",
                   local_path: "_SPATH", *, direction: "_DIRECTION",
                   follow_symlinks: bool = True, quiet: bool = False):

        with context_timeit(quiet):
            for f in files:
                if direction == "get":
                    src = self.c.os.path.join(self.c._path2str(remote_path), f)
                    dst = self.c.os.path.join(self.c._path2str(local_path), f)
                elif direction == "put":
                    dst = self.c.os.path.join(self.c._path2str(remote_path), f)
                    src = self.c.os.path.join(self.c._path2str(local_path), f)
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
        src_str = self.c._path2str(src)
        dst_str = self.c._path2str(dst)

        if direction == "get":
            lprnt(f"{G}Copying from remote:{R} {self.c.server_name}@{src}{LG}"
                  f"\n-->           local:{R} {dst}")

            if os.path.isdir(dst_str):
                raise IsADirectoryError("dst argument must be full path "
                                        "not a directory")

            if follow_symlinks:
                src_str = self.c.os.path.realpath(src_str)
                dst_str = os.path.realpath(dst_str)

            try:
                self.c.sftp.get(src_str, dst_str, callback)
            except IOError as e:
                raise FileNotFoundError(f"File you are trying to get "
                                        f"does not exist: {e}")

        elif direction == "put":
            lprnt(f"{G}Copying from local:{R} {src}\n"
                  f"{LG} -->       remote: {self.c.server_name}@{dst}")

            if self.c.os.path.isdir(dst_str):
                raise IsADirectoryError("dst argument must be full path "
                                        "not a directory")

            if follow_symlinks:
                src_str = os.path.realpath(src_str)
                dst_str = self.c.os.path.realpath(dst_str)

            self.c.sftp.put(src_str, dst_str, callback)
        else:
            raise ValueError(f"{direction} is not valid direction. "
                             f"Choose 'put' or 'get'")

    def copy(self, src: "_SPATH", dst: "_SPATH", *, direction: "_DIRECTION",
             follow_symlinks: bool = True, callback: "_CALLBACK" = None,
             quiet: bool = True):

        dst = self.c._path2str(dst)
        src = self.c._path2str(src)

        if direction == "get":
            if os.path.isdir(dst):
                dst = self.c.os.path.join(dst, os.path.basename(src))

        elif direction == "put" and self.c.os.path.isdir(dst):
            dst = self.c.os.path.join(dst, os.path.basename(src))

        self.copyfile(src, dst, direction=direction,
                      follow_symlinks=follow_symlinks, callback=callback,
                      quiet=quiet)

    copy2 = copy

    def copytree(self, src: "_SPATH", dst: "_SPATH", symlinks: bool = False,
                 ignore: Optional[Callable[["_SPATH"], bool]] = None,
                 copy_function: Callable[["_SPATH", "_SPATH", bool], NoReturn] = "copy2",
                 ignore_dangling_symlinks: bool = False,
                 dirs_exist_ok: bool = False):
        raise NotImplementedError

    @check_connections(exclude_exceptions=(FileNotFoundError, OSError))
    def rmtree(self, path: "_SPATH", ignore_errors: bool = False,
               quiet: bool = True):

        sn = self.c.server_name
        path = self.c._path2str(path)

        with context_timeit(quiet):
            lprint(quiet)(f"{G}Recursively removing dir:{R} {sn}@{path}")

            for root, _, files in self.c.os.walk(path, followlinks=True):
                for f in files:
                    f = self.c.os.path.join(root, f)
                    lprint(quiet)(f"{G}removing file:{R} {sn}@{f}")
                    if self.c.os.path.isfile(f):
                        try:
                            self.c.os.unlink(f)
                        except (FileNotFoundError, OSError) as e:
                            if ignore_errors:
                                log.warning("File does not exist")
                            else:
                                raise FileNotFoundError(str(e)) from e
                if self.c.os.path.isdir(root):
                    try:
                        self.c.os.rmdir(root)
                    except (FileNotFoundError, OSError) as e:
                        if ignore_errors:
                            log.warning("Directory does not exist")
                        else:
                            raise FileNotFoundError(str(e)) from e

            if self.c.os.path.isdir(path):
                self.c.sftp.rmdir(path)

    # TODO collect errors and raise at the end
    @check_connections(exclude_exceptions=(FileNotFoundError, OSError))
    def download_tree(
        self, remote_path: "_SPATH", local_path: "_SPATH",
        include: "_GLOBPAT" = None, exclude: "_GLOBPAT" = None,
        remove_after: bool = False,
        quiet: Literal[True, False, "stats", "progress"] = False
    ):

        dst = self.c._path2str(local_path)
        src = self.c._path2str(remote_path)

        if not self.c.os.path.isdir(remote_path):
            raise FileNotFoundError(f"{remote_path} you are trying to download"
                                    f"from does not exist")

        lprnt = lprint(quiet=True if quiet in (True, "stats") else False)
        ignore_files = file_filter(include, exclude)

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
                directory = directory.replace("/", "", 1)
            dst_dirs.append(self.c.os.path.join(dst, directory))

            skip_files = ignore_files("", files)

            for f in files:
                if f in skip_files:
                    continue

                dst_file = self.c.os.path.join(dst, directory, f)

                if quiet:
                    size = 0
                else:
                    # TODO implement getsize !!
                    size = self.c.os.lstat(self.c.os.path.join(root, f)).st_size
                    if size is None:
                        size = 0

                copy_files.append({
                    "dst": dst_file,
                    "src": self.c.os.path.join(root, f),
                    "size": size
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
        # move additional row because progressbar moves one up by default
        if not q:
            print("\n")
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
            self.rmtree(src, quiet=q)

    @check_connections(exclude_exceptions=(FileNotFoundError, OSError))
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
        ignore_files = file_filter(include, exclude)

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
            dst_dirs.append(self.c.os.path.join(dst, directory))

            skip_files = ignore_files("", files)

            for f in files:
                if f in skip_files:
                    continue

                dst_file = self.c.os.path.join(dst, directory, f)

                if quiet:
                    size = 0
                else:
                    size = os.path.getsize(self.c.os.path.join(root, f))
                    if size is None:
                        size = 0

                copy_files.append({
                    "dst": dst_file,
                    "src": self.c.os.path.join(root, f),
                    "size": size
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
        # move additional row because progressbar moves one up by default
        if not q:
            print("\n")
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
