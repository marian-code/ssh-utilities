Porting from ssh_utilities <=0.4.x to >0.5.x
============================================

Differences
-----------

The main difference between versions lower than 0.4.x and those higher than
0.5.x is that in the newr version all the most methods where moved a level deeper
into inner classes. This decision was motivated by API of the
``SSHConnection`` and ``LocalConnection`` getting to cluttered by many
unrelated methods. Now most methods are neately organized in inner classes
each corresponding to one python module it tries to substitute. The inner classes
are following:

    * ``SSHConnection.builtins``
    * ``SSHConnection.os``
    * ``SSHConnection.pathlib``
    * ``SSHConnection.subprocess``
    * ``SSHConnection.shutil``

So the only difference when calling the connection methods is this.

In version <=0.4.x one could do e.g.:

.. code-block:: python

    >>> from ssh_utilities import Connection
    >>> with Connection(<server_name>) as conn:
    >>>     conn.isfile(<somefile>)
    >>>     conn.run(...)
    >>>     conn.Path(...)

In version >0.5.x the same is archieved by:

.. code-block:: python

    >>> from ssh_utilities import Connection
    >>> with Connection(<server_name>) as conn:
    >>>     conn.os.path.isfile(<somefile>)
    >>>     conn.subprocess.run(...)
    >>>     conn.pathlib.Path(...)

This naturally separates methods that belong together and makes the API more
easy to understand. You will find the respective methods in inner class with same
name as the python module it originates from.