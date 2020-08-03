API reference
=============

.. warning:: 
    Documentation is stil under construction some things might not be up to
    date.

This file describes ssh-utilities API reference. Beware, some things might not be
up to date and all is subject to change since we are still in early
development phase.

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
-------------------------
.. automodule:: ssh_utilities.remote
   :members:

ssh_utilities.local
---------------------
.. automodule:: ssh_utilities.local
   :members:

ssh_utilities.path
----------------------
.. automodule:: ssh_utilities.path
   :members:

ssh_utilities.utils
---------------------------
.. automodule:: ssh_utilities.utils
   :members:

ssh_utilities.exceptions
---------------------------
.. automodule:: ssh_utilities.exceptions
   :members:

ssh_utilities.constants
---------------------------
.. automodule:: ssh_utilities.constants
   :members: