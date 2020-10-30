API reference
=============

This file describes ssh-utilities API reference. 

.. warning:: 

   Beware, we are still in developement phase so API can change without warning,
   although most part are final and there are not expected any major changes.

.. note::

    We often use throughout the documentation notation same as python 
    `typing <https://docs.python.org/3/library/typing.html>`_. 
    module to mark variable types as it is richer and preserves more
    information. e.g. List[str] obviously means list of strings. More on the
    matter can be read in the typing module documentation.

.. note::

   This module should be ideally platform agnostic, but only connections from
   Windows and Linux(Debian, Ubuntu) to Linux(Debian, Ubuntu) have been tested
   so any other combinations are officially unsupported but should work.

ssh_utilities.connection
------------------------------
.. automodule:: ssh_utilities.connection
   :members:

ssh_utilities.base
-------------------
.. automodule:: ssh_utilities.base
   :members:

ssh_utilities.remote
--------------------
.. automodule:: ssh_utilities.remote
   :members:

ssh_utilities.remote._builtins
------------------------------
.. automodule:: ssh_utilities.remote._builtins
   :members:

ssh_utilities.remote._os
------------------------
.. automodule:: ssh_utilities.remote._os
   :members:

ssh_utilities.remote._pathlib
-----------------------------
.. automodule:: ssh_utilities.remote._pathlib
   :members:

ssh_utilities.remote._shutil
----------------------------
.. automodule:: ssh_utilities.remote._shutil
   :members:

ssh_utilities.remote._subprocess
--------------------------------
.. automodule:: ssh_utilities.remote._subprocess
   :members:

ssh_utilities.remote.path
-------------------------
.. automodule:: ssh_utilities.remote.path
   :members:

ssh_utilities.remote._connection_wrapper
----------------------------------------
.. automodule:: ssh_utilities.remote._connection_wrapper
   :members:

ssh_utilities.local
-------------------
.. automodule:: ssh_utilities.local
   :members:

ssh_utilities.local._builtins
-----------------------------
.. automodule:: ssh_utilities.local._builtins
   :members:

ssh_utilities.local._os
-----------------------
.. automodule:: ssh_utilities.local._os
   :members:

ssh_utilities.local._pathlib
----------------------------
.. automodule:: ssh_utilities.local._pathlib
   :members:

ssh_utilities.local._shutil
---------------------------
.. automodule:: ssh_utilities.local._shutil
   :members:

ssh_utilities.local._subprocess
-------------------------------
.. automodule:: ssh_utilities.local._subprocess

ssh_utilities.utils
-------------------
.. automodule:: ssh_utilities.utils
   :members:

ssh_utilities.exceptions
------------------------
.. automodule:: ssh_utilities.exceptions
   :members:

ssh_utilities.constants
-----------------------
.. automodule:: ssh_utilities.constants
   :members: