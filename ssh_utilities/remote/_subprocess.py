"""Remote version of subprocess module."""

import logging
import os
import socket
import sys
from io import BytesIO, StringIO, TextIOBase
from pathlib import Path
from subprocess import DEVNULL, PIPE, STDOUT
from typing import TYPE_CHECKING, Optional, TextIO, Union

from ..base import SubprocessABC
from ..constants import C, R, Y
from ..exceptions import CalledProcessError, TimeoutExpired
from ..utils import CompletedProcess, lprint
from ._connection_wrapper import check_connections

if TYPE_CHECKING:
    from ..typeshed import _CMD, _ENV, _FILE, _SPATH
    from .remote import SSHConnection

__all__ = ["Subprocess", "PIPE", "STDOUT", "DEVNULL"]

log = logging.getLogger(__name__)


class Subprocess(SubprocessABC):
    """Class with similar API to subprocess module.

    See also
    --------
    :class:`ssh_utilities.local.Subprocess`
        local version of class with same API
    """

    def __init__(self, connection: "SSHConnection") -> None:
        self.c = connection

    # TODO WORKS weird on AIX only first/last line of output
    @check_connections(exclude_exceptions=(TypeError, CalledProcessError))
    def run(self, args: "_CMD", *, suppress_out: bool, quiet: bool = True,
            bufsize: int = -1, executable: "_SPATH" = None,
            input: Optional[str] = None, stdin: "_FILE" = None,
            stdout: "_FILE" = None, stderr: "_FILE" = None,
            capture_output: bool = False, shell: bool = False,
            cwd: "_SPATH" = None, timeout: Optional[float] = None,
            check: bool = False, encoding: Optional[str] = None,
            errors: Optional[str] = None, text: Optional[bool] = None,
            env: Optional["_ENV"] = None, universal_newlines: bool = False
            ) -> CompletedProcess:
        """Excecute command on remote, has simillar API to subprocess run.

        Parameters
        ----------
        args : _CMD
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
        executable : _SPATH, optional
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
        env : Optional[_ENV], optional
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
        exception
            [description]
        CalledProcessError
            if check is true and command exited with non-zero status
        TimeoutExpired
            if the command exceeded allowed run time
        """
        command: str
        stdout_pipe: Union[BytesIO, StringIO, TextIO]
        stderr_pipe: Union[BytesIO, StringIO, TextIO]

        # init limited printing
        lprnt = lprint(quiet=quiet)

        if executable:
            raise NotImplementedError("executable argument is not implemented")

        if input and stdin:
            raise ValueError("input and stdin arguments may not be used at "
                             "the same time")
        if capture_output:
            if stdout or stderr:
                raise ValueError("capture_output may not be used with "
                                 "stdout or/and stderr")
            else:
                stdout = PIPE
                stderr = PIPE
        if text or universal_newlines:
            if encoding or errors:
                raise ValueError("text or universal_newlines may not be used "
                                 "with encoding and/or errors arguments")
            else:
                encoding = "utf-8"
                errors = "strict"
        else:
            if encoding and not errors:
                errors = "strict"
            else:  # only for typechecker otherwise not needed
                errors = ""

        if not stdin:
            stdin_pipe = sys.stdin
        elif stdin == DEVNULL:
            stdin_pipe = open(os.devnull, "w")
        elif stdin == PIPE:
            raise NotImplementedError
        elif isinstance(stdin, int):
            stdin_pipe = os.fdopen(stdin, encoding=encoding, errors=errors)
        elif isinstance(stdin, TextIOBase):
            pass
        else:
            raise TypeError("stdin argument is of unsupported type")

        if not stdout:
            stdout_pipe = sys.stdout
        elif stdout == DEVNULL:
            stdout_pipe = open(os.devnull, "w")
        elif stdout == PIPE:
            if encoding:
                stdout_pipe = StringIO()
            else:
                stdout_pipe = BytesIO()
        elif isinstance(stdout, int):
            stdout_pipe = os.fdopen(stdout, encoding=encoding, errors=errors)
        elif isinstance(stdout, TextIOBase):
            stdout_pipe = stdout
        else:
            raise TypeError("stdout argument is of unsupported type")

        if not stderr:
            stderr_pipe = sys.stderr
        elif stderr == DEVNULL:
            stderr_pipe = open(os.devnull, "w")
        elif stderr == PIPE:
            if encoding:
                stderr_pipe = StringIO()
            else:
                stderr_pipe = BytesIO()
        elif isinstance(stderr, int):
            stderr_pipe = os.fdopen(stderr, encoding=encoding, errors=errors)
        elif stderr == STDOUT:
            stderr_pipe = stdout_pipe
        elif isinstance(stderr, TextIOBase):
            stderr_pipe = stderr
        else:
            raise TypeError("stderr argument is of unsupported type")

        if isinstance(args, list):
            if isinstance(args[0], Path):
                args[0] = self.c._path2str(args[0])

            command = " ".join(args)
        elif isinstance(args, Path):
            command = self.c._path2str(args)
        elif isinstance(args, str):
            command = args
        else:
            raise TypeError("process arguments are of wrong type")

        commands = command.split(" && ")
        if len(commands) == 1:
            lprnt(f"{Y}Executing command on remote:{R} {command}\n")
        else:
            lprnt(f"{Y}Executing commands on remote:{R} {commands[0]}")
            for c in commands[1:]:
                lprnt(" " * 30 + c)

        # change work directory for command execution
        if cwd:
            command = f"cd {self.c._path2str(cwd)} && {command}"

        cp = CompletedProcess(bytes_out=not encoding)
        try:
            # create output object
            cp.args = args

            # carry out command
            ssh_stdin, ssh_stdout, ssh_stderr = self.c.c.exec_command(
                command, bufsize=bufsize, timeout=timeout, get_pty=shell,
                environment=env)

            if input:
                ssh_stdin.write(input)
                ssh_stdin.flush()

            if stdout_pipe or stderr_pipe:

                # loop until channels are exhausted
                while (not ssh_stdout.channel.exit_status_ready() and
                       not ssh_stderr.channel.exit_status_ready()):

                    # get data when available
                    if ssh_stdout.channel.recv_ready():
                        data = ssh_stdout.channel.recv(1024)
                        if encoding:
                            data_dec = str(data, encoding, errors)
                            stdout_pipe.write(data_dec)  # type: ignore
                            cp.stdout += data_dec  # type: ignore
                        else:
                            stdout_pipe.write(data)
                            cp.stdout += data

                    if ssh_stderr.channel.recv_stderr_ready():
                        data = ssh_stderr.channel.recv_stderr(1024)
                        if encoding:
                            data_dec = str(data, encoding, errors)
                            stderr_pipe.write(data_dec)  # type: ignore
                            cp.stderr += data_dec  # type: ignore
                        else:
                            stderr_pipe.write(data)
                            cp.stderr += data

                # strip unnecessary newlines
                cp.stdout = cp.stdout.rstrip()
                cp.stderr = cp.stderr.rstrip()

                # get command return code
                cp.returncode = ssh_stdout.channel.recv_exit_status()

                # check if return code is 0
                if check:
                    cp.check_returncode()

                # print command stdout
                if not suppress_out:
                    lprnt(f"{C}Printing remote output\n{'-' * 111}{R}")
                    lprnt(cp.stdout)
                    lprnt(f"{C}{'-' * 111}{R}\n")

                if not capture_output:
                    cp.stdout = ""
                    cp.stderr = ""

                return cp
            else:

                # check if return code is 0, else raise exception
                if check:
                    returncode = ssh_stdout.channel.recv_exit_status()
                    if returncode != 0:
                        raise CalledProcessError(returncode, command, "", "")

                return cp
        except socket.timeout:
            if isinstance(timeout, float):
                raise TimeoutExpired(args, timeout, cp.stdout, cp.stderr)
            else:
                raise Exception("command timed out even though timeout "
                                "was not set")
