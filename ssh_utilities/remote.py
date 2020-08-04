"""Module implementing SSH connection functionality."""

import logging
import os
import shutil
import time
from functools import wraps
from os.path import join as jn
from pathlib import Path
from stat import S_ISDIR, S_ISREG
from types import MethodType
from typing import TYPE_CHECKING, Callable, List, Optional, Tuple, Type, Union

import paramiko
from typing_extensions import Literal

from .base import ConnectionABC
from .constants import LG, RED, C, G, R, Y
from .exceptions import (CalledProcessError, ConnectionError, SFTPOpenError,
                         UnknownOsError)
from .path import SSHPath
from .utils import CompletedProcess, ProgressBar
from .utils import bytes_2_human_readable as b2h
from .utils import context_timeit, file_filter, lprint

if TYPE_CHECKING:
    SPath = Union[str, Path, SSHPath]
    ExcType = Union[Type[Exception], Tuple[Type[Exception], ...]]
    from paramiko.sftp_file import SFTPFile
    from paramiko.sftp_client import SFTPClient
    GlobPat = Optional[str]

__all__ = ["SSHConnection"]

LOGGER = logging.getLogger(__name__)


def _check_connections(original_function: Optional[Callable] = None, *,
                       exclude_exceptions: "ExcType" = ()):
    """A decorator to check SSH connections.

    If connection is dropped while running function, re-negotiate new
    connection and run function again.

    Parameters
    ----------
    original_function: Callable
        function to watch for dropped connections
    exclude_exceptions: Tuple[Exception]
        tuple of exceptions not to catch

    Raises
    ------
    Exception
        Any exception that is not specified in the wrapper when it is thrown
        in the decorated method
    exclude_exceptions
        Any exception specified in this list when it is thrown
        in the decorated method

    Warnings
    --------
    Beware, this function can hide certain errors or cause the code to become
    stuck in an infinite loop!

    References
    ----------
    https://stackoverflow.com/questions/3888158/making-decorators-with-optional-arguments

    Examples
    --------
    First use cases is without arguments:

    >>> @_check_connections
    ... def function(*args, **kwargs):

    Second possible use cases is with arguments:

    >>> @_check_connections(exclude_exceptions=(<Exception>, ...))
    ... def function(*args, **kwargs):
    """
    def _decorate(function):

        @wraps(function)
        def connect_wrapper(self, *args, **kwargs):

            def negotiate() -> bool:
                try:
                    self.close(quiet=True)
                except Exception as e:
                    LOGGER.exception(f"Couldn't close connection: {e}")

                try:
                    self._get_ssh()
                except ConnectionError:
                    success = False
                else:
                    success = True

                LOGGER.debug(f"success 1: {success}")
                if not success:
                    return False

                if self._sftp_open:
                    LOGGER.debug(f"success 2: {success}")
                    try:
                        self.sftp
                    except SFTPOpenError:
                        success = False
                        LOGGER.debug(f"success 3: {success}")

                    else:
                        LOGGER.debug(f"success 4: {success}")

                        success = True
                else:
                    success = False

                LOGGER.exception(f"Relevant variables:\n"
                                 f"success:    {success}\n"
                                 f"password:   {self.password}\n"
                                 f"address:    {self.address}\n"
                                 f"username:   {self.username}\n"
                                 f"ssh class:  {type(self._c)}\n"
                                 f"sftp class: {type(self.sftp)}")
                if self._sftp_open:
                    LOGGER.exception(f"remote home: {self.remote_home}")

                return success

            n = function.__name__
            error = None
            try:
                return function(self, *args, **kwargs)
            except exclude_exceptions as e:
                # if exception is one of the excluded, re-raise it
                raise e from None
            except paramiko.ssh_exception.NoValidConnectionsError as e:
                error = e
                LOGGER.exception(f"Caught paramiko error in {n}: {e}")
            except paramiko.ssh_exception.SSHException as e:
                error = e
                LOGGER.exception(f"Caught paramiko error in {n}: {e}")
            except AttributeError as e:
                error = e
                LOGGER.exception(f"Caught attribute error in {n}: {e}")
            except OSError as e:
                error = e
                LOGGER.exception(f"Caught OS error in {n}: {e}")
            except paramiko.SFTPError as e:
                # garbage packets,
                # see: https://github.com/paramiko/paramiko/issues/395
                LOGGER.exception(f"Caught paramiko error in {n}: {e}")
            finally:
                while error:

                    LOGGER.warning("Connection is down, trying to reconnect")
                    if negotiate():
                        LOGGER.info("Connection restablished, continuing ..")
                        connect_wrapper(self, *args, **kwargs)
                        break
                    else:
                        LOGGER.warning("Unsuccessful, wait 60 seconds "
                                       "before next try")
                        time.sleep(60)

        return connect_wrapper

    if original_function:
        return _decorate(original_function)

    return _decorate


