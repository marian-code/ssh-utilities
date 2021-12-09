"""Module collecting shutil-like remote methods."""

import errno
import logging
import os
import shutil
import stat
import sys
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
                raise IsADirectoryError(
                    errno.EISDIR,
                    "dst argument must be full path not a directory",
                    dst_str
                )

            if follow_symlinks:
                src_str = self.c.os.path.realpath(src_str)
                dst_str = os.path.realpath(dst_str)

            try:
                self.c.sftp.get(src_str, dst_str, callback)
            except IOError as e:
                raise FileNotFoundError(
                    errno.ENOENT, str(e), src_str
                )

        elif direction == "put":
            lprnt(f"{G}Copying from local:{R} {src}\n"
                  f"{LG} -->       remote: {self.c.server_name}@{dst}")

            if self.c.os.path.isdir(dst_str):
                raise IsADirectoryError(
                    errno.EISDIR,
                    "dst argument must be full path not a directory",
                    dst_str,
                )

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

    # TODO
    @check_connections(exclude_exceptions=shutil.Error)
    def copytree(self, src: "_SPATH", dst: "_SPATH",
                 direction: "_DIRECTION", symlinks: bool = False,
                 ignore: Optional[Callable[["_SPATH"], bool]] = None,
                 copy_function: Callable[["_SPATH", "_SPATH", bool], NoReturn] = "copy2",
                 ignore_dangling_symlinks: bool = False,
                 dirs_exist_ok: bool = False):

        sys.audit("ssh_utilities.shutil.copytree", src, dst)
        with self.c.os.scandir(src) as itr:
            entries = list(itr)
        return self._copytree(
            entries=entries, src=src, dst=dst, direction=direction,
            symlinks=symlinks, ignore=ignore, copy_function=copy_function,
            ignore_dangling_symlinks=ignore_dangling_symlinks,
            dirs_exist_ok=dirs_exist_ok)
        
    def _copytree(self, entries, src, dst, direction, symlinks, ignore,
                  copy_function, ignore_dangling_symlinks,
                  dirs_exist_ok=False):

        if ignore is not None:
            ignored_names = ignore(self.c._path2str(src), [x.name for x in entries])
        else:
            ignored_names = set()

        self.c.os.makedirs(dst, exist_ok=dirs_exist_ok)
        errors = []
        use_srcentry = copy_function is self.copy2 or copy_function is self.copy

        for srcentry in entries:
            if srcentry.name in ignored_names:
                continue
            srcname = self.c.os.path.join(src, srcentry.name)
            dstname = self.c.os.path.join(dst, srcentry.name)
            srcobj = srcentry if use_srcentry else srcname
            try:
                is_symlink = srcentry.is_symlink()
                if is_symlink and self.c.os.name == 'nt':
                    # Special check for directory junctions, which appear as
                    # symlinks but we want to recurse.
                    lstat = srcentry.stat(follow_symlinks=False)
                    if lstat.st_reparse_tag == stat.IO_REPARSE_TAG_MOUNT_POINT:
                        is_symlink = False
                if is_symlink:
                    # TODO 
                    linkto = os.readlink(srcname)
                    if symlinks:
                        # We can't just leave it to `copy_function` because legacy
                        # code with a custom `copy_function` may rely on copytree
                        # doing the right thing.
                        self.c.os.symlink(linkto, dstname)
                    else:
                        # ignore dangling symlink if the flag is on
                        if not os.path.exists(linkto) and ignore_dangling_symlinks:
                            continue
                        # otherwise let the copy occur. copy2 will raise an error
                        if srcentry.is_dir():
                            self.copytree(srcobj, dstname, direction, symlinks,
                                          ignore, copy_function,
                                          dirs_exist_ok=dirs_exist_ok)
                        else:
                            copy_function(srcobj, dstname)
                elif srcentry.is_dir():
                    self.copytree(srcobj, dstname, direction, symlinks, ignore,
                                  copy_function, dirs_exist_ok=dirs_exist_ok)
                else:
                    # Will raise a SpecialFileError for unsupported file types
                    copy_function(srcobj, dstname)
            # catch the Error from the recursive copytree so that we can
            # continue with other files
            except shutil.Error as err:
                errors.extend(err.args[0])
            except OSError as why:
                errors.append((srcname, dstname, str(why)))

        if errors:
            raise shutil.Error(errors)
        return dst

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
                        except OSError as e:  # catches also FileNotFoundError
                            if ignore_errors:
                                log.warning("File does not exist")
                            else:
                                raise FileNotFoundError(
                                    errno.ENOENT, str(e), f
                                ) from e
                if self.c.os.path.isdir(root):
                    try:
                        self.c.os.rmdir(root)
                    except OSError as e:  # catches also FileNotFoundError
                        if ignore_errors:
                            log.warning("Directory does not exist")
                        else:
                            raise FileNotFoundError(
                                    errno.ENOENT, str(e), root
                                ) from e

            if self.c.os.path.isdir(path):
                self.c.sftp.rmdir(path)

    # TODO collect errors and raise at the end
    # TODO should raise shutil error
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
            raise FileNotFoundError(
                errno.ENOENT, os.strerror(errno.ENOENT), remote_path
            )

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
                        f"error: {e}") from e

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
            raise FileNotFoundError(
                errno.ENOENT, os.strerror(errno.ENOENT), local_path
            )

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
