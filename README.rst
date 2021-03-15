ssh-utilities
=============

:Test Status:

    .. image:: https://readthedocs.org/projects/ssh-utilities/badge/?version=latest
        :target: https://ssh-utilities.readthedocs.io/en/latest/?badge=latest
        :alt: Documentation Status

    .. image:: https://github.com/marian-code/ssh-utilities/actions/workflows/python-package.yml/badge.svg?branch=release
        :target: https://github.com/marian-code/ssh-utilities/actions
        :alt: build

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
        :target: https://pypistats.org/packages/ssh-utilities

:License:

    .. image:: https://img.shields.io/pypi/l/ssh-utilities
        :alt: PyPI - License


.. |yes| unicode:: U+2705
.. |no| unicode:: U+274C
.. _builtins: https://docs.python.org/3/library/builtins.html
.. _os: https://docs.python.org/3/library/os.html
.. _os.path: https://docs.python.org/3/library/os.path.html
.. _subprocess: https://docs.python.org/3/library/subprocess.html
.. _shutil: https://docs.python.org/3/library/shutil.html
.. _pathlib: https://docs.python.org/3/library/pathlib.html

.. contents:: Table of contents
    :local:
    :depth: 2

Introduction
------------

Simple paramiko wrapper that aims to facilitate easy remote file operations
and command execution. The API vaguely follows python libraries: `builtins`_,
`os`_, `os.path`_, `subprocess`_, `shutil`_, `pathlib`_, 


This is not intended to be a full fledged python ssh client. Instead it focuses
on smaller set of features which it tries to make as user-friendly and familiar
as possible.

This module should be ideally platform agnostic, but only connections from
Windows and Linux(Debian, Ubuntu) to Linux(Debian, Ubuntu) have been tested
so any other combinations are officially unsupported but should still work.

Design goals and features
-------------------------

- support python > 3.6
- everything is typed for easy code understanding and superior type hints and
  autocompletion
- everything is properly documented
- API is as consistent as possible with python modules and functions we are
  trying to reimplement
- connection can be made thread safe
- try to be as platform agnostic as possible
- accept both stings and Path objects in all methods that require some path as
  an input
- strong emphasis on usage of ssh key based authentication

List of inner classes and implemented methods
---------------------------------------------

ssh_utilities have three main connection classes:
  - ``SSHConnection``
  - ``LocalConnection``
  - ``MultiConnection``

Their inner classes with their methods are listed in the table below which
summarizes the API. Based on table you can do for instance:

 .. code-block:: python

    >>> # this is OK
    >>> SSHConnection.os.isfile(<somepath>)
    >>> # this is not OK as it is marked in table as not implemented
    >>> MultiConnection.os.path.realpath(<somepath>)
    >>> # this is also not permitted as methods not mentioned in table are not
    >>> # implemented in any class
    >>> SSHConnection.os.getpid()