# ! this is not a viable way too complex logic
# use locking decorator instead
# TODO share_connection could be implemented with dict
# - must be indexable, need to remember which class uses which connection
# - must store both sftp and connection
# - must remove the element from the dataframe so no one can access it
"""
from threading import Condition, Lock


class ConnectionHolder:

    _connections = dict()
    _lock = Lock()
    _max_connections = 10

    @classmethod
    def get(cls, ip: str, instance_id):

        with cls._lock:
            if getattr(cls, f"{ip}:{instance_id}", None):
                getattr(cls, f"{ip}:{instance_id}").wait()
            conn = cls._connections[ip][iid].pop()
            setattr(cls, f"{ip}:{instance_id}", conn["cond"])

        pass

    @classmethod
    def put(cls, conn: dict):
        pass

    @classmethod
    def new(cls, ip: str, instance_id: Optional[str]):
        cls._lock.acquire()

        if ip in cls._connections:

            # None only when creating completely new class,
            # is known when reconnecting
            if not instance_id:
                for iid in cls._conditions.values():
                    if iid["count"] < cls._max_connections:
                        # some id has free connections
                        # just increment counter
                        cls._connections[ip][idd]["count"] += 1
                        return iid
                else:
                    # no id has free connections
                    iid = cls._get_unique_instance_id()
                    # TODO get connection somehow
                    cls._connections[ip] = {iid: {"conn": None,
                                                  "count": 1,
                                                  "cond": Condition()}}
                    return iid

            else:
                # only reopening downed connection
                # TODO get connection somehow
                cls._connections[ip][instance_id]["conn"] = None
                return instance_id
        else:
            iid = cls._get_unique_instance_id()
            # TODO get connection somehow
            cls._connections[ip] = {iid: {"conn": None,
                                          "count": 1,
                                          "cond": Condition()}}

        cls._lock.release()

    @classmethod
    def _get_unique_instance_id(cls):
        raise NotImplementedError
"""


