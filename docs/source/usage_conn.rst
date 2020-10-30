Connection usage
================

Instantiating connection
------------------------

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
    >>> conn = Connection.open(<ssh_username>, <ssh_server>, <ssh_key_file>, <server_name>,
                               <share_connection>)
    >>>

Using connection - subprocess
-----------------------------

This part describes how to use subproces-like methods in ``ssh-utilities``

First let's import needed modules and create connection instance. We will
assume that we have an entry in ``~/.ssh/config`` belonging to **remote**
such as:

.. code-block:: ini

    Host my_ssh_server
        HostName xxx.xxx.xxx.xxx
        IdentityFile ~/.ssh/id_rsa_my_ssh_server
        User ssh_user

and ofcourse corresponding identity file has to be present too.

.. code-block:: python

    >>> from ssh_utilities import Connection
    >>> from ssh_utilities.exceptions import CalledProcessError
    >>> from pathlib import Path
    >>> 
    >>> c = Connection.get("my_ssh_server")
    >>> Will login with private RSA key located in /home/current_user/.ssh/id_rsa_my_ssh_server
    >>> Connecting to server: ssh_user@xxx.xxx.xxx.xxx (my_ssh_server)

Next lets try to run some command.

.. code-block:: python

    >>> try:
    >>>     ls = c.subprocess.run(["ls", "-l"], suppress_out=False, quiet=False,
    >>>                           capture_output=True, check=True, cwd=Path("/home/rynik"))
    >>> except CalledProcessError as e:
    >>>     print(e)
    >>> else:
    >>>     print(ls)
    >>> 
    >>> Executing command on remote: ls -l
    >>> 
    >>> Printing remote output
    >>> ---------------------------------------------------------------------------------------------------------------
    >>> total 4
    >>> lrwxrwxrwx  1 ssh_user ssh_user   25 May 22 12:21 code -> OneDrive/dizertacka/code/
    >>> lrwxrwxrwx  1 ssh_user ssh_user   27 Nov  5  2019 Downloads -> /home/ssh_user/Raid/Downloads/
    >>> lrwxrwxrwx  1 ssh_user ssh_user   26 Sep 10  2019 OneDrive -> /home/ssh_user/Raid/OneDrive/
    >>> lrwxrwxrwx  1 root  root     9 Mar 20  2019 Raid -> /mnt/md0/
    >>> drwxr-xr-x 28 ssh_user ssh_user 4096 Jul 22 13:24 Software
    >>> 
    >>> ---------------------------------------------------------------------------------------------------------------
    >>> 
    >>> <CompletedProcess>(
    >>> stdout: total 4
    >>> lrwxrwxrwx  1 ssh_user ssh_user   25 May 22 12:21 code -> OneDrive/dizertacka/code/
    >>> lrwxrwxrwx  1 ssh_user ssh_user   27 Nov  5  2019 Downloads -> /home/ssh_user/Raid/Downloads/
    >>> lrwxrwxrwx  1 ssh_user ssh_user   26 Sep 10  2019 OneDrive -> /home/ssh_user/Raid/OneDrive/
    >>> lrwxrwxrwx  1 root  root     9 Mar 20  2019 Raid -> /mnt/md0/
    >>> drwxr-xr-x 28 ssh_user ssh_user 4096 Jul 22 13:24 Software
    >>> 
    >>> stderr: 
    >>> returncode: 0
    >>> args: ['ls', '-l'])

The API of run method resembles that of ``subprocess.run`` the first part of
the output is caused by ``suppress_out=False`` and ``quiet=False`` it is mainly
usefull for debugging. The second part is print out of the ``CompletedProcess``
object that is the same as subprocess outputs, also the raised exception
``CalledProcessError`` is the same as in subprocess. Other arguments have the
exact same meaning as in ``subprocess.run`` but currently only a limited subset
is supported. Nevertheless they should cover most usage scenarios. Notice that
``cwd`` argument accepts also ``Path`` objects!

.. note::

    All methods that take some path as argument accept ``str``, ``pathlib.Path``
    and also ``ssh_utilities.SSHPath``

Using connection - shutil
-------------------------

This part describes how to use shutil-like methods in ``ssh-utilities``

.. code-block:: python

    >>> c.shutil.download_tree(Path("/home/ssh_user/test"), "/home/current_user",
    >>>                        include="*.txt", remove_after=False)

output:

.. code-block:: bash

    >>> Building directory structure for download from remote...
    >>> 
    >>> Searching remote directory: MY_SSH_SERVER@/home/ssh_user/test
    >>> 
    >>> |--> Total number of files to copy: 1
    >>> |--> Total size of files to copy: 57.0 b
    >>> 
    >>> Creating directory structure on local side...
    >>> 
    >>> Copying remote: MY_SSH_SERVER@/home/ssh_user/test/something.txt
    >>> --> local: /home/ssh_user/something.txt
    >>> 100%|██████████████████████████████████████████████████████████████| 57.0/57.0 [00:00<00:00, 281b/s]

The output can be avoided if ``quiet=True``.

Other methods are:
    - ``upload_tree`` - function works in same manner as ``download_tree``.
    - ``send_files`` - send files specified by list of strings between local and
      remote directory in any direction
    - ``rmtree`` - works exactly same as ``shutil.rmtree``
    - ``copyfile`` - works exactly same as ``shutil.copyfile``
    - ``copy`` - works exactly same as ``shutil.copy`` except it cannot preserve
      file permisions
    - ``copy2`` - works exactly same as ``shutil.copy2`` except it cannot
      preserve file metadata

Using connection - os
---------------------

This part describes how to use os-like methods in ``ssh-utilities``

.. code-block:: python

    >>> c.os.isfile("/home/ssh_user/.bashrc")
    >>> True
    >>>
    >>> c.os.name()
    >>> "posix"
    >>>
    >>> c.os.listdir(Path("/home/ssh_user"))
    >>> ["file1", "file2", ...]

There are a few more methods which should cover basic usage, their names are
quite self explanatory. For more advances path and files manipulation use
``SSHPath`` class.

Using connection - builtins
---------------------------

This part describes how to use methods in ``ssh-utilities`` substituting python
builtins, namely ``open`` function

.. code-block:: python

    >>> with c.builtins.open(<filename>, "r", encoding="utf-8") as f:
    >>>     data = f.read()
    >>>
    >>> data
    >>> "... file constents ..."

Alternative initialization
--------------------------

The new API permits usage of individual sub-modules which can be handy at times
as a drop-in replacement for python module. We will demonstrate this on ``os``
submodule:

.. code-block:: python

    >>> # all sub-modules are named same as python modules they replace, except
    >>> # for the capital startinf letter
    >>> from ssh_utilities import Os, Connection
    >>>
    >>> c = Connection.get("some-host")
    >>>
    >>> # now define remote version of os module, it must be tied to a
    >>> # connection object 
    >>> os = Os(c)
    >>>
    >>> # now use it!
    >>> os.isfile(<somefile>)
    >>> os.stat(<somefile>)
    >>> os.isdir(<somefile>)
    >>> ...