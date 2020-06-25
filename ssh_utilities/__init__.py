from .remote import Connection as SSHConnection
from .local import Connection as LocalConnection
from .connection import Connection
from .path import SSHPath

__all__ = ["SSHConnection", "Connection", "LocalConnection"]
