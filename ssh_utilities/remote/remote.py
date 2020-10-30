"""Module implementing SSH connection functionality."""

import builtins
import logging
import os
from pathlib import Path
import pathlib
import shutil
import subprocess
from typing import TYPE_CHECKING, Optional, Union
from colorama.initialise import reinit

import paramiko

from ..base import ConnectionABC
from ..constants import RED, C, G, R, Y
from ..exceptions import CalledProcessError, ConnectionError, SFTPOpenError
from ..utils import lprint
from . import Builtins, Os, Pathlib, Shutil, Subprocess
from ._connection_wrapper import check_connections

if TYPE_CHECKING:
    from paramiko.sftp_client import SFTPClient

__all__ = ["SSHConnection"]

log = logging.getLogger(__name__)


# ! this is not a viable way, too complex logic
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

    _remote_home: str = ""

    def __init__(self, address: str, username: str,
                 password: Optional[str] = None,
                 rsa_key_file: Optional[Union[str, Path]] = None,
                 line_rewrite: bool = True, server_name: Optional[str] = None,
                 quiet: bool = False, share_connection: int = 10) -> None:

        lprint.line_rewrite = line_rewrite
        lprnt = lprint(quiet)

        if rsa_key_file:
            msg = f"Will login with private RSA key located in {rsa_key_file}"
            lprnt(msg)
            log.info(msg)
        else:
            msg = f"Will login as {username} to {address}"
            lprnt(msg)
            log.info(msg)

        msg = (f"{C}Connecting to server:{R} {username}@{address}"
               f"{' (' + server_name + ')' if server_name else ''}")
        lprnt(msg)
        log.info(msg.replace(C, "").replace(R, ""))

        msg = (f"{RED}When running an executale on server always make"
               f"sure that full path is specified!!!\n")

        lprnt(msg)
        log.info(msg.replace(R, "").replace(RED, ""))

        # misc
        self._sftp_open = False
        self.server_name = server_name.upper() if server_name else address

        self.local = False

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

        self.c = paramiko.client.SSHClient()
        self.c.set_missing_host_key_policy(paramiko.client.AutoAddPolicy())

        # negotiate connection
        self._get_ssh()

        # init submodules
        self._builtins = Builtins(self)  # type: ignore
        self._os = Os(self)  # type: ignore
        self._pathlib = Pathlib(self)  # type: ignore
        self._shutil = Shutil(self)  # type: ignore
        self._subprocess = Subprocess(self)  # type: ignore

    @property
    def builtins(self) -> Builtins:
        return self._builtins

    @property
    def os(self) -> Os:
        return self._os

    @property
    def pathlib(self) -> Pathlib:
        return self._pathlib

    @property
    def shutil(self) -> Shutil:
        return self._shutil

    @property
    def subprocess(self) -> Subprocess:
        return self._subprocess

    def __str__(self) -> str:
        return self.to_str("SSHConnection", self.server_name, self.address,
                           self.username, self.rsa_key_file)

    @check_connections
    def close(self, *, quiet: bool = True):
        """Close SSH connection.

        Parameters
        ----------
        quiet: bool
            whether to print other function messages
        """
        lprint(quiet)(f"{G}Closing ssh connection to:{R} {self.server_name}")
        self.c.close()

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

    # * additional methods needed by remote ssh class, not in ABC definition
    def _get_ssh(self, authentication_attempts: int = 0):

        try:
            if self.rsa_key:
                # connect with public key
                self.c.connect(self.address, username=self.username,
                               pkey=self.rsa_key)
            else:
                # if password was passed try to connect with it
                self.c.connect(self.address, username=self.username,
                               password=self.password, look_for_keys=False)

        except (paramiko.ssh_exception.AuthenticationException,
                paramiko.ssh_exception.NoValidConnectionsError) as e:
            log.warning(f"Error in authentication {e}. Trying again ...")

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
    @check_connections
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

            self._sftp = self.c.open_sftp()
            self.local_home = os.path.expanduser("~")

            for _ in range(3):  # sometimes failes, give it three tries
                try:
                    self._remote_home = self.subprocess.run(
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
