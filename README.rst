Paramiko wrapper
================

:Test Status:

    .. image:: https://readthedocs.org/projects/ssh-utilities/badge/?version=latest
        :target: https://ssh-utilities.readthedocs.io/en/latest/?badge=latest
        :alt: Documentation Status

    .. image:: https://travis-ci.com/marian-code/ssh-utilities.svg?branch=master
        :target: https://travis-ci.com/marian-code/ssh-utilities

    .. image:: https://coveralls.io/repos/github/marian-code/ssh-utilities/badge.svg?branch=master
        :target: https://coveralls.io/github/marian-code/ssh-utilities?branch=master

    .. image:: https://api.codeclimate.com/v1/badges/978efa969238d28ab1ab/maintainability
        :target: https://codeclimate.com/github/marian-code/ssh-utilities/maintainability
        :alt: Maintainability

:Version Info:

    .. image:: https://img.shields.io/pypi/v/ssh-utilities
        :target: https://pypi.org/project/ssh-utilities/
        :alt: PyPI

    .. image:: https://img.shields.io/pypi/implementation/ssh-utilities
        :alt: PyPI - Implementation

    .. image:: https://img.shields.io/static/v1?label=MyPy&message=checked&color=blue
        :alt: Checked with mypy
        :target: http://mypy-lang.org

    .. image:: https://img.shields.io/pypi/dm/ssh-utilities
        :alt: PyPI - Downloads

:License:

    .. image:: https://img.shields.io/pypi/l/ssh-utilities
        :alt: PyPI - License


Simple paramiko wrapper that aims to facilitate easy remote file operations
and command execution. The API vaguely follows python libraries:
`os <https://docs.python.org/3/library/os.html>`_,
`os.path <https://docs.python.org/3/library/os.path.html>`_,
`subprocess <https://docs.python.org/3/library/subprocess.html>`_,
`shutil <https://docs.python.org/3/library/shutil.html>`_,
`pathlib <https://docs.python.org/3/library/pathlib.html>`_. Has also
local variant that mimics the remote API on local machine. The connection is
resilient to interruptions and thread safe. Everything is well documented by
dostrings and typed.

This module should be ideally platform agnostic, but only connections from
Windows and Linux(Debian, Ubuntu) to Linux(Debian, Ubuntu) have been tested
so any other combinations are officially unsupported but should work.

Installation
------------

.. code-block:: bash

    pip install ssh_utilities

Or if you want to install directly from source:

.. code-block:: bash

    git clone https://github.com/marian-code/ssh-utilities.git
    cd ssh_utilities
    pip install -e .

Use ``-e`` only to install in editable mode

If you encounter some import errors try installing from requirements.txt file:
``pip install requirements.txt``

Warning
-------

There has been a recent mayor change in modules API betweeen versions 0.4.2
and 0.5.0. Most methods of the connection classes have been moved a level
deeper. See `migration from 0.4.x to 0.5.x <https://ssh-utilities.readthedocs.io/en/latest/migration.html>`_
for details how to port to newer version

API and documentation
---------------------

It is recommended that you have configured **rsa** keys with config file according
to `openssh standard <https://www.ssh.com/ssh/config/>`_. For easy quickstart guide
you can look at: https://www.cyberciti.biz/faq/create-ssh-config-file-on-linux-unix/

API exposes three main connection classes one path manipulation class, python
module replacement classes, utility functions and constants:

.. code-block:: python

    from ssh_utilities import SSHConnection, Connection, LocalConnection
    from ssh_utilities import SSHPath
    from ssh_utilities import Builtins, Os, Pathlib, Shutil, Subprocess
    from ssh_utilities import config_parser
    from ssh_utilities import PIPE, STDOUT, DEVNULL, GET, PUT

``Connection`` is the a factory class that initializes ``SSHConnection`` or
``LocalConnection`` classes based on input parameters.

