"""Module implementing SSH connection functionality."""

import logging
import os

# because of python 3.6 we do not use contextlib
from ..utils import NullContext as nullcontext

from pathlib import Path
from threading import RLock
from typing import TYPE_CHECKING, ContextManager, Dict, Optional, Union

import paramiko

from ..abstract import ConnectionABC
from ..constants import RED, C, G, R, Y
from ..exceptions import CalledProcessError, ConnectionError, SFTPOpenError
from ..utils import lprint
from . import Builtins, Os, Pathlib, Shutil, Subprocess
from ._connection_wrapper import check_connections

if TYPE_CHECKING:
    from paramiko.client import SSHClient
    from paramiko.sftp_client import SFTPClient

    from ..abstract import (_BUILTINS_REMOTE, _OS_REMOTE, _PATHLIB_REMOTE,
                       _SHUTIL_REMOTE, _SUBPROCESS_REMOTE)

__all__ = ["SSHConnection"]

log = logging.getLogger(__name__)

_KEYS = (
    paramiko.RSAKey,
    paramiko.Ed25519Key,
    paramiko.DSSKey,
    paramiko.ECDSAKey
)


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
    pkey_file: Optional[Union[str, Path]]
        path to rsa key file
    line_rewrite: bool
        rewrite lines in output when copying instead of normal mode when lines
        are outputed one after the other. Default is True
    warn_on_login: bool
        Display on warnings of firs login
    server_name: Optional[str]
        input server name that will be later displayed on file operations,
        if None then IP address will be used
    thread_safe: bool
        make connection object thread safe so it can be safely accessed from
        any number of threads, it is disabled by default to avoid performance
        penalty of threading locks

    Warnings
    --------
    At least one of (password, pkey_file, allow_agent) must be specified, priority used is
    SSH-Agent -> RSA Key -> password

    thread_safe parameter is not implemented yet!!!

    Raises
    ------
    ConnectionError
        connection to remote could not be established
    """

    _remote_home: str = ""
    __lock: Union[ContextManager[None], RLock]
    __AUTH_ATTEMPTS: int = 3

    def __init__(self, address: str, username: str,
                 password: Optional[str] = None,
                 pkey_file: Optional[Union[str, Path]] = None,
                 line_rewrite: bool = True, server_name: Optional[str] = None,
                 quiet: bool = False, thread_safe: bool = False,
                 allow_agent: Optional[bool] = False) -> None:

        log.info(f"Connection object will {'' if thread_safe else 'not'} be "
                 f"thread safe")

        if thread_safe:
            self.thread_safe = True
            self.__lock = RLock()
        else:
            self.thread_safe = False
            self.__lock = nullcontext()

        lprint.line_rewrite = line_rewrite
        lprnt = lprint(quiet)

        if allow_agent:
            msg = "Will login with ssh-agent"
            lprnt(msg)
            log.info(msg)
        if pkey_file:
            msg = f"Will login with private RSA key located in {pkey_file}"
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

        msg = (f"{RED}When running an executale on server always make "
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
        self.pkey_file = pkey_file
        self.allow_agent = allow_agent

        if not allow_agent and not pkey_file and not password:
            raise RuntimeError(
                "Must allow ssh-agent input password or path to private key"
            )


        if pkey_file:
            self._load_pkey()

        self._c = paramiko.client.SSHClient()
        self._c.set_missing_host_key_policy(paramiko.client.AutoAddPolicy())

        # negotiate connection
        self._get_ssh()

        # init submodules
        self._builtins = Builtins(self)  # type: ignore
        self._os = Os(self)  # type: ignore
        self._pathlib = Pathlib(self)  # type: ignore
        self._shutil = Shutil(self)  # type: ignore
        self._subprocess = Subprocess(self)  # type: ignore

    @property
    def c(self) -> "SSHClient":
        with self.__lock:
            return self._c

    @property
    def builtins(self) -> "_BUILTINS_REMOTE":
        """Inner class providing access to substitutions for python builtins.

        :type: .remote.Builtins
        """
        return self._builtins

    @property
    def os(self) -> "_OS_REMOTE":
        """Inner class providing access to substitutions for python os module.

        :type: .remote.Os
        """
        return self._os

    @property
    def pathlib(self) -> "_PATHLIB_REMOTE":
        """Inner class providing access to substitutions for pathlib module.

        :type: .remote.Pathlib
        """
        return self._pathlib

    @property
    def shutil(self) -> "_SHUTIL_REMOTE":
        """Inner class providing access to substitutions for shutil module.

        :type: .remote.Shutil
        """
        return self._shutil

    @property
    def subprocess(self) -> "_SUBPROCESS_REMOTE":
        """Inner class providing access to substitutions for subprocess module.

        :type: .remote.Subprocess
        """
        return self._subprocess

    def __str__(self) -> str:
        return self._to_str("SSHConnection", self.server_name, self.address,
                            self.username, self.pkey_file, self.thread_safe,
                            self.allow_agent)

    def to_dict(self) -> Dict[str, Optional[Union[str, bool, int]]]:
        return self._to_dict("SSHConnection", self.server_name, self.address,
                             self.username, self.pkey_file, self.thread_safe,
                             self.allow_agent)

    @check_connections()
    def close(self, *, quiet: bool = True):
        """Close SSH connection.

        Parameters
        ----------
        quiet: bool
            whether to print other function messages
        """
        lprint(quiet)(f"{G}Closing ssh connection to:{R} {self.server_name}")
        self.c.close()

    # * additional methods needed by remote ssh class, not in ABC definition
    def _get_ssh(self):

        def _connect(method: str, **kwargs):

            log.info(f"trying to authenticate with {method}")
            for _ in range(self.__AUTH_ATTEMPTS):
                with self.__lock:
                    try:
                        self.c.connect(self.address, username=self.username, **kwargs)
                    except (paramiko.ssh_exception.AuthenticationException,
                            paramiko.ssh_exception.NoValidConnectionsError) as e:
                        log.warning(
                            f"Error in authentication {e}. Trying again ..."
                        )
                    else:
                        log.info(f"successfully authenticated with: {method}")
                        return True

            log.warning(
                f"authentication with {method} failed, reverting to backup methods"
            )
            return False

        # we will try each method maximum three times
        # authenticatiom method preference is based on security and convenience
        if self.allow_agent and _connect("ssh-agent", allow_agent=True):
            return

        if self.pkey_file and _connect("private-key", pkey=self._pkey):
            return

        if self.password and _connect("password", password=self.password, look_for_keys=False):
            return

        # if none of the authentication methods was sucessfull, raise error
        raise ConnectionError(
            f"Connection to {self.address} could not be established"
        )


    def _load_pkey(self):

        for key in _KEYS:
            try:
                self._pkey = key.from_private_key_file(
                    self._path2str(self.pkey_file)
                )
            except paramiko.SSHException:
                log.info(f"could not parse key with {key.__name__}")        

    @property  # type: ignore
    @check_connections()
    def sftp(self) -> "SFTPClient":
        """Opens and return sftp channel.

        If SFTP coud be open then return SFTPClient instance else return None.

        :type: :class:`Optional[paramiko.SFTPClient]`

        Raises
        ------
        SFTPOpenError
            when remote home could not be found
        """
        with self.__lock:
            if not self._sftp_open:

                self._sftp = self.c.open_sftp()
                self.local_home = os.path.expanduser("~")

                for _ in range(3):  # sometimes failes, give it three tries
                    try:
                        self._remote_home = self.subprocess.run(
                            ["echo $HOME"], suppress_out=True, quiet=True,
                            encoding="utf-8",
                            check=True, capture_output=True).stdout.strip()
                    except CalledProcessError as e:
                        print(f"{RED}Cannot establish remote home, "
                              f"trying again..")
                        exception = e
                    else:
                        self._sftp_open = True
                        break
                else:
                    print(f"{RED}Remote home could not be found "
                          f"{exception}")  # type: ignore
                    self._sftp_open = False
                    raise SFTPOpenError("Remote home could not be found")

            return self._sftp
