"""module providing dictionary interface for multi_connection."""

import logging
from typing import (TYPE_CHECKING, Dict, ItemsView, KeysView, Optional, Tuple,
                    Union, ValuesView)

if TYPE_CHECKING:
    from ..local import LocalConnection
    from ..remote import SSHConnection
    from .multi_connection import MultiConnection

    _CONN = Union[SSHConnection, LocalConnection]


log = logging.getLogger(__name__)


class DictInterface:
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
        return self._connections.keys()

    def values(self) -> ValuesView["_CONN"]:
        return self._connections.values()

    def items(self) -> ItemsView[str, "_CONN"]:
        return self._connections.items()

    def pop(self, key: str, *args) -> "_CONN":
        conn = self._connections.pop(key, *args)
        self._share_connection.pop(key, *args)
        return conn

    def popitem(self) -> Tuple[str, "_CONN"]:
        key, conn = self._connections.popitem()
        self._share_connection.pop(key, None)
        return key, conn

    def update(self, other: "MultiConnection"):
        self._add_multi(other)

    def get(self, key: str, *args) -> Optional["_CONN"]:
        return self._connections.get(key, *args)

    def copy(self):
        return self

    def clear(self):
        self.close()
        self._connections.clear()
        self._share_connection.clear()
        self.pool.shutdown()

    def _add_one(self, other: "_CONN",
                 key: Optional[str] = None):

        if key is None:
            key = other.server_name.lower()
        self._connections.update({key: other})

    def _add_multi(self, other: "MultiConnection"):
        self._share_connection.update(other._share_connection)
        self._connections.update(other._connections)
