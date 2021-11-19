"""Module that provides delegation callables.

These callables defer calls from MultiConnection to individual connections.
"""

import logging
from typing import TYPE_CHECKING, Union
from ..abstract import OsPathABC

if TYPE_CHECKING:
    from ..abstract import (BuiltinsABC, ConnectionABC, OsABC,
                            PathlibABC, ShutilABC, SubprocessABC)
    from ..local import LocalConnection
    from ..remote import SSHConnection
    from .multi_connection import MultiConnection

    ABCs = Union[BuiltinsABC, ConnectionABC, OsABC, OsPathABC, PathlibABC,
                 ShutilABC, SubprocessABC]

    _CONN = Union[SSHConnection, LocalConnection]

__all__ = ["Inner"]

log = logging.getLogger(__name__)


class delegated:
    """Callable that delegates method call to all open connections.

    This way the base class methods are reimplemented programatically and
    there is no code duplication prone to errors.

    Parameters
    ----------
    method_name : str
        name of the method to be called
    multi_connection : MultiConnection
        mutliconnection instace that holds all the connections
    inner_class : str
        name of the inner class that mathod belongs to

    See also
    --------
    :class:`ssh_utilities.multi_conncection.MultiConnection`
    """

    def __init__(self, method_name: str, parent_ref: "ABCs",
                 inner_class: str) -> None:
        self._method_name = method_name
        self._parent_ref = parent_ref
        self._inner_class = inner_class
        self._property = False

    def is_property(self):
        """Set this callabel to behave like a property."""
        self._property = True

    def __call__(self, *args, **kwargs):
        """Call the appropriate method on all connections asynchronously."""
        iterables = [(c, *args, *kwargs)
                     for c in self._parent_ref.mc.values()]
        return self._parent_ref.mc.pool.map(self._call, *zip(*iterables))

    def _call(self, c: "_CONN", *args, **kwargs):
        """Make method calls for each of the connections."""
        #print(c, args, kwargs)
        method = getattr(getattr(c, self._inner_class), self._method_name)
        #print(method, self._property)
        if self._property:
            return method
        else:
            return method(*args, **kwargs)


# TODO maybe this is too deep magic? still not sure if we are returning
# TODO actual class or class instance, this can have dangerous consequences!
def Inner(abc_parent: "ABCs", multi_connection: "MultiConnection"):  # NOSONAR
    """Class implementing the inner classes of connection object.

    Reimplementation of abstract methods is done auto-magically.
    This function is esentially a factory for the inner classes of connection.

    This makes the class hierarchy 'transposed' instead of this:

    >>> [Connection1.method1(), Connection2.method1()]
    >>> [Connection1.method2(), Connection2.method2()]

    we now essentialy have:

    >>> method1[Connection1, Connection2]
    >>> method2[Connection1, Connection2]

    The methods become classes and each one holds reference to all
    open connections

    Parameters
    ----------
    abc_parent : ABCs
        The abstract parent that is going to be reimplemented
    multi_connection : MultiConnection
        reference to MultiConnection object

    See also
    --------
    :class:`ssh_utilities.multi_conncection.MultiConnection`
    """
    new_method: Union[property, delegated]

    implemented = set()
    abc_parent.mc = multi_connection  # type: ignore
    for name in abc_parent.__abstractmethods__:
        if hasattr(abc_parent, name):
            inner_class = abc_parent.__name__.replace("ABC", "").lower()
            attr = getattr(abc_parent, name)
            new_method = delegated(name, abc_parent, inner_class)
            #print(name, inner_class, isinstance(attr, property))
            # * special treatment for os.path subclass
            #if name == "path" and inner_class == "os":
            #    new_method = Inner(OsPathABC, multi_connection)
            if isinstance(attr, property):
                new_method.is_property()
                new_method = property(new_method.__call__,
                                      attr.__set__, attr.__delattr__)

            setattr(abc_parent, name, new_method)

            implemented.add(name)
    abc_parent.__abstractmethods__ = frozenset(
        abc_parent.__abstractmethods__ - implemented
    )
    return abc_parent()  # type: ignore