# TODO implement warapper for multiple connections
class SSHConnection(ConnectionABC):
    """Self keeping ssh connection, to execute commands and file operations.

    Parameters
    ----------
    address: str
        server IP address
    username: str
        server login
    password: Optional[str]
        server password for login, by default RSA keys is used
    rsa_key_file: Optional[Union[str, Path]]
        path to rsa key file
    line_rewrite: bool
        rewrite lines in output when copying instead of normal mode when lines
        are outputed one after the other. Default is True
    warn_on_login: bool
        Display on warnings of firs login
    server_name: Optional[str]
        input server name that will be later displayed on file operations,
        if None then IP address will be used
    logger: Logger
        python logger instance that will be used for logging else, new Logger
        instance will be created
    share_connection: int
        share connection between different instances of class, number says
        how many instances can share the same connection

    Warnings
    --------
    At least one of (password, rsa_key_file) must be specified, if both are,
    RSA key will be used

    share_connection parameter is not implemented yet!!!

    Raises
    ------
    ConnectionError
        connection to remote could not be established
    """

    log: logging.Logger
    _remote_home: str = ""
    _osname: Literal["nt", "posix", ""] = ""

    def __init__(self, address: str, username: str,
                 password: Optional[str] = None,
                 rsa_key_file: Optional[Union[str, Path]] = None,
                 line_rewrite: bool = True, warn_on_login: bool = False,
                 server_name: Optional[str] = None,
                 logger: logging.Logger = None,
                 share_connection: int = 10) -> None:

        print(f"{C}Connecting to server:{R} {username}@{address}"
              f"{' (' + server_name + ')' if server_name else ''}")
        if warn_on_login:
            print(f"{R}When running an executale on server always make"
                  f"sure that full path is specified!!!\n")

        self.log = logger if logger else LOGGER

        # set login credentials
        self.password = password
        self.address = address
        self.username = username
        self.rsa_key_file = rsa_key_file

        # paramiko connection
        if rsa_key_file:
            self.rsa_key = paramiko.RSAKey.from_private_key_file(
                self._path2str(rsa_key_file))
        elif password:
            self.rsa_key = None
        else:
            raise RuntimeError("Must input password or path to rsa_key")

        self._c = paramiko.client.SSHClient()
        self._c.set_missing_host_key_policy(paramiko.client.AutoAddPolicy())

        # negotiate connection
        self._get_ssh()

        # misc
        self._sftp_open = False
        lprint.line_rewrite = line_rewrite
        self.server_name = server_name.upper() if server_name else address

        self.local = False

    def __str__(self) -> str:
        return self.to_str("SSHConnection", self.server_name, self.address,
                           self.username, self.rsa_key_file)

    @_check_connections
    def close(self, *, quiet: bool):
        """Close SSH connection.

        Parameters
        ----------
        quiet: bool
            whether to print other function messages
        """
        lprint(quiet)(f"{G}Closing ssh connection to:{R} {self.server_name}")
        self._c.close()

    @staticmethod
    def ssh_log(log_file: Union[Path, str] = Path("paramiko.log"),
                level: str = "WARN"):
        """Initialize paramiko logging functionality.

        Parameters
        ----------
        log_file: str
            location of the log file (default: paramiko.log)
        level: str
            logging level represented by string
        """
        if os.path.isfile(log_file):
            os.remove(log_file)
        lprint()(f"{Y}Logging ssh session to file:{R} {log_file}\n")
        paramiko.util.log_to_file(log_file, level=level)

    @_check_connections(exclude_exceptions=(TypeError, CalledProcessError))
    def run(self, args: List[str], *, suppress_out: bool, quiet: bool = True,
            capture_output: bool = False, check: bool = False,
            cwd: Optional[Union[str, Path]] = None, encoding: str = "utf-8"
            ) -> CompletedProcess:
        """Excecute command on remote, has simillar API to subprocess run.

        Parameters
        ----------
        args: List[str]
            command as a list all parts shoul be separate list entries
        suppress_out: bool
            whether to print command output to console, this is required
            keyword argument
        quiet: bool
            whether to print other function messages
        capture_output: bool
            if true then lightweight result object with
            same API as subprocess.CompletedProcess is returned
        cwd: Optional[Union[str, Path]]
            execute command in this directory
        check: bool
            checks for command return code if other than 0 raises
            CalledProcessError
        encoding: str
            encoding to use when decoding remote output, default is utf-8

        Raises
        ------
        TypeError
            if command arguments are of wrong type
        CalledProcessError
            if check is true and command exited with non-zero status

        Returns
        -------
        Optional[CompletedProcess]
            if capture_output is true, returns lightweight result object with
            same API as subprocess.CompletedProcess
        """
        if isinstance(args, str):
            raise TypeError("command must be of type list")

        # init limited printing
        lprnt = lprint(quiet=quiet)
        command: str = " ".join(args)

        commands = command.split(" && ")
        if len(commands) == 1:
            lprnt(f"{Y}Executing command on remote:{R} {command}\n")
        else:
            lprnt(f"{Y}Executing commands on remote:{R} {commands[0]}")
            for c in commands[1:]:
                lprnt(" " * 30 + c)

        # change work directory for command execution
        if cwd:
            command = f"cd {self._path2str(cwd)} && {command}"

        # carry out command
        # stdin, stdout, stderr
        stdout, stderr = self._c.exec_command(command)[1:]

        if capture_output:
            # create output object
            out = CompletedProcess()
            out.args = args

            # loop until channels are exhausted
            while (not stdout.channel.exit_status_ready() and
                   not stderr.channel.exit_status_ready()):

                # get data when available
                if stdout.channel.recv_ready():
                    out.stdout += str(stdout.channel.recv(1024), encoding)
                if stderr.channel.recv_stderr_ready():
                    out.stderr += str(stderr.channel.recv_stderr(1024),
                                      encoding)

            # strip unnecessary newlines
            out.stdout.rstrip()
            out.stderr.rstrip()

            # get command return code
            out.returncode = stdout.channel.recv_exit_status()

            # check if return code is 0
            if check:
                out.check_returncode()

            # print command stdout
            if not suppress_out:
                lprnt(f"{C}Printing remote output\n{'-' * 111}{R}")
                lprnt(out.stdout)
                lprnt(f"{C}{'-' * 111}{R}\n")

            return out
        else:
            # check if return code is 0, else raise exception
            if check:
                returncode = stdout.channel.recv_exit_status()
                if returncode != 0:
                    raise CalledProcessError(returncode, command, "", "")

            cp = CompletedProcess()
            cp.args = args

            return cp

    @_check_connections(exclude_exceptions=(FileNotFoundError, ValueError))
    def copy_files(self, files: List[str], remote_path: "SPath",
                   local_path: "SPath", direction: str, quiet: bool = False):
        """Send files in the chosen direction local <-> remote.

        Parameters
        ----------
        files: List[str]
            list of files to upload/download
        remote_path: "SPath"
            path to remote directory with files
        local_path: "SPath"
            path to local directory with files
        direction: str
            get for download and put for upload
        quiet: bool
            if True informative messages are suppresssed
        """
        with context_timeit(quiet):
            for f in files:
                file_remote = jn(self._path2str(remote_path), f)
                file_local = jn(self._path2str(local_path), f)

                if direction == "get":
                    lprint(quiet)(f"{G}Copying from remote:{R} "
                                  f"{self.server_name}@{file_remote}{LG}\n"
                                  f"-->           local:{R} {file_local}")

                    try:
                        self.sftp.get(file_remote, file_local)
                    except IOError as e:
                        raise FileNotFoundError(f"File you are trying to get "
                                                f"does not exist: {e}")

                elif direction == "put":
                    if not self.isdir(remote_path):
                        raise FileNotFoundError("Remote directory "
                                                "does not exist")

                    lprint(quiet)(f"{G}Copying from local:{R} {file_local}\n"
                                  f"{LG} -->       remote: {self.server_name}@"
                                  f"{file_remote}")

                    self.sftp.put(file_remote, file_local)
                else:
                    raise ValueError(f"{direction} is not valid direction. "
                                     f"Choose 'put' or 'get'")

    @_check_connections(exclude_exceptions=FileNotFoundError)
    def download_tree(self, remote_path: "SPath", local_path: "SPath",
                      include: "GlobPat" = None, exclude: "GlobPat" = None,
                      remove_after: bool = True, quiet: bool = False):
        """Download directory tree from remote.

        Remote direcctory must exist otherwise exception is raised.

        Parameters
        ----------
        remote_path: "SPath"
            path to directory which should be downloaded
        local_path: "SPath"
            directory to copy to, must be full path!
        remove_after: bool
            remove remote copy after directory is uploaded
        include: GlobPat
            glob pattern of files to include in copy, can be used
            simultaneously with exclude, default is None = no filtering
        exclude: GlobPat
            glob pattern of files to exclude in copy, can be used
            simultaneously with include, default is None = no filtering
        quiet: bool
            if True informative messages are suppresssed

        Warnings
        --------
        both paths must be full: <some_remote_path>/my_directory ->
        <some_local_path>/my_directory

        Raises
        ------
        FileNotFoundError
            when remote directory does not exist
        """
        dst = self._path2str(local_path)
        src = self._path2str(remote_path)

        if not self.isdir(remote_path):
            raise FileNotFoundError(f"{remote_path} you are trying to download"
                                    f"from does not exist")

        lprnt = lprint(quiet=quiet)
        allow_file = file_filter(include, exclude)

        copy_files = []
        dst_dirs = []

        lprnt(f"{C}Building directory structure for download from remote...\n")

        # create a list of directories and files to copy
        for root, _, files in self._sftp_walk(src):

            lprnt(f"{G}Searching remote directory:{R} "
                  f"{self.server_name}@{root}", up=1)

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
                    "size": self.sftp.lstat(jn(root, f)).st_size
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

        with ProgressBar(total=total, quiet=quiet) as t:
            for f in copy_files:

                t.write(f"{G}Copying remote:{R} {self.server_name}@{f['src']}"
                        f"\n{G}     --> local:{R} {f['dst']}")

                self.sftp.get(f["src"], f["dst"], callback=t.update_bar)

        lprnt("")

        if remove_after:
            self.rmtree(src)

    @_check_connections(exclude_exceptions=FileNotFoundError)
    def upload_tree(self, local_path: "SPath", remote_path: "SPath",
                    include: "GlobPat" = None, exclude: "GlobPat" = None,
                    remove_after: bool = True, quiet: bool = False):
        """Upload directory tree to remote.

        Local path must exist otherwise, exception is raised.

        Parameters
        ----------
        local_path: "SPath"
            path to directory which should be uploaded
        remote_path: "SPath"
            directory to copy to, must be full path!
        remove_after: bool
            remove local copy after directory is uploaded
        include: GlobPat
            glob pattern of files to include in copy, can be used
            simultaneously with exclude, default is None = no filtering
        exclude: GlobPat
            glob pattern of files to exclude in copy, can be used
            simultaneously with include, default is None = no filtering
        quiet: bool
            if True informative messages are suppresssed

        Warnings
        --------
        both paths must be full: <some_local_path>/my_directory ->
        <some_remote_path>/my_directory

        Raises
        ------
        FileNotFoundError
            when local directory does not exist
        """
        src = self._path2str(local_path)
        dst = self._path2str(remote_path)

        if not os.path.isdir(local_path):
            raise FileNotFoundError(f"{local_path} you are trying to upload "
                                    f"does not exist")

        lprnt = lprint(quiet=quiet)
        allow_file = file_filter(include, exclude)

        copy_files = []
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
            self.mkdir(d, exist_ok=True, quiet=quiet)

        # copy
        lprnt(f"\n{C}Copying...{R}\n")

        with ProgressBar(total=total, quiet=quiet) as t:
            for cf in copy_files:

                t.write(f"{G}Copying local:{R} {cf['src']}\n"
                        f"{G}   --> remote:{R} {self.server_name}@{cf['dst']}")

                self.sftp.put(cf["src"], cf["dst"], callback=t.update_bar)

        lprnt("")

        if remove_after:
            shutil.rmtree(src)

    @_check_connections
    def isfile(self, path: "SPath") -> bool:
        """Check ifg path points to a file.

        Parameters
        ----------
        path: "SPath"
            path to check

        Raises
        ------
        IOError
            if file could not be accessed
        """
        try:
            return S_ISREG(self.sftp.stat(self._path2str(path)).st_mode)
        except IOError:
            return False

    @_check_connections
    def isdir(self, path: "SPath") -> bool:
        """Check if path points to directory.

        Parameters
        ----------
        path: "SPath"
            path to check

        Raises
        ------
        IOError
            if dir could not be accessed
        """
        try:
            return S_ISDIR(self.sftp.stat(self._path2str(path)).st_mode)
        except IOError:
            return False

    @_check_connections
    def Path(self, path: "SPath") -> SSHPath:
        """Provides API similar to pathlib.Path only for remote host.

        Only for Unix to Unix connections

        Parameters
        ----------
        path: SPath
            provide initial path

        Returns
        -------
        SSHPath
            object representing remote path
        """
        return SSHPath(self, self._path2str(path))

    @_check_connections(exclude_exceptions=(FileExistsError, FileNotFoundError,
                                            OSError))
    def mkdir(self, path: "SPath", mode: int = 511, exist_ok: bool = True,
              parents: bool = True, quiet: bool = True):
        """Recursively create directory.

        If it already exists, show warning and return.

        Parameters
        ----------
        path: "SPath"
            path to directory which should be created
        mode: int
            create directory with mode, default is 511
        exist_ok: bool
            if true and directory exists, exception is silently passed when dir
            already exists
        parents: bool
            if true any missing parent dirs are automatically created, else
            exception is raised on missing parent
        quiet: bool
            if True informative messages are suppresssed

        Raises
        ------
        OSError
            if directory could not be created
        FileNotFoundError
            when parent directory is missing and parents=False
        FileExistsError
            when directory already exists and exist_ok=False
        """
        path = self._path2str(path)

        if not self.isdir(path):
            lprint(quiet)(f"{G}Creating directory:{R} "
                          f"{self.server_name}@{path}")

            if not parents:
                try:
                    self.sftp.mkdir(path, mode)
                except Exception as e:
                    raise FileNotFoundError(f"Error in creating directory: "
                                            f"{self.server_name}@{path}, "
                                            f"probably parent does not exist.")

            to_make = []
            actual = path

            while True:
                actual = os.path.dirname(actual)
                if not self.isdir(actual):
                    to_make.append(actual)
                else:
                    break

            for tm in reversed(to_make):
                try:
                    self.sftp.mkdir(tm, mode)
                except OSError as e:
                    raise OSError(f"Couldn't make dir {tm},\n probably "
                                  f"permission error: {e}")

            try:
                self.sftp.mkdir(path, mode)
            except OSError as e:
                raise OSError(f"Couldn't make dir {path}, probably "
                              f"permission error: {e}\n"
                              f"Also check path formating")
        elif not exist_ok:
            raise FileExistsError(f"Directory already exists: "
                                  f"{self.server_name}@{path}")

    @_check_connections(exclude_exceptions=FileNotFoundError)
    def rmtree(self, path: "SPath", ignore_errors: bool = False,
               quiet: bool = True):
        """Recursively remove directory tree.

        Parameters
        ----------
        path: "SPath"
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
        sn = self.server_name
        path = self._path2str(path)

        with context_timeit(quiet):
            lprint(quiet)(f"{G}Recursively removing dir:{R} {sn}@{path}")

            try:
                for root, _, files in self._sftp_walk(path):
                    for f in files:
                        f = jn(root, f)
                        lprint(quiet)(f"{G}removing file:{R} {sn}@{f}")
                        if self.isfile(f):
                            self.sftp.remove(f)
                    if self.isdir(root):
                        self.sftp.rmdir(root)

                if self.isdir(path):
                    self.sftp.rmdir(path)
            except FileNotFoundError as e:
                if ignore_errors:
                    self.log.warning("Directory does not exist")
                else:
                    raise FileNotFoundError(e)

    @_check_connections(exclude_exceptions=FileNotFoundError)
    def listdir(self, path: "SPath") -> List[str]:
        """Lists contents of specified directory.

        Parameters
        ----------
        path: "SPath"
            directory path

        Returns
        -------
        List[str]
            list  of files, dirs, symlinks ...

        Raises
        ------
        FileNotFoundError
            if directory does not exist
        """
        try:
            return self.sftp.listdir(self._path2str(path))
        except IOError as e:
            raise FileNotFoundError(f"Directory does not exist: {e}")

    @_check_connections
    def change_dir(self, path: "SPath"):
        """Change sftp working directory.

        Parameters
        ----------
        path: "SPath"
            new directory path
        """
        self.sftp.chdir(self._path2str(path))

    @_check_connections(exclude_exceptions=FileNotFoundError)
    def open(self, filename: "SPath", mode: str = "r",
             encoding: Optional[str] = None,
             bufsize: int = -1, errors: Optional[str] = None
             ) -> "SFTPFile":
        """Opens remote file, works as python open function.

        Can be used both as a function or a decorator.

        Parameters
        ----------
        filename: SPath
            path to file to be opened
        mode: str
            select mode to open file. Same as python open modes
        encoding: Optional[str]
            encoding type to decode file bytes stream
        bufsize: int
            buffer size, 0 turns off buffering, 1 uses line buffering, and any
            number greater than 1 (>1) uses that specific buffer size
        errors: Optional[str]
            string that specifies how encoding and decoding errors are to be
            handled, see builtin function
            `open <https://docs.python.org/3/library/functions.html#open>`_
            documentation for more details

        Raises
        ------
        FileNotFoundError
            when mode is 'r' and file does not exist
        """
        path = self._path2str(filename)
        encoding = encoding if encoding else "utf-8"
        errors = errors if errors else "strict"

        if not self.isfile(path) and "r" in mode:
            raise FileNotFoundError(f"Cannot open {path} for reading, "
                                    f"it does not exist.")

        def read_decode(self, size=None):
            data = self.paramiko_read(size=size)

            if isinstance(data, bytes) and "b" not in mode and encoding:
                data = data.decode(encoding=encoding, errors=errors)

            return data

        # open file
        file_obj = self.sftp.open(path, mode=mode, bufsize=bufsize)

        # rename the read method so i is not overwritten
        setattr(file_obj, "paramiko_read", getattr(file_obj, "read"))

        # repalce read with new method that automatically decodes
        file_obj.read = MethodType(read_decode, file_obj)

        return file_obj

    @property
    def osname(self) -> Literal["nt", "posix"]:
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
        if self._osname:
            return self._osname

        error_count = 0

        # Try some common cmd strings
        for cmd in ('ver', 'command /c ver', 'cmd /c ver'):
            try:
                info = self.run([cmd], suppress_out=True, quiet=True,
                                check=True, capture_output=True).stdout
            except CalledProcessError as e:
                self.log.debug(f"Couldn't get os name: {e}")
                error_count += 1
            else:
                if "windows" in info.lower():
                    self._osname = "nt"
                    break
                else:
                    continue
        else:
            # no errors were thrown, but os name could not be identified from
            # the response strings
            if error_count == 0:
                raise UnknownOsError("Couldn't get os name")
            else:
                self._osname = "posix"

        return self._osname

    # * additional methods needed by remote ssh class, not in ABC definition
    def _get_ssh(self, authentication_attempts: int = 0):

        try:
            if self.rsa_key:
                # connect with public key
                self._c.connect(self.address, username=self.username,
                                pkey=self.rsa_key)
            else:
                # if password was passed try to connect with it
                self._c.connect(self.address, username=self.username,
                                password=self.password, look_for_keys=False)

        except (paramiko.ssh_exception.AuthenticationException,
                paramiko.ssh_exception.NoValidConnectionsError) as e:
            self.log.warning(f"Error in authentication {e}. Trying again ...")

            # max three attempts to connect at once
            authentication_attempts += 1
            if authentication_attempts >= 3:
                raise ConnectionError(f"Connection to {self.address} "
                                      f"could not be established")
            else:
                self._get_ssh(authentication_attempts=authentication_attempts)

    @property
    def remote_home(self) -> str:
        if not self._remote_home:
            self.sftp

        return self._remote_home

    @property  # type: ignore
    @_check_connections
    def sftp(self) -> "SFTPClient":
        """Opens and return sftp channel.

        If SFTP coud be open then return SFTPClient instance else return None.

        Raises
        ------
        SFTPOpenError
            when remote home could not be found

        :type: Optional[paramiko.SFTPClient]
        """
        if not self._sftp_open:

            self._sftp = self._c.open_sftp()
            self.local_home = os.path.expanduser("~")

            for _ in range(3):  # sometimes failes, give it three tries
                try:
                    self._remote_home = self.run(
                        ["echo $HOME"], suppress_out=True, quiet=True,
                        check=True, capture_output=True).stdout.strip()
                except CalledProcessError as e:
                    print(f"{RED}Cannot establish remote home, trying again..")
                    exception = e
                else:
                    self._sftp_open = True
                    break
            else:
                print(f"{RED}Remote home could not be found {exception}")
                self._sftp_open = False
                raise SFTPOpenError("Remote home could not be found")

        return self._sftp

    @_check_connections
    def _sftp_walk(self, remote_path: "SPath"):
        """Recursive directory listing."""
        remote_path = self._path2str(remote_path)
        path = remote_path
        files = []
        folders = []
        for f in self.sftp.listdir_attr(remote_path):
            if S_ISDIR(f.st_mode):
                folders.append(f.filename)
            else:
                files.append(f.filename)

        yield path, folders, files

        for folder in folders:
            new_path = jn(remote_path, folder)
            for x in self._sftp_walk(new_path):
                yield x

    # ! DEPRECATED methods, kept for backwards compatibility reasons
    @_check_connections
    def sendCommand(self, command: str, suppress_out: bool,
                    quiet: bool = True):
        """DEPRECATED METHOD !!!.

        See also
        --------
        :meth:`run` more recent implementation
        """
        lprnt = lprint(quiet)
        commands = command.split(" && ")
        if len(commands) == 1:
            lprnt(f"{Y}Executing command on remote:{R} {command}\n")
        else:
            lprnt(f"{Y}Executing commands on remote:{R} {commands[0]}")
            for c in commands[1:]:
                lprnt(" " * 30 + c)

        # vykonat prikaz
        # stdin, stdout, stderr
        stdout = self._c.exec_command(command, get_pty=True)[1]

        while not stdout.channel.exit_status_ready():
            # print data when available
            if stdout.channel.recv_ready():
                alldata = stdout.channel.recv(1024)
                prevdata = b"1"
                while prevdata:
                    prevdata = stdout.channel.recv(1024)
                    alldata += prevdata

                if not suppress_out:
                    lprnt(f"{C}Printing remote output\n{'-' * 111}{R}")
                    lprnt(str(alldata, "utf8"))
                    lprnt(f"{C}{'-' * 111}{R}\n")

                return str(alldata, "utf8")

    sendFiles = copy_files
    send_files = copy_files
    downloadTree = download_tree
    uploadTree = upload_tree
