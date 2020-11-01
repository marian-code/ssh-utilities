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
from .utils import config_parser

if TYPE_CHECKING:
    from pathlib import Path

    from typing_extensions import TypedDict

    _HOSTS = TypedDict("_HOSTS", {"user": str, "hostname": str,
                                  "identityfile": Union[str, List[str]]})

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

    available_hosts: Dict

    def __new__(cls, classname, bases, dictionary: dict):

        dictionary["available_hosts"] = dict()

        if not (RTD or CI):
            config = config_parser(CONFIG_PATH)

            # add remote hosts
            for host in config.get_hostnames():
                dictionary["available_hosts"][host] = config.lookup(host)

        return type.__new__(cls, classname, bases, dictionary)

    def __getitem__(cls, key: str) -> Union[SSHConnection, LocalConnection]:
        return cls.get(key, local=False, quiet=False, thread_safe=False)

    def get(cls, *args, **kwargs) -> Union[SSHConnection, LocalConnection]:
        """Overriden in class that inherits this metaclass."""
        ...


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
    >>> conn = Connection.from_str(<string>)

    returns an initialized connection instance.

    All these return connection with preset reasonable parameters if more
    customization is required, use open method, this also allows use of
    passwords

    >>> from ssh_utilities import Connection
    >>> conn = Connection.open(<ssh_username>, <ssh_server>, <ssh_key_file>,
                               <server_name>, <thread_safe>):
    """

    def __init__(self, ssh_server: str, local: bool = False,
                 quiet: bool = False, thread_safe: bool = False) -> None:
        self._connection = self.get(ssh_server, local=local, quiet=quiet,
                                    thread_safe=thread_safe)

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
    def get(cls, ssh_server: str, local: Literal[False], quiet: bool,
            thread_safe: bool) -> SSHConnection:
        ...

    @overload
    @classmethod
    def get(cls, ssh_server: str, local: Literal[True], quiet: bool,
            thread_safe: bool) -> LocalConnection:
        ...

    @overload
    @classmethod
    def get(cls, ssh_server: str, local: bool, quiet: bool,
            thread_safe: bool) -> Union[SSHConnection, LocalConnection]:
        ...

    @classmethod
    def get(cls, ssh_server: str, local: bool = False, quiet: bool = False,
            thread_safe: bool = False):
        """Get Connection based on one of names defined in .ssh/config file.

        If name of local PC is passed initilize LocalConnection

        Parameters
        ----------
        ssh_server : str
            server name to connect to defined in ~/.ssh/config file
        local: bool
            if True return emulated connection to loacl host
        quiet: bool
            If True suppress login messages
        thread_safe: bool
            make connection object thread safe so it can be safely accessed
            from  any number of threads, it is disabled by default to avoid
            performance  penalty of threading locks

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
            return cls.open(getpass.getuser(), server_name=gethostname(),
                            quiet=quiet)

        try:
            credentials = cls.available_hosts[ssh_server]
        except KeyError as e:
            raise KeyError(f"couldn't find login credentials for {ssh_server}:"
                           f" {e}")
        else:
            try:
                return cls.open(credentials["user"], credentials["hostname"],
                                credentials["identityfile"][0],
                                server_name=ssh_server, quiet=quiet,
                                thread_safe=thread_safe)
            except KeyError as e:
                raise KeyError(f"{RED}missing key in config dictionary for "
                               f"{ssh_server}: {R}{e}")

    get_connection = get

    @classmethod
    def add_hosts(cls, hosts: Union["_HOSTS", List["_HOSTS"]]):
        """add or override availbale host read fron ssh config file.

        You can use supplied config parser to parse some externaf ssh config
        file.

        Parameters
        ----------
        hosts : Union[_HOSTS, List[_HOSTS]]
            dictionary or a list of dictionaries containing keys: `user`,
            `hostname` and `identityfile`

        See also
        --------
        :func: ssh_utilities.config_parser
        """
        if not isinstance(hosts, list):
            hosts = [hosts]

        for h in hosts:
            if not isinstance(h["identityfile"], list):
                h["identityfile"] = [h["identityfile"]]

        cls.available_hosts.update({h: h["hostname"] for h in hosts})

    @classmethod
    def from_str(cls, string: str, quiet: bool = False
                 ) -> Union[SSHConnection, LocalConnection]:
        """Initializes Connection from str.

        String must be formated as defined by `base.ConnectionABC.to_str`
        method.

        Parameters
        ----------
        string: str
            str to initialize connection from
        quiet: bool
            If True suppress login messages

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
                r"\(user_name:(\S*) \| rsa_key:(\S*) \| address:(\S*) \| "
                r"threadsafe:(\S*)\)", string)[0]
        except IndexError:
            raise ValueError("String is not formated correctly")

        return cls.open(user_name, address, ssh_key, server_name, quiet=quiet)

    @overload
    @staticmethod
    def open(ssh_username: str, ssh_server: None = None,
             ssh_key_file: Optional[Union[str, "Path"]] = None,
             ssh_password: Optional[str] = None,
             server_name: Optional[str] = None, quiet: bool = False,
             thread_safe: bool = False) -> LocalConnection:
        ...

    @overload
    @staticmethod
    def open(ssh_username: str, ssh_server: str,
             ssh_key_file: Optional[Union[str, "Path"]] = None,
             ssh_password: Optional[str] = None,
             server_name: Optional[str] = None, quiet: bool = False,
             thread_safe: bool = False) -> SSHConnection:
        ...

    @staticmethod
    def open(ssh_username: str, ssh_server: Optional[str] = "",
             ssh_key_file: Optional[Union[str, "Path"]] = None,
             ssh_password: Optional[str] = None,
             server_name: Optional[str] = None, quiet: bool = False,
             thread_safe: bool = False):
        """Initialize SSH or local connection.

        Local connection is only a wrapper around os and shutil module methods
        and its purpose is to mirror API of the SSHConnection class

        Parameters
        ----------
        ssh_username: str
            login name, only used for remote connections
        ssh_server: str
            server address, numeric address or normal address
        ssh_key_file: Optional[Union[str, Path]]
            path to file with private rsa key. If left empty and password is
            `None` script will ask for password.
        ssh_password: Optional[str]
            password in string form, this is mainly for testing. Using this in
            production is a great security risk!
        server_name: str
            server name (default:None) only for id purposes, if it is left
            default than it will be replaced with address.
        quiet: bool
            If True suppress login messages
        thread_safe: bool
            make connection object thread safe so it can be safely accessed
            from  any number of threads, it is disabled by default to avoid
            performance  penalty of threading locks

        Warnings
        --------
        Do not use plain text passwords in production, they are great security
        risk!
        """
        if not ssh_server:
            return LocalConnection(ssh_server, ssh_username,
                                   rsa_key_file=ssh_key_file,
                                   server_name=server_name, quiet=quiet)
        else:
            if ssh_key_file:
                c = SSHConnection(ssh_server, ssh_username,
                                  rsa_key_file=ssh_key_file, line_rewrite=True,
                                  server_name=server_name, quiet=quiet,
                                  thread_safe=thread_safe)
            else:
                if not ssh_password:
                    ssh_password = getpass.getpass(prompt="Enter password: ")

                c = SSHConnection(ssh_server, ssh_username,
                                  password=ssh_password, line_rewrite=True,
                                  server_name=server_name, quiet=quiet,
                                  thread_safe=thread_safe)

            return c
