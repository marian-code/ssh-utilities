"""Remote version of subprocess module."""

import logging
import os
import socket
import sys
from collections.abc import Sequence
from io import BytesIO, StringIO
from pathlib import Path
from subprocess import DEVNULL, PIPE, STDOUT
from typing import TYPE_CHECKING, Optional, TextIO, Union

from ..abstract import SubprocessABC
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
    def run(self, args: "_CMD", *, suppress_out: bool,  # NOSONAR
            quiet: bool = True, bufsize: int = -1, executable: "_SPATH" = None,
            input: Optional[str] = None, stdin: "_FILE" = None,
            stdout: "_FILE" = None, stderr: "_FILE" = None,
            capture_output: bool = False, shell: bool = False,
            cwd: "_SPATH" = None, timeout: Optional[float] = None,
            check: bool = False, encoding: Optional[str] = None,
            errors: Optional[str] = None, text: Optional[bool] = None,
            env: "_ENV" = None, universal_newlines: bool = False
            ) -> CompletedProcess:

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
        elif hasattr(stdin, "write"):
            stdin_pipe = stdin
        else:
            raise TypeError(
                f"stdin argument is of unsupported type. You have passed in "
                f"{type(stdin)}. The allowed types are: None, DEVNULL, PIPE, "
                f"integer file descriptor or a stream-like object supporting "
                f"write"
            )

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
        elif hasattr(stdout, "write"):
            stdout_pipe = stdout
        else:
            raise TypeError(
                f"stdout argument is of unsupported type. You have passed in "
                f"{type(stdout)}. The allowed types are: None, DEVNULL, PIPE, "
                f"integer file descriptor or a stream-like object supporting "
                f"write"
            )

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
        elif hasattr(stderr, "write"):
            stderr_pipe = stderr
        else:
            raise TypeError(
                f"stderr argument is of unsupported type. You have passed in "
                f"{type(stderr)}. The allowed types are: None, DEVNULL, PIPE, "
                f"integer file descriptor or a stream-like object supporting "
                f"write"
            )

        # convert general sequence to list
        if isinstance(args, Sequence):
            args = list(args)

        if isinstance(args, list):
            for i, a in enumerate(args):
                if isinstance(a, Path):
                    args[i] = self.c._path2str(a)

            command = " ".join(args)
        elif isinstance(args, Path):
            command = self.c._path2str(args)
        elif isinstance(args, str):
            command = args
        else:
            raise TypeError(
                "process arguments are of wrong type. "
                "Must be str, Path, Sequence of one them"
            )

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

        if encoding:
            cp = CompletedProcess[str]("")
        else:
            cp = CompletedProcess[bytes](b"")  # type: ignore

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
                            cp.stdout += data_dec
                        else:
                            stdout_pipe.write(data)
                            cp.stdout += data

                    if ssh_stderr.channel.recv_stderr_ready():
                        data = ssh_stderr.channel.recv_stderr(1024)
                        if encoding:
                            data_dec = str(data, encoding, errors)
                            stderr_pipe.write(data_dec)  # type: ignore
                            cp.stderr += data_dec
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
                raise TimeoutExpired(args, 0, cp.stdout, "command timed out "
                                     "even though timeout was not set:" +
                                     str(cp.stderr))
