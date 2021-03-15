"""Template module for all pathlib classes."""
import logging
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, FrozenSet, Generic, TypeVar

if TYPE_CHECKING:
    from ..typeshed import _SPATH

__all__ = ["PathlibABC"]

logging.getLogger(__name__)

# Python does not yet support higher order generics so this is devised to
# circumvent the problem, we must always define Generic with all possible
# return types
# problem discussion: https://github.com/python/typing/issues/548
# potentially use returns in the future github.com/dry-python/returns
_Pathlib1 = TypeVar("_Pathlib1")  # Union[Path, "SSHPath"]


class PathlibABC(ABC, Generic[_Pathlib1]):
    """`pathlib` module drop-in replacement base."""

    __name__: str
    __abstractmethods__: FrozenSet[str]

    @abstractmethod
    def Path(self, path: "_SPATH") -> _Pathlib1:
        """Provides API similar to pathlib.Path only for remote host.

        Only for Unix to Unix connections

        Parameters
        ----------
        path: :const:`ssh_utilities.typeshed._SPATH`
            provide initial path

        Returns
        -------
        SSHPath
            object representing remote path
        """
        raise NotImplementedError
