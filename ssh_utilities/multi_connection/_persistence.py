"""Module providing persistance methods for multi_connection.

Adds the ability to persist object using:
- str
- dictionary
- pickle
- deepcopy
"""

import logging
from json import dumps, loads
from typing import (TYPE_CHECKING, Deque, Dict, List, Optional, Tuple, Union,
                    ValuesView)

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

    _connections: Dict[str, Deque["_CONN"]]

    def __str__(self) -> str:
        return dumps(self.to_dict())

    def __repr__(self):
        self.__str__()

    def __deepcopy__(self, memodict: dict = {}):
        """On deepcopy we create new instance as this is simpler and safer."""
        return self.from_dict(self.to_dict())

    def __getstate__(self):
        """Gets the state of object for pickling."""
        return self.to_dict()

    def __setstate__(self, state: dict):
        """Initializes the object after load from pickle."""
        ssh_servers, local, thread_safe, allow_agent = (
            self._parse_persistence_dict(state)
        )

        self.__init__(ssh_servers, local, quiet=True,  # type: ignore
                      thread_safe=thread_safe, allow_agent=allow_agent)

    def to_dict(self) -> Dict[int, Dict[str, Optional[Union[str, bool,
                                                            int, None]]]]:
        """Saves all the importatnt info from object to dictonary.

        Returns
        -------
        Dict[int, Dict[str, Optional[Union[str, bool, int, None]]]]
            dictionary representing the object
        """
        conns = {}
        for i, v in enumerate(self.values_all()):
            json = v.to_dict()
            conns[i] = json

        return conns

    @staticmethod
    def _parse_persistence_dict(d: dict) -> Tuple[List[str], List[int],
                                                  List[bool], List[bool]]:
        """Parses dictionary produced by `to_dict` method.

        Parameters
        ----------
        d : dict
            dictionary of values needed to reinitialize the class

        Returns
        -------
        Tuple[List[str], List[int], List[bool], List[bool]]
            Tuple of lists with parsed information
        """
        ssh_servers = []
        local = []
        thread_safe = []
        allow_agent = []
        for j in d.values():
            ssh_servers.append(j.pop("server_name"))
            thread_safe.append(j.pop("thread_safe"))
            local.append(not bool(j.pop("address")))
            allow_agent.append(j.pop("allow_agent"))

        return ssh_servers, local, thread_safe, allow_agent

    @classmethod
    def from_dict(cls, json: dict, quiet: bool = False
                  ) -> "MultiConnection":
        """Initializes Connection from str.

        String must be formated as defined by `base.ConnectionABC._to_str`
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
        ssh_servers, local, thread_safe, allow_agent = (
            cls._parse_persistence_dict(json)
        )

        return cls(ssh_servers, local, quiet=quiet,  # type: ignore
                   thread_safe=thread_safe, allow_agent=allow_agent)

    @classmethod
    def from_str(cls, string: str, quiet: bool = False
                 ) -> "MultiConnection":
        """Initializes Connection from str.

        String must be formated as defined by `base.ConnectionABC._to_str`
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

    def values_all(self) -> ValuesView["_CONN"]:
        """Will be reimplemented by dict interface."""
        pass
