from .remote import Connection as SSHConnection
from .local import Connection as LocalConnection
from .connection import Connection

__all__ = ["SSHConnection", "Connection", "LocalConnection"]
