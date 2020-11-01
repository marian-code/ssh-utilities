"""Template module for all connections classes."""
import logging
from abc import ABC, abstractmethod
from os import fspath
from pathlib import Path
from typing import IO, TYPE_CHECKING, List, Optional, Union

from typing_extensions import Literal

if TYPE_CHECKING:
    from os import stat_result
    from subprocess import CompletedProcess as sCP

    from paramiko.sftp_attr import SFTPAttributes

    _ATTRIBUTES = Union[SFTPAttributes, stat_result]

    from .remote.path import SSHPath
    from .utils import CompletedProcess as CP

    CompletedProcess = Union[CP, sCP]
    from paramiko.sftp_file import SFTPFile

    from .typeshed import (_CALLBACK, _CMD, _DIRECTION, _ENV, _FILE, _GLOBPAT,
                           _SPATH)


__all__ = ["ConnectionABC", "OsPathABC", "BuiltinsABC", "OsABC", "ShutilABC",
           "SubprocessABC", "PathlibABC"]

logging.getLogger(__name__)


class OsPathABC(ABC):
    """`os.path` module drop-in replacement base."""

    def realpath(self, path: "_SPATH") -> str:
        raise NotImplementedError


class BuiltinsABC(ABC):
    """Python builtins drop-in replacement base."""

    @abstractmethod
    def open(self, filename: "_SPATH", mode: str = "r",
             encoding: Optional[str] = None,
             bufsize: int = -1, errors: Optional[str] = None
             ) -> Union[IO, "SFTPFile"]:
        raise NotImplementedError


class OsABC(ABC):
    """`os` module drop-in replacement base."""

    @abstractmethod
    def isfile(self, path: "_SPATH") -> bool:
        raise NotImplementedError

    @abstractmethod
    def isdir(self, path: "_SPATH") -> bool:
        raise NotImplementedError

    @abstractmethod
    def makedirs(self, path: "_SPATH", mode: int = 511, exist_ok: bool = True,
                 parents: bool = True, quiet: bool = True):
        raise NotImplementedError

    @abstractmethod
    def mkdir(self, path: "_SPATH", mode: int = 511, quiet: bool = True):
        raise NotImplementedError

    @abstractmethod
    def listdir(self, path: "_SPATH") -> List[str]:
        raise NotImplementedError

    @abstractmethod
    def stat(self, path: "_SPATH", *, dir_fd=None,
             follow_symlinks: bool = True) -> "_ATTRIBUTES":
        raise NotImplementedError

    @abstractmethod
    def lstat(self, path: "_SPATH", *, dir_fd=None) -> "_ATTRIBUTES":
        raise NotImplementedError

    @property
    @abstractmethod
    def name(self) -> Literal["nt", "posix", "java"]:
        raise NotImplementedError

    osname = name

    @property  # type: ignore
    @abstractmethod
    def path(self) -> OsPathABC:
        raise NotImplementedError

    @path.setter  # type: ignore
    @abstractmethod
    def path(self, path: OsPathABC):
        raise NotImplementedError


class ShutilABC(ABC):
    """`shutil` module drop-in replacement base."""

    @abstractmethod
    def copy_files(self, files: List[str], remote_path: "_SPATH",
                   local_path: "_SPATH", *, direction: "_DIRECTION",
                   follow_symlinks: bool = True, quiet: bool = False):
        raise NotImplementedError

    @abstractmethod
    def copyfile(self, src: "_SPATH", dst: "_SPATH", *,
                 direction: "_DIRECTION", follow_symlinks: bool = True,
                 callback: "_CALLBACK" = None, quiet: bool = True):
        raise NotImplementedError

    @abstractmethod
    def copy(self, src: "_SPATH", dst: "_SPATH", *, direction: "_DIRECTION",
             follow_symlinks: bool = True, callback: "_CALLBACK" = None,
             quiet: bool = True):
        raise NotImplementedError

    @abstractmethod
    def copy2(self, src: "_SPATH", dst: "_SPATH", *, direction: "_DIRECTION",
              follow_symlinks: bool = True, callback: "_CALLBACK" = None,
              quiet: bool = True):
        raise NotImplementedError

    @abstractmethod
    def download_tree(self, remote_path: "_SPATH", local_path: "_SPATH",
                      include: "_GLOBPAT" = None, exclude: "_GLOBPAT" = None,
                      remove_after: bool = True, quiet: bool = False):
        raise NotImplementedError

    @abstractmethod
    def upload_tree(self, local_path: "_SPATH", remote_path: "_SPATH",
                    include: "_GLOBPAT" = None, exclude: "_GLOBPAT" = None,
                    remove_after: bool = True, quiet: bool = False):
        raise NotImplementedError

    @abstractmethod
    def rmtree(self, path: "_SPATH", ignore_errors: bool = False,
               quiet: bool = True):
        raise NotImplementedError


