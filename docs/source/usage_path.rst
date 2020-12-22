SSHPath usage
=============

pathlib module graph
--------------------

.. uml:: ssh_utilities.remote.path
    :classes:

Instantiating SSHPath
---------------------

Module API also exposes powerfull SSHPath object with identical API as
``pathlib.Path`` only this one works for remote files. It must be always tied to
some connection object which will provide interaction with remote host. The
easyiest way to initialize it is as a method of Connection object.

.. code-block:: python

    >>> from ssh_utilities import Connection
    >>> with Connection(<server_name>) as conn:
    >>>     sshpath = conn.pathlib.Path(<some_path>)

Or the seccond option is to pass the SSHPath constructor an instace of created
connection

.. code-block:: python

    >>> from ssh_utilities import Connection
    >>> conn = Connection.get(<server_name>)
    >>> sshpath = SSHPath(conn, <some_path>)

Using SSHPath
-------------

Almost excacly the same as ``pathlib.Path``. There are some minor difereneces,
like change of ``home`` and ``cwd`` methods from classmethods to
instance methods for obvious reasons. Also some methods will raise
``NotImplementedError`` as their implementation through ssh is problematic or
unfeasiblle so they were left out. But most of the API should work just as
expected

.. warning::
    Even though differences to ``pathlib.Path`` are rather minor, it is
    recommended to do extensive testing, especially when working wiht valuable
    files!

.. warning::
    Testing working with windows servers has not been done yet. It should work
    but we do not have any available suitable environment at hand so use at your
    own risk! 

TODO - provide examples