"""Subprocess module proxy."""

import logging
import subprocess
from typing import TYPE_CHECKING, Optional

from ..base import SubprocessABC
from ..constants import C, R
from ..utils import lprint

if TYPE_CHECKING:
    from ..typeshed import _CMD, _ENV, _FILE, _SPATH
    from .local import LocalConnection

__all__ = ["Subprocess"]

logging.getLogger(__name__)


class Subprocess(SubprocessABC):
    """Local proxy for subprocess module.

    Supports same subset of API as remote version.

    See also
    --------
    :class:`ssh_utilities.remote.Subprocess`
        remote version of class with same API
    """

    def __init__(self, connection: "LocalConnection") -> None:
        self.c = connection

    @staticmethod
    def run(args: "_CMD", *, suppress_out: bool, quiet: bool = True,
            bufsize: int = -1, executable: "_SPATH" = None,
            input: Optional[str] = None, stdin: "_FILE" = None,
            stdout: "_FILE" = None, stderr: "_FILE" = None,
            capture_output: bool = False, shell: bool = False,
            cwd: "_SPATH" = None, timeout: Optional[float] = None,
            check: bool = False, encoding: Optional[str] = None,
            errors: Optional[str] = None, text: Optional[bool] = None,
            env: Optional["_ENV"] = None, universal_newlines: bool = False
            ) -> subprocess.CompletedProcess:

        if capture_output:
            stdout = subprocess.PIPE
            stderr = subprocess.PIPE

        out = subprocess.run(  # type: ignore
            args, bufsize=bufsize,
            executable=executable,  # type: ignore
            input=input, stdin=stdin, stdout=stdout, stderr=stderr,
            shell=shell, cwd=cwd, timeout=timeout, check=check,
            encoding=encoding,  # type: ignore
            errors=errors, text=text, universal_newlines=universal_newlines
        )

        if capture_output and not suppress_out:
            lprint(quiet)(f"{C}Printing local output\n{'-' * 111}{R}")
            lprint(quiet)(out.stdout)
            lprint(quiet)(f"{C}{'-' * 111}{R}\n")

        return out
