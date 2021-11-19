"""The main module with toplevel Connection class.

The connection class is the main public class that initializes local
or remote connection classes as needed based on input arguments.
"""

import getpass
import logging
import os
from json import loads
from socket import gethostname
from typing import TYPE_CHECKING, Dict, List, Optional, Union, overload

try:
    from typing import Literal  # type: ignore - python >= 3.8
except ImportError:
    from typing_extensions import Literal  # python < 3.8

from .constants import CONFIG_PATH, RED, R
from .local import LocalConnection
from .remote import SSHConnection
from .utils import config_parser

if TYPE_CHECKING:
    from pathlib import Path

    try:
        from typing import TypedDict  # type: ignore - python >= 3.8
    except ImportError:
        from typing_extensions import TypedDict  # python < 3.8

    _HOSTS = TypedDict("_HOSTS", {"user": str, "hostname": str,
                                  "identityfile": Union[str, List[str]]})

__all__ = ["Connection"]

log = logging.getLogger(__name__)

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
        return cls(key, local=False, quiet=False, thread_safe=False)


class Connection(metaclass=_ConnectionMeta):
    """Factory for class with self-keeping SSH or local connection.

    Main purpose is to have SSH connection with convenience methods which can
    be easily used. Connection is resiliet to errors and will reinitialize
    itself if for some reason it fails. It also has a local variant which is
    mirroring its API but uses os and shutil and subprocess modules internally.

    This is a factory class so calling any of the initializer classmethods
    returns initialized SSHConnection or LocalConnection based on arguments.

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
    >>> Connection(<server_name>)
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

    @overload
    def __new__(cls, ssh_server: str, local: Literal[False], quiet: bool,
                thread_safe: bool, allow_agent: bool) -> SSHConnection:
        ...

    @overload
    def __new__(cls, ssh_server: str, local: Literal[True], quiet: bool,
                thread_safe: bool, allow_agent: bool) -> LocalConnection:
        ...

    @overload
    def __new__(cls, ssh_server: str, local: bool, quiet: bool,
                thread_safe: bool, allow_agent: bool
                ) -> Union[SSHConnection, LocalConnection]:
        ...

    def __new__(cls, ssh_server: str, local: bool = False, quiet: bool = False,
                thread_safe: bool = False, allow_agent: bool = True):
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
        allow_agent: bool
            allows use of ssh agent for connection authentication, when this is
            `True` key for the host does not have to be available.

        Raises
        ------
        KeyError
            if server name is not in config file and allow agent is false

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
            # get username and address
            try:
                user = credentials["user"]
                hostname = credentials["hostname"]
            except KeyError as e:
                raise KeyError(
                    "Cannot find username or hostname for specified host"
                )

            # get key or use agent
            if allow_agent:
                log.info(f"no private key supplied for {hostname}, will try "
                         f"to authenticate through ssh-agent")
                pkey_file = None
            else:
                log.info(f"private key found for host: {hostname}")
                try:
                    pkey_file = credentials["identityfile"][0]
                except (KeyError, IndexError) as e:
                    raise KeyError(f"No private key found for specified host")

            return cls.open(
                user,
                hostname,
                ssh_key_file=pkey_file,
                allow_agent=allow_agent,
                server_name=ssh_server,
                quiet=quiet,
                thread_safe=thread_safe
            )

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

    @classmethod
    def get(cls, *args, **kwargs):
        raise AttributeError(
            "Usage of 'get'/'get_connection' method is deprecated. "
            "Instantiate the object normally instead.",
        )
    get_connection = get

    @classmethod
    def add_hosts(cls, hosts: Union["_HOSTS", List["_HOSTS"]],
                  allow_agent: Union[bool, List[bool]]):
        """Add or override availbale host read fron ssh config file.

        You can use supplied config parser to parse some externaf ssh config
        file.

        Parameters
        ----------
        hosts : Union[_HOSTS, List[_HOSTS]]
            dictionary or a list of dictionaries containing keys: `user`,
            `hostname` and `identityfile`
        allow_agent: Union[bool, List[bool]]
            bool or a list of bools with corresponding length to list of hosts.
            if only one bool is passed in, it will be used for all host entries

        See also
        --------
        :func:ssh_utilities.config_parser
        """
        if not isinstance(hosts, list):
            hosts = [hosts]
        if not isinstance(allow_agent, list):
            allow_agent = [allow_agent] * len(hosts)

        for h, a in zip(hosts, allow_agent):
            if a:
                h["identityfile"][0] = None
            if not isinstance(h["identityfile"], list):
                h["identityfile"] = [h["identityfile"]]
            h["identityfile"][0] = os.path.abspath(
                os.path.expanduser(h["identityfile"][0])
            )

        cls.available_hosts.update({h["hostname"]: h for h in hosts})

    @classmethod
    def from_str(cls, string: str, quiet: bool = False
                 ) -> Union[SSHConnection, LocalConnection]:
        """Initializes Connection from str.

        String must be formated as defined by `abc.ConnectionABC._to_str`
        method.

        Parameters
        ----------
        string: str
            json str to initialize connection from
        quiet: bool
            If True suppress login messages

        Returns
        -------
        Union[SSHConnection, LocalConnection]
            initialized local or remmote connection
            based on parameters parsed from string

        Raises
        ------
        KeyError
            if required key is missing from string
        """
        return cls.from_dict(loads(string), quiet=quiet)

    @classmethod
    def from_dict(cls, json: dict, quiet: bool = False
                  ) -> Union[SSHConnection, LocalConnection]:
        """Initializes Connection from str.

        String must be formated as defined by `abc.ConnectionABC._to_str`
        method.

        Parameters
        ----------
        json: dict
            dictionary initialize connection from
        quiet: bool
            If True suppress login messages

        Returns
        -------
        Union[SSHConnection, LocalConnection]
            initialized local or remmote connection
            based on parameters parsed from string
        """
        return cls.open(json["user_name"], json["address"], json["ssh_key"],
                        json["server_name"], quiet=quiet,
                        thread_safe=json["thread_safe"])

    @overload
    @staticmethod
    def open(ssh_username: str, ssh_server: None = None,
             ssh_key_file: Optional[Union[str, "Path"]] = None,
             ssh_password: Optional[str] = None,
             server_name: Optional[str] = None, quiet: bool = False,
             thread_safe: bool = False,
             allow_agent: bool = False) -> LocalConnection:
        ...

    @overload
    @staticmethod
    def open(ssh_username: str, ssh_server: str,
             ssh_key_file: Optional[Union[str, "Path"]] = None,
             ssh_password: Optional[str] = None,
             server_name: Optional[str] = None, quiet: bool = False,
             thread_safe: bool = False,
             allow_agent: bool = False) -> SSHConnection:
        ...

    @staticmethod
    def open(ssh_username: str, ssh_server: Optional[str] = "",
             ssh_key_file: Optional[Union[str, "Path"]] = None,
             ssh_password: Optional[str] = None,
             server_name: Optional[str] = None, quiet: bool = False,
             thread_safe: bool = False,
             allow_agent: bool = False):
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
        allow_agent: bool
            allow the use of the ssh-agent to connect. Will disable ssh_key_file.

        Warnings
        --------
        Do not use plain text passwords in production, they are great security
        risk!
        """
        if not ssh_server:
            return LocalConnection(
                ssh_server,
                ssh_username,
                pkey_file=ssh_key_file,
                server_name=server_name,
                quiet=quiet
            )
        elif allow_agent:
            ssh_key_file = None
            ssh_password = None
        elif ssh_key_file:
            ssh_password = None
        elif not ssh_password:
            ssh_password = getpass.getpass(prompt="Enter password: ")

        return SSHConnection(
            ssh_server,
            ssh_username,
            allow_agent=allow_agent,
            pkey_file=ssh_key_file,
            password=ssh_password,
            line_rewrite=True,
            server_name=server_name,
            quiet=quiet,
            thread_safe=thread_safe
        )