``SSHConnection`` is the remote connection class with API partly following that
of python `os <https://docs.python.org/3/library/os.html>`_,
`os.path library <https://docs.python.org/3/library/os.path.html>`_,
`shutil library <https://docs.python.org/3/library/shutil.html>`_ and
`subprocess library <https://docs.python.org/3/library/subprocess.html>`_
`pathlib <https://docs.python.org/3/library/pathlib.html>`_

``LocalConnection`` is included only for convenience purposes so same API as for
``SSHConnection`` can be used for interacting with local machine

``SSHPath`` is an object for remote path manipulation with same API as python: 
`pathlib library <https://docs.python.org/3/library/pathlib.html>`_ 

The ``SSHConnection`` and ``LocalConnection`` objects are both devided to few
inner classes which correspond to python modules. For ``SSHConnection``
these are:
    
    * ``SSHConnection.builtins``
    * ``SSHConnection.os``
    * ``SSHConnection.pathlib``
    * ``SSHConnection.subprocess``
    * ``SSHConnection.shutil``

same applies to ``LocalConnection``

All API documentation can be found at readthedocs:
https://ssh-utilities.readthedocs.io/en/latest/


Simple Usage
------------

for more detailed usage examples please refer to
`documnetation <https://ssh-utilities.readthedocs.io/en/latest/>`_

``Connection`` factory supports dict-like indexing by values that are in
your **~/.ssh/config** file. It can be made thread safe by passing
``thread_safe=True`` argument to the constructor

.. code-block:: python

    >>> from ssh_utilities import Connection
    >>> Connection[<server_name>]
    >>> <ssh_utilities.ssh_utils.SSHConnection at 0x7efedff4fb38>

There is also a specific get method which is safer and with better typing
support than dict-like indexing

.. code-block:: python

    >>> from ssh_utilities import Connection
    >>> Connection.get(<server_name>, <local>, <quiet>, <thread_safe>)
    >>> <ssh_utilities.ssh_utils.SSHConnection at 0x7efedff4fb38>

Class can be also used as a context manager.

.. code-block:: python

    >>> from ssh_utilities import Connection
    >>> with Connection(<server_name>, <local>, <quiet>, <thread_safe>) as conn:
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
    >>> conn = Connection.open(<ssh_username>, <ssh_server>, <ssh_key_file>,
                               <server_name>, <thread_safe>):

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

    >>> from ssh_utilities import Connection, SSHPath
    >>> conn = Connection.get(<server_name>)
    >>> sshpath = SSHPath(conn, <some_path>)

The replacements for parts of python standard lib can be used as inner classes
of ``SSHConnection`` or ``LocalConnection``:

.. code-block:: python

    >>> from ssh_utilities import Connection
    >>> with Connection(<server_name>, <local>, <quiet>, <thread_safe>) as conn:
    >>>     conn.os.isfile(<path_to_some_file>)
    >>>     conn.subprocess.run(*args, **kwargs)
    >>>     # and so on for other modules

Or you can assign the inner class to another variable but keep in mind
that when connection is closed it will stop working!

.. code-block:: python

    >>> from ssh_utilities import Connection
    >>> conn = Connection.get(<server_name>, <local>, <quiet>, <thread_safe>)
    >>> remote_os =conn.os
    >>> remote_subprocess = conn.subprocess

The last possibility is to instantiate each module by itself

.. code-block:: python


    >>> from ssh_utilities import Connection, Os, Subprocess
    >>> conn = Connection.get(<server_name>, <local>, <quiet>, <thread_safe>)
    >>> remote_os = Os(conn)
    >>> remote_subprocess = Subprocess(conn)


Contributing
------------

1. Fork it
2. Create your feature branch: ``git checkout -b my-new-feature``
3. Commit your changes: ``git commit -am 'Add some feature'``
4. Push to the branch: ``git push origin my-new-feature``
5. Submit a pull request

License
-------

LGPL-2.1

TODO
----
- implement wrapper for pool of connections
