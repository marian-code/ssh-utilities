MultiConnection usage
=====================

Instantiating MultiConnection
-----------------------------

``MultiConnection`` is a container cleverly managing pool of connections for
you. It can be used to carry out same command accross multiple hosts
asynchronously or to essentially parallelize connection by openning multiple
connections instances connected to same host. Its main initialization method is
just by instantiating the class. It can also be loaded from dictionary, string
or pickle file as well as be persisted  by using these data types. The
``MultiConnection`` supports all ``dict`` API methods so all individual
connections managed by the object can accesed individually. ``MultiConnection``
can hold mix of ``SSHConnection`` and ``LocalConnection`` instances. The API is
exactly the same as for ``SSHConnection`` and ``LocalConnection`` except the
methods that would return value for individual connection now return iterator
of these individual values.

Instantiating class provides a simple interface similar to factory
``Connection.get`` method. It relies on the keys present in your
``~/.ssh.config`` file or ones added through ``add_hosts`` method

.. note::

    You can specify each host multiple times. This will open more ssh
    connections to the same host which will effectively parallelize the
    connection to the host in question.

.. code-block:: python

    >>> from ssh_utilities import MultiConnection
    >>> MultiConnection(<server_names_list>, local=False, thread_safe=True)
    >>> <ssh_utilities.ssh_utilities.MultiConnection at 0x7efedff4fb38>

``MultiConnection`` class can also be used as a contextmanager.

.. code-block:: python

    >>> from ssh_utilities import MultiConnection
    >>> with MultiConnection(<server_names_list>, local=False,
                             thread_safe=True) as mc:
    >>>     mc.<some_attribute>
    >>>     ...

.. note::

    ``local`` and ``thread_safe`` arguments can also be
    lists with length corresponding to ``server_names`` each element in these
    lists will be used with corresponding connection otherwise the arguments
    will be same for all connections.

More hosts can be simply added in a same way as with ``Connection``

.. code-block:: python

    >>> from ssh_utilities import MultiConnection
    >>> MultiConnection.add_hosts({"user": <some_user>, "hostname": <my_ssh_server>,
                                   "identityfile": <path_to_my_identity_file>})

If you require higher level of customization simply initialize ``MultiConnection``
without parameters and than add individual connections one by one.

.. code-block:: python

    >>> from ssh_utilities import MultiConnection, Connection
    >>> mc = MultiConnection([])  # ssh_servers argument must be empty list
    >>>
    >>> c1 = Connection.get(<ssh_server>)
    >>> mc += c1  # or mc = mc + c1
    >>>
    >>> c2 = Connection.open(<ssh_username>, <ssh_server>, <ssh_key_file>,
    >>>                      <server_name>, <thread_safe>)
    >>> mc["some_key"] = c2  # use dict interface
    >>>
    >>> mc1 = MultiConnection(<[ssh_Servers_list]>)
    >>> mc2 = mc + mc1  # you can also join MultiConnection instances
    >>> mc2.update(mc1)  # or use dict interface

.. warning::

    You cannot add more connections under same key!


Fully aupported dictionary interface also allows you to easilly access and
manipulate individual connections in container.

.. code-block:: python

    >>> from ssh_utilities import MultiConnection, Connection
    >>> mc = MultiConnection(<[ssh_Servers_list]>)
    >>>
    >>> # iterate over connections
    >>> mc.keys()  # keys under which individual connections are registered
    >>> mc.values()  # respective connection instances
    >>> mc.items()
    >>>
    >>> # access individual connections
    >>> mc.get(<connection_name>, None)  # None will be default value if key is not present
    >>> mc[<connection_name>]
    >>> <connection_name> in mc  # test if key is present
    >>>
    >>> # delete connections
    >>> del mc[<connection_name>]
    >>> mc.pop(<connection_name>)
    >>> mc.popitem()
    >>> mc.clear()
    >>>
    >>> copy
    >>> mc1 = mc.copy()  # shallow copy same as dict.copy() method

Persistence
-----------

``MultiConnection`` can also be initialized from appropriately formated string.

.. code-block:: python

    >>> from ssh_utilities import MultiConnection
    >>> mc = MultiConnection(<[ssh_Servers_list]>)
    >>> string = str(mc)
    >>> mc = MultiConnection.from_str(<string>)

or dictionary

.. code-block:: python

    >>> from ssh_utilities import MultiConnection
    >>> mc = MultiConnection(<[ssh_Servers_list]>)
    >>> <dictionary> = mc.to_dict()
    >>> mc = MultiConnection.from_dict(<dictionary>)

or pickle

.. code-block:: python

    >>> import pickle
    >>> from ssh_utilities import MultiConnection
    >>> mc = MultiConnection(<[ssh_Servers_list]>)
    >>> pickle.dump(mc, <MultiConnection.pickle_file>)
    >>> mc = pickle.load(<MultiConnection.pickle_file>)

``MultiConnection`` can also be deepcopied


.. code-block:: python

    >>> from copy import deepcopy
    >>> from ssh_utilities import MultiConnection
    >>> mc = MultiConnection(<[ssh_Servers_list]>)
    >>> mc1 = deepcopy(mc)
    >>> print(id(mc), id(mc1))
    >>> 139653107408400 139653058483088

Using connection - inner classes
--------------------------------

Using the inner classes that that mirror API of builtins, os, pathlib, shutil,
subprocess is exactly the same as in simple ``Connection`` except all the methods
that return now return iterators. For further details refer to
`Connection usage <usage_conn.rst>`