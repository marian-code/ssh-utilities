"""Testring of SSHPath.

Warnings
--------
Will need to rethink this as obviously testing this functionallity in some
CI system proves rather difficult.
"""

import logging
import sys
from unittest import TestCase, main

from ssh_utilities import Connection

logging.basicConfig(stream=sys.stderr)
log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)


class TestSSHPath(TestCase):
    """Test remote version of Path"""

    def setUp(self):

        self.p = Connection.get("dusanko").Path("/tmp")

    def test_cwd(self):

        self.assertEqual(str(self.p.cwd()), "/home/rynik")


if __name__ == '__main__':
    main()