+---------------+---------------+-----------------+------------------+-----------------+
| module        | method        | SSHConnection   | LocalConnection  | MultiConnection |
+===============+===============+=================+==================+=================+
| `builtins`_   | open          | |yes|           | |yes|            | |yes|           |
+---------------+---------------+-----------------+------------------+-----------------+
| `os`_         | isfile        | |yes|           | |yes|            | |yes|           |
|               +---------------+-----------------+------------------+-----------------+
|               | isdir         | |yes|           | |yes|            | |yes|           |
|               +---------------+-----------------+------------------+-----------------+
|               | makedirs      | |yes|           | |yes|            | |yes|           |
|               +---------------+-----------------+------------------+-----------------+
|               | mkdir         | |yes|           | |yes|            | |yes|           |
|               +---------------+-----------------+------------------+-----------------+
|               | listdir       | |yes|           | |yes|            | |yes|           |
|               +---------------+-----------------+------------------+-----------------+
|               | chdir         | |yes|           | |yes|            | |yes|           |
|               +---------------+-----------------+------------------+-----------------+
|               | stat          | |yes|           | |yes|            | |yes|           |
|               +---------------+-----------------+------------------+-----------------+
|               | lstat         | |yes|           | |yes|            | |yes|           |
|               +---------------+-----------------+------------------+-----------------+
|               | name          | |yes|           | |yes|            | |yes|           |
|               +---------------+-----------------+------------------+-----------------+
|               | walk          | |yes|           | |yes|            | |yes|           |
|               +---------------+-----------------+------------------+-----------------+
|               | path          | |yes|           | |yes|            | |no|            |
+---------------+---------------+-----------------+------------------+-----------------+
| `os.path`_    | realpath      | |yes|           | |yes|            | |no|            |
+---------------+---------------+-----------------+------------------+-----------------+
| `pathlib`_    | Path          | |yes|           | |yes|            | |yes|           |
+---------------+---------------+-----------------+------------------+-----------------+
| `shutil`_     | copy          | |yes|           | |yes|            | |yes|           |
|               +---------------+-----------------+------------------+-----------------+
|               | copy2         | |yes|           | |yes|            | |yes|           |
|               +---------------+-----------------+------------------+-----------------+
|               | copyfile      | |yes|           | |yes|            | |yes|           |
|               +---------------+-----------------+------------------+-----------------+
|               | rmtree        | |yes|           | |yes|            | |yes|           |
|               +---------------+-----------------+------------------+-----------------+
|               | copy_files    | |yes|           | |yes|            | |yes|           |
|               +---------------+-----------------+------------------+-----------------+
|               | upload_tree   | |yes|           | |yes|            | |yes|           |
|               +---------------+-----------------+------------------+-----------------+
|               | download_tree | |yes|           | |yes|            | |yes|           |
+---------------+---------------+-----------------+------------------+-----------------+
| `subprocess`_ | run           | |yes|           | |yes|            | |yes|           |
+---------------+---------------+-----------------+------------------+-----------------+


API and documentation
---------------------

It is recommended that you have configured **rsa** keys with config file according
to `openssh standard <https://www.ssh.com/ssh/config/>`_. For easy quickstart guide
you can look at: https://www.cyberciti.biz/faq/create-ssh-config-file-on-linux-unix/

API exposes four main connection classes one path manipulation class, python
module replacement classes, utility functions and constants:

.. code-block:: python

    from ssh_utilities import SSHConnection, Connection, LocalConnection, MultiConnection
    from ssh_utilities import SSHPath
    from ssh_utilities import Builtins, Os, Pathlib, Shutil, Subprocess
    from ssh_utilities import config_parser
    from ssh_utilities import PIPE, STDOUT, DEVNULL, GET, PUT

``Connection`` is the a factory class that initializes ``SSHConnection`` or
``LocalConnection`` classes based on input parameters. ``MultiConnection`` is
a container for convenient management of pool of connections.
``SSHPath`` is an object for remote path manipulation. 

All API documentation can be found at readthedocs:
https://ssh-utilities.readthedocs.io/en/latest/


Simple Usage
------------

for more detailed usage examples please refer to
`documnetation <https://ssh-utilities.readthedocs.io/en/latest/>`_

``Connection`` factory supports dict-like indexing by values that are in
your **~/.ssh/config** file.

.. code-block:: python

    >>> from ssh_utilities import Connection
    >>> Connection[<server_name>]
    >>> <ssh_utilities.ssh_utils.SSHConnection at 0x7efedff4fb38>

There is also a specific get method which is safer and with better typing
support than dict-like indexing. Connection can be made thread safe by passing
``thread_safe=True`` argument to the constructor

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

ssh_utilities now contains ``MultiConnection`` container which cleverly
manages multiple individual connections for you. You can carry out same
command across multiple servers asynchronously and many more! Detailed
information is in the docs.

.. code-block:: python

    >>> from ssh_utilities import MultiConnection
    >>> with MultiConnection(<server_names_list>, local=False,
                             thread_safe=True) as mc:
    >>>     mc.<some_attribute>
    >>>     ...

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
``pip install -r requirements.txt``

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
- show which methods are implemented
- SSHPath root and anchor attributes incorectlly return '.' instead of '/' 