class SubprocessABC(ABC):
    """`subprocess` module drop-in replacement base."""

    @abstractmethod
    def run(self, args: "_CMD", *, suppress_out: bool, quiet: bool = True,
            bufsize: int = -1, executable: "_SPATH" = None,
            input: Optional[str] = None, stdin: "_FILE" = None,
            stdout: "_FILE" = None, stderr: "_FILE" = None,
            capture_output: bool = False, shell: bool = False,
            cwd: "_SPATH" = None, timeout: Optional[float] = None,
            check: bool = False, encoding: Optional[str] = None,
            errors: Optional[str] = None, text: Optional[bool] = None,
            env: Optional["_ENV"] = None,
            universal_newlines: bool = False
            ) -> "CompletedProcess":
        raise NotImplementedError


class PathlibABC(ABC):
    """`pathlib` module drop-in replacement base."""

    @abstractmethod
    def Path(self, path: "_SPATH") -> Union[Path, "SSHPath"]:
        raise NotImplementedError


class ConnectionABC(ABC):
    """Class defining API for connection classes."""

    @abstractmethod
    def __str__(self):
        raise NotImplementedError

    @abstractmethod
    def close(self, *, quiet: bool = True):
        raise NotImplementedError

    @abstractmethod
    def ssh_log(self, log_file: Union[Path, str] = Path("paramiko.log"),
                level: str = "WARN"):
        raise NotImplementedError

    @property  # type: ignore
    @abstractmethod
    def builtins(self) -> BuiltinsABC:
        raise NotImplementedError

    @builtins.setter  # type: ignore
    @abstractmethod
    def builtins(self, builtins: BuiltinsABC):
        raise NotImplementedError

    @property  # type: ignore
    @abstractmethod
    def os(self) -> OsABC:
        raise NotImplementedError

    @os.setter  # type: ignore
    @abstractmethod
    def os(self, os: OsABC):
        raise NotImplementedError

    @property  # type: ignore
    @abstractmethod
    def shutil(self) -> ShutilABC:
        raise NotImplementedError

    @shutil.setter  # type: ignore
    @abstractmethod
    def shutil(self, shutil: ShutilABC):
        raise NotImplementedError

    @property  # type: ignore
    @abstractmethod
    def subprocess(self) -> SubprocessABC:
        raise NotImplementedError

    @subprocess.setter  # type: ignore
    @abstractmethod
    def subprocess(self, subprocess: SubprocessABC):
        raise NotImplementedError

    @property  # type: ignore
    @abstractmethod
    def pathlib(self) -> PathlibABC:
        raise NotImplementedError

    @pathlib.setter  # type: ignore
    @abstractmethod
    def pathlib(self, pathlib: PathlibABC):
        raise NotImplementedError

    # * Normal methods ########################################################
    @staticmethod
    def _path2str(path: Optional["_SPATH"]) -> str:
        """Converts pathlib.Path, SSHPath or plain str to string.

        Also remove any rtailing backslashes.

        Parameters
        ----------
        path: "_SPATH"
            path to convert to string, if string is passed,
            then just returns it

        Raises
        ------
        FileNotFoundError
            if path is not instance of str, Path or SSHPath
        """
        if isinstance(path, Path):  # (Path, SSHPath)):
            p = fspath(path)
            return p if not p.endswith("/") else p[:-1]
        elif isinstance(path, str):
            return path if not path.endswith("/") else path[:-1]
        else:
            raise FileNotFoundError(f"{path} is not a valid path")

    @staticmethod
    def to_str(connection_name: str, host_name: str, address: Optional[str],
               user_name: str, ssh_key: Optional[Union[Path, str]],
               thread_safe: bool) -> str:
        """Aims to ease persistance, returns string representation of instance.

        With this method all data needed to initialize class are saved to sting
        and connection can be reinitialized with from_str method of
        `conection.Connection` class.

        Parameters
        ----------
        connection_name : str
            SSHConnection or LocalConnection
        host_name : str
            name of remote server
        address : str
            server address in case of remote connection
        user_name : str
            server login name
        ssh_key : Optional[Union[Path, str]]
            file with public key, pass none for LocalConnection
        thread_safe: bool
            make connection object thread safe so it can be safely accessed
            from  any number of threads, it is disabled by default to avoid
            performance  penalty of threading locks

        Returns
        -------
        str
            string representation of the class

        See Also
        --------
        :class:`ssh_utilities.conncection.Connection`
        """
        if ssh_key is None:
            key_path = ssh_key
        else:
            key_path = str(Path(ssh_key).resolve())
        return (f"<{connection_name}:{host_name}>("
                f"user_name:{user_name} | "
                f"rsa_key:{key_path} | "
                f"address:{address} | "
                f"threadsafe:{thread_safe})")

    def __del__(self):
        self.close(quiet=True)
