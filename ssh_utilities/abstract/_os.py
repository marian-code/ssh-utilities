"""Template module for all os classes and methods."""

import logging
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, FrozenSet, Generic, Optional, TypeVar

if TYPE_CHECKING:
    from ..typeshed import _ONERROR, _SPATH
    from . import _ATTRIBUTES

__all__ = ["OsABC", "DirEntryABC"]

logging.getLogger(__name__)

# Python does not yet support higher order generics so this is devised to
# circumvent the problem, we must always define Generic with all possible
# return types
# problem discussion: https://github.com/python/typing/issues/548
# potentially use returns in the future github.com/dry-python/returns
_Os1 = TypeVar("_Os1")  # "_SCANDIR"
_Os2 = TypeVar("_Os2")  # List[str]
_Os3 = TypeVar("_Os3")  # "_ATTRIBUTES"
_Os4 = TypeVar("_Os4")  # Literal["nt", "posix", "java"]
_Os5 = TypeVar("_Os5")  # OsPathABC
_Os6 = TypeVar("_Os6")  # "_WALK"


class DirEntryABC(ABC):
    """Object representation of directory or a file yielded by `scandir()`.

    Has subset of `Path` object methods.
    """

    @abstractmethod
    def inode(self) -> int:
        """Return the inode number of the entry.

        Returns
        -------
        int
            inode number
        """
        raise NotImplementedError

    @abstractmethod
    def is_dir(self, *, follow_symlinks: bool = True) -> bool:
        """Return True if this entry is a directory.

        Parameters
        ----------
        follow_symlinks : bool, optional
            if we method should follow and resolve symlinks, by default False

        Returns
        -------
        bool
            True if path points to a directory.

        Warnings
        --------
        follow_symlinks is `False` by default in the remote implementation,
        contrary to the implementation in python os library!
        """
        raise NotImplementedError

    @abstractmethod
    def is_file(self, *, follow_symlinks: bool = True) -> bool:
        """Return True if this entry is a file.

        Parameters
        ----------
        follow_symlinks : bool, optional
            if we method should follow and resolve symlinks, by default False

        Returns
        -------
        bool
            True if path points to a file.

        Warnings
        --------
        follow_symlinks is `False` by default in the remote implementation,
        contrary to the implementation in python os library!
        """
        raise NotImplementedError

    @abstractmethod
    def is_symlink(self) -> bool:
        """Return True if this entry is a symlink.

        Returns
        -------
        bool
            true if targer is symlink
        """
        raise NotImplementedError

    @abstractmethod
    def stat(self, *, follow_symlinks: bool = True) -> "_ATTRIBUTES":
        """Return `SFTPAttributes` object similar to `os.stat`.

        Parameters
        ----------
        follow_symlinks : bool, optional
            if we method should follow and resolve symlinks, by default False

        Returns
        -------
        SFTPAttributes
            attributes object for the entry.

        Warnings
        --------
        follow_symlinks is `False` by default in the remote implementation,
        contrary to the implementation in python os library!
        """
        raise NotImplementedError


