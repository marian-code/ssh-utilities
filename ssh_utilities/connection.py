"""The main module with toplevel Connection class.

The connection class is the main public class that initializes local
or remote connection classes as needed based on input arguments.
"""

import getpass
import logging
import os
import re
from socket import gethostname
from typing import TYPE_CHECKING, Dict, List, Optional, Union, overload

from typing_extensions import Literal

from .constants import CONFIG_PATH, RED, R
from .local import LocalConnection
from .remote import SSHConnection
from .utils import config_parser, lprint

if TYPE_CHECKING:
    from logging import Logger
    from pathlib import Path

__all__ = ["Connection"]

logging.getLogger(__name__)

# guard for when readthedocs is building documentation or travis
# is running CI build
RTD = os.environ.get("READTHEDOCS", False)
CI = os.environ.get("TRAVIS", False)


class _ConnectionMeta(type):
    """MetaClass for connection factory, adds indexing support.

    The inheriting classes can be indexed by keys in ~/.ssh/config file
    """

    SHARE_CONNECTION: int = 10
    available_hosts: Dict

    def __new__(cls, classname, bases, dictionary: dict):

        dictionary["available_hosts"] = dict()

        if not RTD and CI:
            config = config_parser(CONFIG_PATH)

            # add remote hosts
            for host in config.get_hostnames():
                dictionary["available_hosts"][host] = config.lookup(host)

        return type.__new__(cls, classname, bases, dictionary)

    def __getitem__(cls, key: str) -> Union[SSHConnection, LocalConnection]:

        try:
            credentials = cls.available_hosts[key]
        except KeyError as e:
            raise KeyError(f"No such host  available: {e}")
        else:
            try:
                return cls.open(credentials["user"], credentials["hostname"],
                                credentials["identityfile"][0],
                                server_name=key,
                                share_connection=cls.SHARE_CONNECTION)
            except KeyError as e:
                raise KeyError(f"{RED}Missing key in config dictionary: "
                               f"{R}{e}")

    def open(cls, *args, **kwargs):
        pass


