import logging
import time
from functools import wraps
from typing import TYPE_CHECKING, Callable, Optional, Union

from paramiko import SFTPError
from paramiko.client import SSHClient
from paramiko.ssh_exception import NoValidConnectionsError, SSHException

from ..exceptions import ConnectionError, SFTPOpenError

if TYPE_CHECKING:
    from ..typeshed import _EXCTYPE
    from . import Builtins, Os, Pathlib, Shutil, Subprocess
    from .remote import SSHConnection

    _CLASS = Union[Builtins, Os, Pathlib, Shutil, Subprocess, SSHConnection]

log = logging.getLogger(__name__)

__all__ = ["check_connections"]


def check_connections(original_function: Optional[Callable] = None, *,
                      exclude_exceptions: "_EXCTYPE" = ()):
    """A decorator to check SSH connections.

    If connection is dropped while running function, re-negotiate new
    connection and run function again.

    Parameters
    ----------
    original_function: Callable
        function to watch for dropped connections
    exclude_exceptions: Tuple[Exception]
        tuple of exceptions not to catch

    Raises
    ------
    Exception
        Any exception that is not specified in the wrapper when it is thrown
        in the decorated method
    exclude_exceptions
        Any exception specified in this list when it is thrown
        in the decorated method

    Warnings
    --------
    Beware, this function can hide certain errors or cause the code to become
    stuck in an infinite loop!

    References
    ----------
    https://stackoverflow.com/questions/3888158/making-decorators-with-optional-arguments

    Examples
    --------
    First use cases is without arguments:

    >>> @check_connections
    ... def function(*args, **kwargs):

    Second possible use cases is with arguments:

    >>> @check_connections(exclude_exceptions=(<Exception>, ...))
    ... def function(*args, **kwargs):
    """
    def _decorate(function):

        @wraps(function)
        def connect_wrapper(self: "_CLASS", *args, **kwargs):

            # we have to deal with branching inner classes where attribute 'c'
            # is instance of SSHConnection not paramiko SSHClient
            # as of now we have 2 inner levels so we must iterate until we get
            # to the base
            while True:
                if not isinstance(self.c, SSHClient):
                    instance = self.c
                else:
                    instance = self
                    break

            def negotiate() -> bool:
                try:
                    instance.close(quiet=True)
                except Exception as e:
                    log.exception(f"Couldn't close connection: {e}")

                try:
                    instance._get_ssh()
                except ConnectionError:
                    success = False
                else:
                    success = True

                log.debug(f"success 1: {success}")
                if not success:
                    return False

                if instance._sftp_open:
                    log.debug(f"success 2: {success}")
                    try:
                        instance.sftp
                    except SFTPOpenError:
                        success = False
                        log.debug(f"success 3: {success}")

                    else:
                        log.debug(f"success 4: {success}")

                        success = True
                else:
                    success = False

                log.exception(f"Relevant variables:\n"
                              f"success:    {success}\n"
                              f"password:   {instance.password}\n"
                              f"address:    {instance.address}\n"
                              f"username:   {instance.username}\n"
                              f"ssh class:  {type(instance.c)}\n"
                              f"sftp class: {type(instance.sftp)}")
                if instance._sftp_open:
                    log.exception(f"remote home: {instance.remote_home}")

                return success

            n = function.__name__
            error = None
            try:
                return function(instance, *args, **kwargs)
            except exclude_exceptions as e:
                # if exception is one of the excluded, re-raise it
                raise e from None
            except NoValidConnectionsError as e:
                error = e
                log.exception(f"Caught paramiko error in {n}: {e}")
            except SSHException as e:
                error = e
                log.exception(f"Caught paramiko error in {n}: {e}")
            except AttributeError as e:
                error = e
                log.exception(f"Caught attribute error in {n}: {e}")
            except OSError as e:
                error = e
                log.exception(f"Caught OS error in {n}: {e}")
            except SFTPError as e:
                # garbage packets,
                # see: https://github.com/paramiko/paramiko/issues/395
                log.exception(f"Caught paramiko error in {n}: {e}")
            finally:
                while error:

                    log.warning("Connection is down, trying to reconnect")
                    if negotiate():
                        log.info("Connection restablished, continuing ..")
                        connect_wrapper(instance, *args, **kwargs)
                        break
                    else:
                        log.warning("Unsuccessful, wait 60 seconds "
                                       "before next try")
                        time.sleep(60)

        return connect_wrapper

    if original_function:
        return _decorate(original_function)

    return _decorate