class OsABC(ABC, Generic[_Os1, _Os2, _Os3, _Os4, _Os5, _Os6]):
    """`os` module drop-in replacement base."""

    __name__: str
    __abstractmethods__: FrozenSet[str]

    @abstractmethod
    def scandir(self, path: "_SPATH") -> _Os1:
        """Return an iterator of os.DirEntry objects.

        These correspond to the entries in the directory given by path.

        Parameters
        ----------
        path : :const:`ssh_utilities.typeshed._SPATH`
            root path directory to scan

        Returns
        -------
        :const:`ssh_utilities.abstract._SCANDIR`
            scandir iterator.
        """
        raise NotImplementedError

    @abstractmethod
    def chmod(self, path: "_SPATH", mode: int, *, dir_fd: Optional[int] = None,
              follow_symlinks: bool = True):
        """Change the mode of path to the numeric mode.

        Parameters
        ----------
        path : :const:`ssh_utilities.typeshed._SPATH`
            path pointing to the file/directory
        mode : int
            desired mode to set, check python `os` documentation to see options
        dir_fd : Optional[int], optional
            not used by ssh implementation, by default None
        follow_symlinks : bool, optional
            whether to resolve symlinks on the way, by default True

        Raises
        ------
        FileNotFoundError
            if the path does not exist
        """
        raise NotImplementedError

    @abstractmethod
    def lchmod(self, path: "_SPATH", mode: int):
        """Change the mode of path to the numeric mode.

        If path is a symlink, this affects the symlink rather than the target.

        Parameters
        ----------
        path : :const:`ssh_utilities.typeshed._SPATH`
            path pointing to the file/directory
        mode : int
            desired mode to set, check python `os` documentation to see options

        Raises
        ------
        FileNotFoundError
            if the path does not exist
        """
        raise NotImplementedError

    @abstractmethod
    def symlink(self, src: "_SPATH", dst: "_SPATH",
                target_is_directory: bool = False, *,
                dir_fd: Optional[int] = None):
        """Make this path a symlink pointing to the given path.

        Parameters
        ----------
        src : :const:`ssh_utilities.typeshed._SPATH`
            target path to which symlink will point
        dst : :const:`ssh_utilities.typeshed._SPATH`
            symlink path
        target_is_directory : bool, optional
            this parameter is ignored in ssh implementation
        dir_fd : Optional[int], optional
            this parameter is ignored in ssh implementation

        Warnings
        --------
        `target_is_directory` parameter is ignored
        """
        raise NotImplementedError

    @abstractmethod
    def remove(self, path: "_SPATH", *, dir_fd: Optional[int] = None):
        """Remove file.

        Parameters
        ----------
        path : :const:`ssh_utilities.typeshed._SPATH`
            path to remove
        dir_fd : Optional[int], optional
            file descriptor, not used in ssh implementation, by default None

        Warnings
        --------
        `dir_fd` parameter is not implemented
        
        Raises
        ------
        FileNotFoundError
            if path does not point to a file
        IsADirectoryError
            if path points to a directory
        IOError
            if some other paramiko related error happens and file could not
            have been removed.
        """
        raise NotImplementedError

    unlink = remove

    @abstractmethod
    def rmdir(self, path: "_SPATH", *, dir_fd: Optional[int] = None):
        """Remove directory.

        Parameters
        ----------
        path : :const:`ssh_utilities.typeshed._SPATH`
            path to remove
        dir_fd : Optional[int], optional
            file descriptor, not used in ssh implementation, by default None

        Warnings
        --------
        `dir_fd` parameter is not implemented

        Raises
        ------
        FileNotFoundError
            if path does not point to a directory
        OSError
            if directory is not empty or some other ssh implementation related
            error occured
        """
        raise NotImplementedError

    @abstractmethod
    def rename(self, src: "_SPATH", dst: "_SPATH", *,
               src_dir_fd: Optional[int] = None,
               dst_dir_fd: Optional[int] = None):
        """Rename the file or directory src to dst.

        Parameters
        ----------
        src : :const:`ssh_utilities.typeshed._SPATH`
            source file or directory
        dst : :const:`ssh_utilities.typeshed._SPATH`
            destination file or directory
        src_dir_fd : Optional[int], optional
            file descriptor, not used in ssh implementation, by default None
        dst_dir_fd : Optional[int], optional
            file descriptor, not used in ssh implementation, by default None

        Warnings
        --------
        `src_dir_fd` parameter is not implemented
        `dst_dir_fd` parameter is not implemented

        Raises
        ------
        FileNotFoundError
            raised on win if destination path exists
        IsADirectoryError
            raised on posix if `src` is file and `dst` is directory
        NotADirectoryError
            raised on posix in `src` is dir and `dst` is file
        IOError
            if some other paramiko related error happens and file could not
            have been removed.
        """
        raise NotImplementedError

    @abstractmethod
    def replace(self, src: "_SPATH", dst: "_SPATH", *,
                src_dir_fd: Optional[int] = None,
                dst_dir_fd: Optional[int] = None):
        """Rename the file or directory src to dst.

        Parameters
        ----------
        src : :const:`ssh_utilities.typeshed._SPATH`
            source file or directory
        dst : :const:`ssh_utilities.typeshed._SPATH`
            destination file or directory
        src_dir_fd : Optional[int], optional
            file descriptor, not used in ssh implementation, by default None
        dst_dir_fd : Optional[int], optional
            file descriptor, not used in ssh implementation, by default None

        Warnings
        --------
        `src_dir_fd` parameter is not implemented
        `dst_dir_fd` parameter is not implemented
        If dst exists and is a file, it will be replaced silently
        if the user has permission.

        Raises
        ------
        FileNotFoundError
            raised on win if destination path exists
        IsADirectoryError
            raised on posix if `src` is file and `dst` is directory
        NotADirectoryError
            raised on posix in `src` is dir and `dst` is file
        IOError
            if some other paramiko related error happens and file could not
            have been removed.  
        """
        raise NotImplementedError

    @abstractmethod
    def makedirs(self, path: "_SPATH", mode: int = 511, exist_ok: bool = True,
                 quiet: bool = True):
        """Recursively create directory.

        If it already exists, show warning and return.

        Parameters
        ----------
        path: :const:`ssh_utilities.typeshed._SPATH`
            path to directory which should be created
        mode: int
            create directory with mode, default is 511
        exist_ok: bool
            if true and directory exists, exception is silently passed when dir
            already exists
        quiet: bool
            if True informative messages are suppresssed

        Raises
        ------
        OSError
            if directory could not be created
        FileExistsError
            when directory already exists and exist_ok=False
        """
        raise NotImplementedError

    @abstractmethod
    def mkdir(self, path: "_SPATH", mode: int = 511, quiet: bool = True):
        """Create single directory.

        If it already exists, show warning and return.

        Parameters
        ----------
        path: :const:`ssh_utilities.typeshed._SPATH`
            path to directory which should be created
        mode: int
            create directory with mode, default is 511
        quiet: bool
            if True informative messages are suppresssed

        Raises
        ------
        OSError
            if directory could not be created
        FileNotFoundError
            when parent directory is missing and parents=False
        """
        raise NotImplementedError

    @abstractmethod
    def listdir(self, path: "_SPATH") -> _Os2:
        """Lists contents of specified directory.

        Parameters
        ----------
        path: :const:`ssh_utilities.typeshed._SPATH`
            directory path

        Returns
        -------
        List[str]
            list  of files, dirs, symlinks ...

        Raises
        ------
        FileNotFoundError
            if directory does not exist
        NotADirectoryError
            if path is not a directory
        """
        raise NotImplementedError

    @abstractmethod
    def chdir(self, path: "_SPATH"):
        """Changes working directory.

        Parameters
        ----------
        path : _SPATH
            directory to change to

        Warnings
        --------
        This is not guaranted to work on all servers. You should avoud this
        method or check if you are in the correct directory.

        Raises
        ------
        FileNotFoundError
            if directory does not exist
        NotADirectoryError
            if path is not a directory
        """
        raise NotImplementedError

    @abstractmethod
    def stat(self, path: "_SPATH", *, dir_fd=None,
             follow_symlinks: bool = True) -> _Os3:
        """Replacement for os.stat function.

        Parameters
        ----------
        path: :const:`ssh_utilities.typeshed._SPATH`
            path to file whose stats are desired
        dir_fd: Any
            not implemented
        follow_symlinks: bool
            whether to resolve symbolic links along the way

        Returns
        -------
        SFTPAttributes
            stat object similar to one returned by `os.stat`

        Warnings
        --------
        `dir_fd` parameter has no effect, it is present only so the signature
        is compatible with `os.stat`
        """
        raise NotImplementedError

    @abstractmethod
    def lstat(self, path: "_SPATH", *, dir_fd=None) -> _Os3:
        """Similar to stat only this does not resolve symlinks.

        Parameters
        ----------
        path: :const:`ssh_utilities.typeshed._SPATH`
            path to file whose stats are desired
        dir_fd: Any
            not implemented in remote version

        Returns
        -------
        SFTPAttributes
            stat object similar to one returned by `os.lstat`

        Warnings
        --------
        `dir_fd` parameter has no effect, it is present only so the signature
        is compatible with `os.lstat`
        """
        raise NotImplementedError

    @property
    @abstractmethod
    def name(self) -> _Os4:
        """Try to get remote os name same as `os.name` function.

        Warnings
        --------
        Due to the complexity of the check, this method only checks is remote
        server is windows by trying to run `ver` command. If that fails the
        remote is automatically assumed to be POSIX which should hold true
        in most cases.
        If absolute certianty is required you should do your own checks.

        Note
        ----
        This methods main purpose is to help choose the right flavour when
        instantiating `ssh_utilities.path.SSHPath`. For its use the provided
        accuracy should be sufficient.

        Returns
        -------
        Literal["nt", "posix"]
            remote server os name

        Raises
        ------
        UnknownOsError
            if remote server os name could not be determined
        """
        raise NotImplementedError

    @property  # type: ignore
    @abstractmethod
    def path(self) -> _Os5:
        raise NotImplementedError

    @path.setter  # type: ignore
    @abstractmethod
    def path(self, path: _Os5):
        raise NotImplementedError

    @abstractmethod
    def walk(self, top: "_SPATH", topdown: bool = True,
             onerror: "_ONERROR" = None, followlinks: bool = False) -> _Os6:
        """Recursive directory listing.

        Parameters
        ----------
        top : :const:`ssh_utilities.typeshed._SPATH`
            directory to start from
        topdown : bool, optional
            if true or not specified, the triple for a directory is generated
            before the triples for any of its subdirectories (directories are
            generated top-down). This enables you to modify the subdirectories
            list in place befor iteration continues. If topdown is False, the
            triple for a directory is generated after the triples for all of
            its subdirectories, by default True
        onerror : :const:`ssh_utilities.typeshed._ONERROR`, optional
            Callable acception one argument of type exception which decides
            how to handle that exception, by default None
        followlinks : bool, optional
            follow symbolic links if true, by default False

        Returns
        -------
        :const:`ssh_utilities.typeshed._WALK`
            iterator of 3 tuples containing current dir, subdirs and files
        """
        raise NotImplementedError

    @staticmethod
    def supports_fd():
        """Check file descriptor support.

        Raises
        ------
        NotImplementedError
            if passing file descriptor is unsupported
        """
        raise NotImplementedError

    @staticmethod
    def supports_dir_fd():
        """Check file descriptor support.

        Raises
        ------
        NotImplementedError
            if passing file descriptor is unsupported
        """
        raise NotImplementedError