class Connection(metaclass=_ConnectionMeta):
    """Factory for class with self-keeping SSH or local connection.

    Main purpose is to have SSH connection with convenience methods which can
    be easily used. Connection is resiliet to errors and will reinitialize
    itself if for some reason it fails. It also has a local wariant which is
    mirroring its API but uses os and shutil and subprocess modules internally.

    This is a factory class so calling any of the initializer classmethods
    returns initialized SSHConnection or LocalConnection based on arguments.

    All methods belong to class so this object should not be instantiated.

    Upon import this class automatically reads ssh configuration file in:
    ~/.ssh/config if it is present. The class is then indexable by keys in
    config file so calling:

    Examples
    --------
    >>> from ssh_utilities import Connection
    >>> Connection[<server_name>]
    >>> <ssh_utilities.ssh_utils.SSHConnection at 0x7efedff4fb38>

    There is also a specific get method which is safer and with better typing
    support than dict-like indexing

    >>> from ssh_utilities import Connection
    >>> Connection.get(<server_name>)
    >>> <ssh_utilities.ssh_utils.SSHConnection at 0x7efedff4fb38>

    Class can be also used as a context manager.

    >>> from ssh_utilities import Connection
    >>> with Connection(<server_name>) as conn:
    >>>     conn.something(...)

    Connection can also be initialized from appropriately formated string.
    Strings are used mainly for underlying connection classes persistance to
    disk

    >>> from ssh_utilities import Connection
    >>> Connection.from_str(<string>)

    returns an initialized connection instance.

    All these return connection with preset reasonable parameters if more
    customization is required, use open method, this also allows use of
    passwords

    >>> from ssh_utilities import Connection
    >>> with Connection.open(<sshUsername>, <sshServer>, <sshKey>,
                             <server_name>, <logger>, <share_connection>):
    """

    def __init__(self, sshServer: str, local: bool = False) -> None:
        self._connection = self.get(sshServer, local=local)

    def __enter__(self) -> Union[SSHConnection, LocalConnection]:
        return self._connection

    def __exit__(self, exc_type, exc_value, exc_traceback):
        self._connection.close(quiet=True)

    @classmethod
    def get_available_hosts(cls) -> List[str]:
        """List all elegible hosts for connection from ~/.ssh/config.

        Returns
        -------
        List[str]
            list of available hosts
        """
        available = []
        for host, credentials in cls.available_hosts.items():
            if host == "*":
                continue
            elif not (credentials.get("user", None) and
                      credentials.get("hostname", None)):
                continue
            else:
                available.append(host)

        return available

    @overload
    @classmethod
    def get(cls, sshServer: str, local: Literal[False],
            ) -> SSHConnection:
        ...

    @overload
    @classmethod
    def get(cls, sshServer: str, local: Literal[True],
            ) -> LocalConnection:
        ...

    @overload
    @classmethod
    def get(cls, sshServer: str, local: bool,
            ) -> Union[SSHConnection, LocalConnection]:
        ...

    @classmethod
    def get(cls, sshServer: str, local: bool = False):
        """Get Connection based on one of names defined in .ssh/config file.

        If name of local PC is passed initilize LocalConnection

        Parameters
        ----------
        sshServer : str
            server name to connect to defined in ~/.ssh/config file
        local: bool
            if True return emulated connection to loacl host

        Raises
        ------
        KeyError
            if server name is not in config file

        Returns
        -------
        SSHConnection
            Instance of SSHConnection for selected server
        """
        if local:
            return cls.open(getpass.getuser(), server_name=gethostname())
        else:
            return cls.__getitem__(sshServer)

    get_connection = get

    @classmethod
    def from_str(cls, string: str) -> Union[SSHConnection, LocalConnection]:
        """Initializes Connection from str.

        String must be formated as defined by `base.ConnectionABC.to_str`
        method.

        Parameters
        ----------
        string: str
            str to initialize connection from

        Returns
        -------
        Union[SSHConnection, LocalConnection]
            initialized local or remmote connection
            based on parameters parsed from string

        Raises
        ------
        ValueError
            if string with wrong formating is passed
        """
        try:
            server_name = re.findall(r"<\S*:(\S*)>", string)[0]
            user_name, ssh_key, address = re.findall(
                r"\(user_name:(\S*) \| rsa_key:(\S*) \| address:(\S*)\)",
                string)[0]
        except IndexError:
            raise ValueError("String is not formated correctly")

        return cls.open(user_name, address, ssh_key, server_name)

    @classmethod
    def set_shared(cls, number_of_shared: Union[int, bool]):
        """Set how many instancesd can share the same connection to server.

        Parameters
        ----------
        number_of_shared: Union[int, bool]
            if int number of shared instances is set to that number
            if False number of shared instances is set to 0
            if True number of shared instances is set to 10
        """
        if number_of_shared is True:
            number_of_shared = 10
        elif number_of_shared is False:
            number_of_shared = 0
        cls.SHARE_CONNECTION = number_of_shared

    @overload
    @staticmethod
    def open(sshUsername: str, sshServer: None = None,
             sshKey: Optional[Union[str, "Path"]] = None,
             sshPassword: Optional[str] = None,
             server_name: Optional[str] = None,
             logger: Optional["Logger"] = None,
             share_connection: int = 10) -> LocalConnection:
        ...

    @overload
    @staticmethod
    def open(sshUsername: str, sshServer: str,
             sshKey: Optional[Union[str, "Path"]] = None,
             sshPassword: Optional[str] = None,
             server_name: Optional[str] = None,
             logger: Optional["Logger"] = None,
             share_connection: int = 10) -> SSHConnection:
        ...

    @staticmethod
    def open(sshUsername: str, sshServer: Optional[str] = "",
             sshKey: Optional[Union[str, "Path"]] = None,
             sshPassword: Optional[str] = None,
             server_name: Optional[str] = None,
             logger: Optional["Logger"] = None,
             share_connection: int = 10):
        """Initialize SSH or local connection.

        Local connection is only a wrapper around os and shutil module methods
        and its purpose is to mirror API of the SSHConnection class

        Parameters
        ----------
        sshUsername: str
            login name, only used for remote connections
        sshServer: str
            server address, numeric address or normal address
        sshKey: Optional[Union[str, Path]]
            path to file with private rsa key. If left empty and password is
            `None` script will ask for password.
        sshPassword: Optional[str]
            password in string form, this is mainly for testing. Using this in
            production is a great security risk!
        server_name: str
            server name (default:None) only for id purposes, if it is left
            default than it will be replaced with address.
        logger: logging.Logger
            logger instance, If argument is left default than than logging
            messages will be rerouted to stdout/stderr.
        share_connection: int
            share connection between different instances of class, number says
            how many instances can share the same connection

        Warnings
        --------
        Do not use plain text passwords in production, they are great security
        risk!
        """
        if not sshServer:
            return LocalConnection(sshServer, sshUsername, rsa_key_file=sshKey,
                                   server_name=server_name, logger=logger)
        else:
            if sshKey:
                lprint(False)(f"Will login with private RSA key "
                              f"located in {sshKey}")

                c = SSHConnection(sshServer, sshUsername, rsa_key_file=sshKey,
                                  line_rewrite=True, server_name=server_name,
                                  logger=logger,
                                  share_connection=share_connection)
            else:
                lprint(False)(f"Will login as {sshUsername} to {sshServer}")

                if not sshPassword:
                    sshPassword = getpass.getpass(prompt="Enter password: ")

                c = SSHConnection(sshServer, sshUsername, password=sshPassword,
                                  line_rewrite=True, server_name=server_name,
                                  logger=logger,
                                  share_connection=share_connection)

            return c
