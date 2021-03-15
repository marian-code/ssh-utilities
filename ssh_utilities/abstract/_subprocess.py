"""Template module for all subprocess classes."""
import logging
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, FrozenSet, Generic, Optional, TypeVar

if TYPE_CHECKING:
    from ..typeshed import _CMD, _ENV, _FILE, _SPATH

__all__ = ["SubprocessABC"]

logging.getLogger(__name__)

# Python does not yet support higher order generics so this is devised to
# circumvent the problem, we must always define Generic with all possible
# return types
# problem discussion: https://github.com/python/typing/issues/548
# potentially use returns in the future github.com/dry-python/returns
_Subprocess1 = TypeVar("_Subprocess1")  # "CompletedProcess"


class SubprocessABC(ABC, Generic[_Subprocess1]):
    """`subprocess` module drop-in replacement base."""

    __name__: str
    __abstractmethods__: FrozenSet[str]

    @abstractmethod
    def run(self, args: "_CMD", *, suppress_out: bool,  # NOSONAR
            quiet: bool = True, bufsize: int = -1, executable: "_SPATH" = None,
            input: Optional[str] = None, stdin: "_FILE" = None,
            stdout: "_FILE" = None, stderr: "_FILE" = None,
            capture_output: bool = False, shell: bool = False,
            cwd: "_SPATH" = None, timeout: Optional[float] = None,
            check: bool = False, encoding: Optional[str] = None,
            errors: Optional[str] = None, text: Optional[bool] = None,
            env: "_ENV" = None,
            universal_newlines: bool = False
            ) -> _Subprocess1:
        """Excecute command on remote, has simillar API to subprocess run.

        Parameters
        ----------
        args : :const:`ssh_utilities.typeshed._CMD`
            string, Path-like object or a list of strings. If it is a list it
            will be joined to string with whitespace delimiter.
        suppress_out : bool
            whether to print command output to console, this is required
            keyword argument
        quiet : bool, optional
            whether to print other function messages, by default True
        bufsize : int, optional
            buffer size, 0 turns off buffering, 1 uses line buffering, and any
            number greater than 1 (>1) uses that specific buffer size. This
            applies ti underlying paramiko client as well as `stdin`, `stdout`
            and `stderr` PIPES, by default -1
        executable : :const:`ssh_utilities.typeshed._SPATH`, optional
            [description], by default None
        input : Optional[str], optional
            [description], by default None
        stdin : _FILE, optional
            [description], by default None
        stdout : _FILE, optional
            [description], by default None
        stderr : _FILE, optional
            [description], by default None
        capture_output : bool, optional
            if true then lightweight result object with same API as
            subprocess.CompletedProcess is returned. Same as passing PIPE to
            `stdout` and `stderr`. Both options cannot be used at the same
            time, by default False
        shell : bool, optional
            requests a pseudo terminal from server, by default False
        cwd : _SPATH, optional
            execute command in this directory, by default None
        timeout : Optional[float], optional
            set, by default None
        check : bool, optional
            checks for command return code if other than 0 raises
            CalledProcessError, by default False
        encoding : Optional[str], optional
            encoding to use when decoding remote output, default is utf-8,
            by default None
        errors : Optional[str], optional
            string that specifies how encoding and decoding errors are to be
            handled, see builtin function
            `open <https://docs.python.org/3/library/functions.html#open>`_
            documentation for more details, by default None
        text : Optional[bool], optional
            will select default encoding and open `stdin`, `stdout` and
            `stderr` streams in text mode. The default encoding, contrary to
            behaviour of `subprocess` module is not selected by
            `locale.getpreferredencoding(False)` but is always set to `utf-8`.
            By default None
        env : :const:`ssh_utilities.typeshed._ENV`, optional
            optinal environment variables that will be merged into the existing
            environment. This is different to `subprocess` behaviour which
            creates new environment with only specified variables,
            by default None
        universal_newlines : bool, optional
            an alias for text keyword argument, by default None

        Warnings
        --------
        New environment variables defined by `env` might get silently rejected
        by the server.

        Currentlly it is only possible to use `input` agrgument, not `stdin`
        and send data to process only once at the begining. It is still under
        developement

        Returns
        -------
        CompletedProcess
            if capture_output is true, returns lightweight result object with
            same API as subprocess.CompletedProcess

        Raises
        ------
        ValueError
            if `stdin` and `input` are specified at the same time
        ValueError
            if `capture_output` and `stdout` and/or `stderr` are specified at
            the same time
        ValueError
            if `text` or `universal_newlines` is used simultaneously with"
            `encoding` and/or `errors` arguments
        NotImplementedError
            if `stdin` or `executable` is used - work in progress
        TypeError
            if `stdin`, `stdout` or `stderr` arguments are of wrong type
        TypeError
            if `args` argument is of wrong type
        CalledProcessError
            if check is true and command exited with non-zero status
        TimeoutExpired
            if the command exceeded allowed run time
        """
        raise NotImplementedError
