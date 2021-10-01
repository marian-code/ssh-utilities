"""Template module for all builtins classes."""
import logging
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, FrozenSet, Generic, Optional, TypeVar

if TYPE_CHECKING:
    from ..typeshed import _SPATH

__all__ = ["BuiltinsABC"]

logging.getLogger(__name__)

# Python does not yet support higher order generics so this is devised to
# circumvent the problem, we must always define Generic with all possible
# return types
# problem discussion: https://github.com/python/typing/issues/548
# potentially use returns in the future github.com/dry-python/returns
_Builtins1 = TypeVar("_Builtins1")  # Union[IO, "SFTPFile"]


class BuiltinsABC(ABC, Generic[_Builtins1]):
    """Python builtins drop-in replacement base."""

    __name__: str
    __abstractmethods__: FrozenSet[str]

    @abstractmethod
    def open(self, filename: "_SPATH", mode: str = "r", buffering: int = -1,
             encoding: Optional[str] = None, errors: Optional[str] = None,
             newline: Optional[str] = None
             ) -> _Builtins1:
        """Opens remote file, works as python open function.

        Can be used both as a function or a decorator.

        Parameters
        ----------
        filename: :const:`ssh_utilities.typeshed._SPATH`
            path to file to be opened
        mode: str
            select mode to open file. Same as python open modes
        encoding: Optional[str]
            encoding type to decode file bytes stream
        buffering: int
            buffer size, 0 turns off buffering, 1 uses line buffering, and any
            number greater than 1 (>1) uses that specific buffer size
        errors: Optional[str]
            string that specifies how encoding and decoding errors are to be
            handled, see builtin function
            `open <https://docs.python.org/3/library/functions.html#open>`_
            documentation for more details
        newline: Optional[str]
            this parameter is not used in ssh implementation

        Raises
        ------
        FileNotFoundError
            when mode is 'r' and file does not exist
        """
        raise NotImplementedError
