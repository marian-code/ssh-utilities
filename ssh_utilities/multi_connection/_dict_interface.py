"""Module providing dictionary interface for multi_connection."""

import logging
from collections.abc import MutableMapping
from copy import copy
from typing import (TYPE_CHECKING, Deque, Dict, ItemsView, KeysView, Optional,
                    Tuple, TypeVar, Union, ValuesView)

if TYPE_CHECKING:
    from ..local import LocalConnection
    from ..remote import SSHConnection
    from .multi_connection import MultiConnection

    _CONN = Union[SSHConnection, LocalConnection]
    _DictInterface1 = TypeVar("_DictInterface1")

log = logging.getLogger(__name__)


class DictInterface(MutableMapping):
    """Class providing dictionary interface methods to MultiConnection.

    See also
    --------
    :class:`ssh_utilities.multi_conncection.MultiConnection`
    """

    _connections: Dict[str, Deque["_CONN"]]

    def __getitem__(self, key: str) -> "_CONN":
        # always rotate before returning this way we ensure that we return the
        # connection that has the least probability of still being used.
        # The connection that is used is effecitvely moved to then end of the
        # deque
        self._connections[key].rotate()
        return self._connections[key][0]

    def __delitem__(self, key: str) -> None:
        # this only deletes key if pool of connection that it points to
        # is empty
        c = self._connections[key].pop()

        # if zero connection remain in pool delete the key in connections
        # dictionary  remove the key
        if len(self._connections[key]) == 0:
            self._connections.pop(key)

        c.close(quiet=True)

    def __setitem__(self, key: str, value: "_CONN"):
        self._add_one(value, key)

    def __contains__(self, item: str):
        return item in self._connections

    def __iter__(self):
        return iter(self.keys())

    def __len__(self) -> int:
        return len(self._connections)

    def len_all(self) -> int:
        return len(self.keys_all())

    def keys(self) -> KeysView[str]:
        """Iterate over registered key same as `dict.keys` method.

        This method iterates only over unique keys.

        Warnings
        --------
        MultiConnection has seemingly duplicate keys but this is caused by
        the fact that each key can have multiple connections registered under
        itself this way connection to some host can be effectively made
        parallel.

        Yields
        ------
        KeysView[str]
            unique keys poining to connection pools

        See Also
        --------
        :meth:`keys_all` iterate through key duplicates.
        """
        return self._connections.keys()

    def keys_all(self) -> KeysView[str]:
        """Iterate over registered key same as `dict.keys` method.

        This method returnes each key as many times as many connections are
        registered in its pool.

        Warnings
        --------
        MultiConnection has seemingly duplicate keys but this is caused by
        the fact that each key can have multiple connections registered under
        itself this way connection to some host can be effectively made
        parallel.

        Yields
        ------
        KeysView[str]
            key

        See Also
        --------
        :meth:`keys_all` iterate through unique keys.
        """
        for key, conns in self._connections.items():
            for _ in conns:
                yield key

    def values(self) -> ValuesView["_CONN"]:
        """Iterate over registered Connections same as `dict.values` method.

        This method returns only one connection for each registered key.

        Warnings
        --------
        MultiConnection has seemingly duplicate keys but this is caused by
        the fact that each key can have multiple connections registered under
        itself this way connection to some host can be effectively made
        parallel.

        Yields
        ------
        ValuesView[_CONN]
            `SSHConnection`/`LocalConnection`

        See Also
        --------
        :meth:`values_all` iterate all connections not only one for each key.
        """
        for conn_pool in self._connections.values():
            yield conn_pool[0]

    def values_all(self) -> ValuesView["_CONN"]:
        """Iterate over registered Connections same as `dict.values` method.

        This method iterates all connections for each of the keys.

        Warnings
        --------
        MultiConnection has seemingly duplicate keys but this is caused by
        the fact that each key can have multiple connections registered under
        itself this way connection to some host can be effectively made
        parallel.

        Yields
        ------
        ValuesView[_CONN]
            `SSHConnection`/`LocalConnection`

        See Also
        --------
        :meth:`values` output only one connection for each key.
        """
        for conn_pool in self._connections.values():
            for c in conn_pool:
                yield c

    def items(self) -> ItemsView[str, "_CONN"]:
        """Iterate over key, Connection pairs same as `dict.items` method.

        This method returns only one connection for each registered key.

        Warnings
        --------
        MultiConnection has seemingly duplicate keys but this is caused by
        the fact that each key can have multiple connections registered under
        itself this way connection to some host can be effectively made
        parallel.

        Yields
        ------
        ItemsView[str, _CONN]
            key, `SSHConnection`/`LocalConnection`

        See Also
        --------
        :meth:`items_all` iterate all connection coresponding to a key
        """
        return self._connections.items()

    def items_all(self) -> ItemsView[str, "_CONN"]:
        """Iterate over key, Connection pairs same as `dict.items` method.

        This returns all connections for each registered key.

        Warnings
        --------
        MultiConnection has seemingly duplicate keys but this is caused by
        the fact that each key can have multiple connections registered under
        itself this way connection to some host can be effectively made
        parallel.

        Yields
        ------
        ItemsView[str, _CONN]
            key, `SSHConnection`/`LocalConnection`

        See Also
        --------
        :meth:`items_all` iterate only one connection per key
        """
        for key, conns in self._connections.items():
            for c in conns:
                yield key, c

    def pop(self, key: str, *args) -> "_CONN":
        """Pop one connection from `MultiConnection` object based on key.

        Parameters
        ----------
        key: str
            key denoting the connection
        default: Any, optional
            optianal value returned if key is not pressent

        Returns
        -------
        _CONN
            `SSHConnection` or `LocalConnection` object

        Raises
        ------
        KeyError
            if the input key is not present among the connections and default
            is not defined.
        """
        conn_pool = self._connections.pop(key, *args)
        conn = conn_pool.pop()
        if len(conn_pool) > 0:
            self._connections[key] = conn_pool

        return conn

    def pop_all(self, key: str, *args) -> Deque["_CONN"]:
        """Pop pool of connections from `MultiConnection` object based on key.

        Parameters
        ----------
        key: str
            key denoting the connection
        default: Any, optional
            optianal value returned if key is not pressent

        Returns
        -------
        Deque[_CONN]
            `SSHConnection` or `LocalConnection` objects in deque container  

        Raises
        ------
        KeyError
            if the input key is not present among the connections and default
            is not defined.
        """
        return self._connections.pop(key, *args)

    def popitem(self) -> Tuple[str, "_CONN"]:
        """Pops one key, connection pair from `MultiConnection`.

        Returns
        -------
        Tuple[str, _CONN]
            key, `SSHConnection`/`LocalConnection`  pair
        """
        key, conn_pool = self._connections.popitem()
        conn = conn_pool.pop()
        if len(conn_pool) > 0:
            self._connections[key] = conn_pool

        return key, conn

    def popitem_all(self) -> Tuple[str, Deque["_CONN"]]:
        """Pops one key, connection pool pair from `MultiConnection`.

        Returns
        -------
        Tuple[str,  Deque[_CONN]]
            key,  Deque[`SSHConnection`]/ Deque[`LocalConnection`]  pair
        """
        return self._connections.popitem()

    def update(self, other: "MultiConnection"):
        """Updates `Multiconnection` with another `Multiconnection`.

        This only merges underlying dictionaries holding connections

        Parameters
        ----------
        other : `MultiConnection`
            the added object of same type as self
        """
        self._add_multi(other)

    def get(self, key: str, *args) -> Optional["_CONN"]:
        """Get one connection from `MultiConnection` object based on key.

        This will return only one connection from pool registered under key.

        Parameters
        ----------
        key: str
            key denoting the connection
        default: Any, optional
            optianal value returned if key is not pressent

        Returns
        -------
        _CONN
            `SSHConnection` or `LocalConnection` object shallow copy

        Raises
        ------
        KeyError
            if the input key is not present among the connections and default
            is not defined.
        """
        conn_pool = self._connections.get(key, *args)
        conn_pool.rotate()
        return conn_pool[0]

    def get_all(self, key: str, *args) -> Optional[Deque["_CONN"]]:
        """Get pool of connections from `MultiConnection` object based on key.

        This will return the all the connections registered under key orgainzed
        in `collections.deque`

        Parameters
        ----------
        key: str
            key denoting the connection pool
        default: Any, optional
            optianal value returned if key is not pressent

        Returns
        -------
        _CONN
            `SSHConnection` or `LocalConnection` object shallow copy

        Raises
        ------
        AttributeError
            if the input key is not present among the connections and default
            is not defined.
        """
        return self._connections.get(key, *args)

    def copy(self: "_DictInterface1") -> "_DictInterface1":
        """Get a shallow copy of `MultiConnection`.

        Returns
        -------
        `MultiConnection`
            MultiConnection object shallow copy
        """
        return copy(self)

    def clear(self):
        """Close and delete all underlying connections."""
        self.close()
        self._connections.clear()
        self.pool.shutdown()

    def _add_one(self, other: "_CONN",
                 key: Optional[str] = None):
        """Add one connecction to the underlying dictionary.

        Parameters
        ----------
        other: _CONN
            `SSHConnection` or `LocalConnection`
        key: Optional[str]
            if used connection is added under this key, else key is extracted
            from `connection.server_name` attribute

        Warnings
        --------
        If key is already pressent among registered connections no KeyError is
        raised as one would expect in dictionary but instead connection is
        added to the pool of connections to the specific host
        """
        if key is None:
            key = other.server_name.lower()

        self._connections[key].append(other)

    def _add_multi(self, other: "MultiConnection"):
        """Register multiple new connections."""
        for key, conn in other.items_all():
            self._connections[key].append(conn)
