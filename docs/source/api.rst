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

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   api/base
   api/local
   api/remote
   api/multi

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