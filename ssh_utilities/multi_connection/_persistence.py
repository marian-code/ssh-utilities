"""Module providing persistance methods for multi_connection.

Adds the ability to persist object using:
- str
- dictionary
- pickle
- deepcopy
"""

import logging
from json import dumps, loads
from typing import TYPE_CHECKING, Dict, List, Optional, Tuple, Union

if TYPE_CHECKING:
    from ..local import LocalConnection
    from ..remote import SSHConnection
    from .multi_connection import MultiConnection

    _CONN = Union[SSHConnection, LocalConnection]


log = logging.getLogger(__name__)


class Pesistence:
    """Class providing persistance methods to MultiConnection.

    Adds the ability to persist object using:
    - str
    - dictionary
    - pickle
    - deepcopy

    See also
    --------
    :class:`ssh_utilities.multi_conncection.MultiConnection`
    """

    _connections: Dict[str, "_CONN"]
    _share_connection: Dict[str, int]

    def __str__(self) -> str:
        return dumps(self.to_dict())

    def __repr__(self):
        self.__str__()

    def __deepcopy__(self, memodict: dict = {}):
        return MultiConnection.from_dict(self.to_dict())

    def __getstate__(self):
        return self.to_dict()

    def __setstate__(self, state: dict):

        ssh_servers, share_connection, local, thread_safe = (
            self._parse_persistence_dict(state)
        )

        self.__init__(ssh_servers, local, quiet=True,  # type: ignore
                      thread_safe=thread_safe,
                      share_connection=share_connection)

    def to_dict(self) -> Dict[int, Dict[str, Optional[Union[str, bool,
                                                            int, None]]]]:
        conns = {}
        for i, (v, sc) in enumerate(zip(self._connections.values(),
                                        self._share_connection.values())):
            json = v.to_dict()
            json["share_connection"] = sc
            conns[i] = json

        return conns

    @staticmethod
    def _parse_persistence_dict(d: dict) -> Tuple[List[str], List[int],
                                                  List[bool], List[bool]]:

        share_connection = []
        ssh_servers = []
        local = []
        thread_safe = []
        for j in d.values():
            share_connection.append(j.pop("share_connection"))
            ssh_servers.append(j.pop("server_name"))
            thread_safe.append(j.pop("thread_safe"))
            local.append(not bool(j.pop("address")))

        return ssh_servers, share_connection, local, thread_safe

    @classmethod
    def from_dict(cls, json: dict, quiet: bool = False
                  ) -> "MultiConnection":
        """Initializes Connection from str.

        String must be formated as defined by `base.ConnectionABC.to_str`
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

        Raises
        ------
        KeyError
            if required key is missing from string
        """
        ssh_servers, share_connection, local, thread_safe = (
            cls._parse_persistence_dict(json)
        )

        return cls(ssh_servers, local, quiet=quiet,  # type: ignore
                   thread_safe=thread_safe,
                   share_connection=share_connection)

    @classmethod
    def from_str(cls, string: str, quiet: bool = False
                 ) -> "MultiConnection":
        """Initializes Connection from str.

        String must be formated as defined by `base.ConnectionABC.to_str`
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
