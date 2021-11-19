"""The main module with toplevel Connection class.

The connection class is the main public class that initializes local
or remote connection classes as needed abcd on input arguments.
"""

from collections import defaultdict, deque
import logging
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Deque, TYPE_CHECKING, Dict, List, Optional, SupportsFloat, Union

from ..abstract import (BuiltinsABC, ConnectionABC, OsABC, PathlibABC, ShutilABC,
                   SubprocessABC)
from ..connection import Connection
from ..local import LocalConnection
from ..remote import SSHConnection
from ._delegated import Inner
from ._dict_interface import DictInterface
from ._persistence import Pesistence

if TYPE_CHECKING:
    from ..abstract import (_BUILTINS_MULTI, _OS_MULTI, _PATHLIB_MULTI,
                       _SHUTIL_MULTI, _SUBPROCESS_MULTI)

    _CONN = Union[SSHConnection, LocalConnection]

__all__ = ["MultiConnection"]

log = logging.getLogger(__name__)


class MultiConnection(DictInterface, Pesistence, ConnectionABC):
    """Wrapper for multiple connections.

    All methods work exactly the same as for single connections, only now they
    return Generators instead of their respective values.
    Can be used to prallelize connections or to share one ssh connection or
    just to cleverly manage pool of connections.

    Connection can be effectively made parallel by passig same key more times
    to the constructor or by other methods. Namely `__add__`, `__setitem__`,
    `update`. This means that in fact under each key a pool of connections can
    be registered. These are organized in `collections.deque`.

    The `MultiConnection` supports dict interface but with few differences as
    more connections can be registered under one key. Basically you can think
    of it as a distionary which allows duplicit keys. All the dict methods
    work as expected. See expamples section or docs for more detailes.    

    Parameters
    ----------
    ssh_servers : Union[List[str], str]
        list od ssh srevers to connect to
    local : Union[List[bool], bool], optional
        bool or list of bools specifying if the respective connection(s),
        should be local or remote by default False
    quiet : bool, optional
        bool or a list of bools specifing if login messages should be printed,
        on individula connections initialization by default False
    thread_safe : Union[List[bool], bool], optional
        bool or a list of bools specifying if respective connection(s) should,
        be made thead safe or not by default False

    Examples
    --------
    Make connection parallel

    >>> from ssh_utilities import MultiConnection
    >>> # this will create two connection instances both connected to server1
    >>> Multiconnection([server1, server1])

    This results in MultiConnection with a pool of two connections to `server1`
    registered under key `server1`

    Dict intreface

    >>> from ssh_utilities import MultiConnection
    >>> mc = Multiconnection([server1, server1])
    >>> # we always implement normal dict-like method which works as expected
    >>> mc.get(server1)
    >>> <SSHConnection instance connected to server1>
    >>> # in each case there is always also a method with `_all` suffix by
    >>> # which you can acces the whole pool of connections registered under
    >>> # the key
    >>> mc.get_all(server1)
    >>> <deque with two independent SSHConnections to server 1>
    """

    _builtins: "_BUILTINS_MULTI"
    _os: "_OS_MULTI"
    _pathlib: "_PATHLIB_MULTI"
    _shutil: "_SHUTIL_MULTI"
    _subprocess: "_SUBPROCESS_MULTI"
    _connections: Dict[str, Deque["_CONN"]]

    def __init__(self, ssh_servers: Union[List[str], str],
                 local: Union[List[bool], bool] = False, quiet: bool = False,
                 thread_safe: Union[List[bool], bool] = False,
                 allow_agent: Union[List[bool], bool] = True) -> None:

        # TODO somehow adjust number of workers if connection are deleted or
        # TODO added
        self.pool = ThreadPoolExecutor(max_workers=None)

        if not isinstance(ssh_servers, list):
            ssh_servers = [ssh_servers]
        if not isinstance(local, list):
            local = [local] * len(ssh_servers)
        if not isinstance(thread_safe, list):
            thread_safe = [thread_safe] * len(ssh_servers)
        if not isinstance(allow_agent, list):
            allow_agent = [allow_agent] * len(ssh_servers)

        self._connections = defaultdict(deque)
        for ss, l, ts in zip(ssh_servers, local, thread_safe):
            self._connections[ss].append(
                Connection(ss, local=l, quiet=quiet, thread_safe=ts)
            )

        # init submodules
        self._builtins = Inner(BuiltinsABC, self)  # type: ignore
        self._os = Inner(OsABC, self)  # type: ignore
        self._pathlib = Inner(PathlibABC, self)  # type: ignore
        self._shutil = Inner(ShutilABC, self)  # type: ignore
        self._subprocess = Inner(SubprocessABC, self)  # type: ignore

    @property
    def builtins(self) -> "_BUILTINS_MULTI":
        """Inner class providing access to substitutions for python builtins.

        :type: .abc.Builtins
        """
        return self._builtins

    @property
    def os(self) -> "_OS_MULTI":
        """Inner class providing access to substitutions for python os module.

        :type: .abc.Os
        """
        return self._os

    @property
    def pathlib(self) -> "_PATHLIB_MULTI":
        """Inner class providing access to substitutions for pathlib module.

        :type: .abc.Pathlib
        """
        return self._pathlib

    @property
    def shutil(self) -> "_SHUTIL_MULTI":
        """Inner class providing access to substitutions for shutil module.

        :type: .abc.Shutil
        """
        return self._shutil

    @property
    def subprocess(self) -> "_SUBPROCESS_MULTI":
        """Inner class providing access to substitutions for subprocess module.

        :type: .abc.Subprocess
        """
        return self._subprocess

    def close(self, *, quiet: bool = True):
        for c in self.values_all():
            c.close(quiet=quiet)

    get_available_hosts = Connection.get_available_hosts
    add_hosts = Connection.add_hosts

    def __del__(self):
        self.close(quiet=True)

    def __str__(self) -> str:
        return Pesistence.__str__(self)

    def to_dict(self) -> Dict[int, Dict[str, Optional[Union[str, bool,
                                                            int, None]]]]:
        return Pesistence.to_dict(self)

    # TODO will this propagate to the delegated classes?
    def __add__(self, other: Union["_CONN",
                                   "MultiConnection"]) -> "MultiConnection":

        if isinstance(other, MultiConnection):
            self._add_multi(other)
        else:
            self._add_one(other)

        return self

    __radd__ = __add__
    __iadd__ = __add__

    # TODO to be implemented
    def __pow__(self, power: SupportsFloat):
        ...

    def ssh_log(self, log_file: Union[Path, str] = Path("paramiko.log"),
                level: str = "WARN"):
        ...
