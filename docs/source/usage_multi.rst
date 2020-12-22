MultiConnection usage
=====================

multi_connection module graph
-----------------------------

.. uml:: ssh_utilities.multi_connection
    :classes:

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

.. note::

    You can add more connections under same key! which will make the connection
    effectively parallel

Dict interface
--------------

Fully supported dictionary interface also allows you to easilly access and
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

This has a few caveats though. As multiple connections can be registered under
one key you can think of ``MultiConnection`` as ``dict`` wchich supports duplicate
keys. The dict like methods work as expected and there are same methods with
``_all`` suffix in name that allow acces to whole pool registered under the key.

.. code-block:: python

    >>> from ssh_utilities import MultiConnection, Connection
    >>> mc = MultiConnection(<[server_1, server_1, server_2]>)
    >>>
    >>> # keys under which individual connection pools are registered
    >>> mc.keys()
    >>> server_1, server_2
    >>> # unpack and return key as many times as there are connections in its pool
    >>> mc.keys_all()
    >>> # same applies for values and items
    >>> mc.values() # one connection instance for each key
    >>> mc.values_all() # unpack pools and return all connections
    >>> mc.items()
    >>> mc.items_all()
    >>>
    >>> # access individual connection from pool under key
    >>> mc.get(server_1)
    >>> # access the whole pool
    >>> mc.get_all(server_1)
    >>> <deque with two connections to server_1>
    >>> mc[server_1] # return sone connection from pool has no _all twin method
    >>>
    >>> # delete one connection from pool
    >>> del mc[server_1]
    >>> server_1 in mc
    >>> True
    >>> # since there are two connections in server_1 pool the key server_1 will
    >>> # be deleted only after calling del on server_1 key two times
    >>> del mc[server_1]
    >>> server_1 in mc
    >>> False
    >>>
    >>> # with pop and popitem you also have `_all` alterantive so you can
    >>> # delete whole pool at once
    >>> mc.pop_all(server_1)
    >>> server_1 in mc
    >>> False

Connection internal storage
---------------------------

Schematic graph of how individual connections are organized in Multiconnection

.. graphviz::
    :name: MultiConnection data structure
    :caption: MultiConnection data structure
    :alt: Organization of individual connections in MultiConnection object
    :align: center

     digraph "sphinx-ext-graphviz" {
         size="6,4";
         rankdir="TD";
         graph [fontname="Verdana", fontsize="12"];
         node [fontname="Verdana", fontsize="12"];
         edge [fontname="Sans", fontsize="9"];

         multi_connection [
            label="MultiConnection([key_1, key_1, key_2, key_3])",
            shape="cylinder",
            href="https://ssh-utilities.readthedocs.io/en/latest/usage_multi.html",
        ];
         connections_dict [
            label="_connections",
            shape="component",
        ];
        key1 [
            label="key_1",
            shape=cylinder,
            fillcolor=orange,
            style=filled
        ];
        key2 [
            label="key_2",
            shape=cylinder,
            fillcolor=yellow,
            style=filled
        ];
        key3 [
            label="key_3",
            shape=cylinder,
            fillcolor=red,
            style=filled
        ];

        subgraph clusterDeque1 {
            label="Pool (deque) of connections registered under key_1";
            node [style=filled];
            bgcolor=lightblue;
            conn11 [
                label="SSHConnection<key_1>",
                shape="box",
                fillcolor=blue,
                style=filled
            ];
            conn12 [
                label="SSHConnection<key_1>",
                shape="box",
                fillcolor=blue,
                style=filled
            ];
         };

        subgraph clusterDeque2 {
            label="Pool under key_2";
            node [style=filled];
            bgcolor=lightblue;
            conn21 [
                label="SSHConnection<key_2>",
                shape="box",
                fillcolor=blue,
                style=filled
            ];
        };

        subgraph clusterDeque3 {
            label="Pool under key_3";
            node [style=filled];
            bgcolor=lightblue;
            conn31 [
                label="LocalConnection<key_3>",
                shape="box",
                fillcolor=green,
                style=filled
            ];
        };

        multi_connection -> connections_dict [label=" holds connection pools "];

        connections_dict -> key1 [label=" all connections to key_1 ", style=dashed];
        key1 -> conn11 [label="connection 1", style=dashed];
        key1 -> conn12 [label="connection 2", style=dashed];
        connections_dict -> key2 [label=" all connections to key_2 "];
        key2 -> conn21 [label="connection 1", style=dashed];
        connections_dict -> key3 [label=" all connections to key_3 "];
        key3 -> conn31 [label="connection 1", style=dashed];

     }

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
that return now return iterators. A trivial example would be:

.. code-block:: python

    >>> from ssh_utilities import MultiConnection
    >>> mc = MultiConnection(<[server_1, server_2]>)
    >>> for is_f in mc.os.isfile(<path>):
    >>>     print(is_f)
    >>>
    >>> True  # output for server_1
    >>> False  # output for server_2

.. warning::

    If method prints some output these can become unordered and mangled. This is
    especially true for shutil methods wich display progressbar so it is
    recomended to turn it off.

For further details refer to `Connection usage <usage_conn.rst>`

Parallel Connection
-------------------

Connection can be effectively parallelized by adding multiple connections under
same key. This will however not be exploited by the default iterator-like job
dispatcher as it would not make sense. Consider this example:

.. code-block:: python

    >>> from ssh_utilities import MultiConnection
    >>>
    >>> # this will open 2 independent connections both to server_1
    >>> mc = MultiConnection(<[server_1, server_1]>)
    >>> for is_f in mc.os.isfile(<path>):
    >>>     print(is_f)
    >>>
    >>> True  # output for server_1 
    >>> True  # output for server_1

This would run same command on one host twice. Instead when using iterator interface
commands are run only once on each server. If you want to exploit the parallelism
you have to manage it manually. But fortunatelly even in this case
`MultiConnection` does most of the heavy lifting. Under the hood pool of 
connections for each key is managed in `collections.deque` and after each request
the queue is rotated so you get new connection. Example:

.. code-block:: python

    >>> from ssh_utilities import MultiConnection, PUT
    >>> trom threading import Thread
    >>>
    >>> # this will open 2 independent connections both to server_1
    >>> mc = MultiConnection(<[server_1, server_1]>, thread_safe=True)
    >>>
    >>> # get one connection
    >>> c1 = mc.get(server_1)
    >>> # run copy function in background thread
    >>> t = Thread(target=c1.copy, args=(<path_local>, <path_remote>),
    >>>            kwargs={"direction": PUT})
    >>> t.start()
    >>> 
    >>> # to get second connection just call again get method. MultiConnection
    >>> # automatically returns next connection in pool
    >>> c2 = mc.get(server_1)
    >>> # this can now be used while the copy is still running as it uses the
    >>> # second connection in pool
    >>> c2.isfile(<some_path>)
    >>>
    >>> # since we have only two connections in pool calling get method again
    >>> # will return same connection as c1 and all calls will be blocked
    >>> # until copying finishes
    >>> c3 = mc.get(server_1)  # this is in fact same as c1
