Usage
=====

``Connection`` factory supports dict-like indexing by values that are in
your **~/.ssh/config** file

.. code-block:: python

    >>> from ssh_utilities import Connection
    >>> Connection[<server_name>]
    >>> <ssh_utilities.ssh_utils.SSHConnection at 0x7efedff4fb38>

There is also a specific get method which is safer and with better typing
support than dict-like indexing

.. code-block:: python

    >>> from ssh_utilities import Connection
    >>> Connection.get(<server_name>)
    >>> <ssh_utilities.ssh_utils.SSHConnection at 0x7efedff4fb38>

Class can be also used as a context manager.

.. code-block:: python

    >>> from ssh_utilities import Connection
    >>> with Connection(<server_name>) as conn:
    >>>     conn.something(...)

Connection can also be initialized from appropriately formated string.
Strings are used mainly for underlying connection classes persistance to
disk

.. code-block:: python

    >>> from ssh_utilities import Connection
    >>> Connection.from_str(<string>)

All these return connection with preset reasonable parameters if more
customization is required, use open method, this also allows use of passwords

.. code-block:: python

    >>> from ssh_utilities import Connection
    >>> with Connection.open(<sshUsername>, <sshServer>, <sshKey>, <server_name>,
                             <logger>, <share_connection>):

Module API also exposes powerfull SSHPath object with identical API as
``pathlib.Path`` only this one works for remote files. It must be always tied to
some connection object which will provide interaction with remote host. The
easyiest way to initialize it is as a method of Connection object.

.. code-block:: python

    >>> from ssh_utilities import Connection
    >>> with Connection(<server_name>) as conn:
    >>>     sshpath = conn.Path(<some_path>)

Or the seccond option is to pass the SSHPath constructor an instace of created
connection

.. code-block:: python

    >>> from ssh_utilities import Connection
    >>> conn = Connection.get(<server_name>)
    >>> sshpath = SSHPath(conn, <some_path>)
