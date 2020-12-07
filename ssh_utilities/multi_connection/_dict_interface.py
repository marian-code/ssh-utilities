"""Module providing dictionary interface for multi_connection."""

import logging
from copy import copy
from typing import (TYPE_CHECKING, Dict, ItemsView, KeysView, Optional, Tuple,
                    Union, ValuesView, TypeVar)
from collections.abc import MutableMapping

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

    _connections: Dict[str, "_CONN"]
    _share_connection: Dict[str, int]

    def __getitem__(self, key: str) -> "_CONN":
        return self._connections[key]

    def __delitem__(self, key: str) -> None:
        self._connections[key].close(quiet=True)
        self._connections.pop(key)
        self._share_connection.pop(key)

    def __setitem__(self, key: str, value: "_CONN"):
        self._add_one(value, key)

    def __contains__(self, item: str):
        return item in self._connections

    def __iter__(self):
        return self.keys()

    def __len__(self) -> int:
        return len(self._connections)

    def keys(self) -> KeysView[str]:
        """Iterate over registered key same as `dict.keys` method.

        Yields
        ------
        KeysView[str]
            key
        """
        return self._connections.keys()

    def values(self) -> ValuesView["_CONN"]:
        """Iterate over registered Connections same as `dict.values` method.

        Yields
        ------
        ValuesView[_CONN]
            `SSHConnection`/`LocalConnection`
        """
        return self._connections.values()

    def items(self) -> ItemsView[str, "_CONN"]:
        """Iterate over key, Connection pairs same as `dict.items` method.

        Yields
        ------
        ItemsView[str, _CONN]
            key, `SSHConnection`/`LocalConnection`
        """
        return self._connections.items()

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
        AttributeError
            if the input key is not present among the connections and default
            is not defined.
        """
        conn = self._connections.pop(key, *args)
        self._share_connection.pop(key, *args)
        return conn

    def popitem(self) -> Tuple[str, "_CONN"]:
        """Pops one key, connection pair from `MultiConnection`.

        Returns
        -------
        Tuple[str, _CONN]
            key, `SSHConnection`/`LocalConnection`  pair
        """
        key, conn = self._connections.popitem()
        self._share_connection.pop(key, None)
        return key, conn

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
        self._share_connection.clear()
        self.pool.shutdown()

    def _add_one(self, other: "_CONN",
                 key: Optional[str] = None):
        """Add one connecction to the undelying dictionary.

        Parameters
        ----------
        other: _CONN
            `SSHConnection` or `LocalConnection`
        key: Optional[str]
            if used connection is added under this key, else key is extracted
            from `connection.server_name` attribute

        Raises
        ------
        AttributeError
            if key is already pressent among registered connections
        """
        if key is None:
            key = other.server_name.lower()

        if key in self.keys():
            raise KeyError(f"Cannot register new Connection under key: {key}, "
                           f"change Connection.server_name attribute or pass "
                           f"in another key")
        self._connections.update({key: other})

    def _add_multi(self, other: "MultiConnection"):
        """Register multiple new connections."""
        self._share_connection.update(other._share_connection)
        self._connections.update(other._connections)
