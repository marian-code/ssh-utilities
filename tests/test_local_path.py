"""Testring of SSHPath.

Warnings
--------
Will need to rethink this as obviously testing this functionallity in some
CI system proves rather difficult.
"""

import logging
import sys
from unittest import TestCase, main
import os
from pathlib import Path

from ssh_utilities import Connection

logging.basicConfig(stream=sys.stderr)
log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)

CI = os.environ.get("TRAVIS", False)


class TestSSHPath(TestCase):
    """Test local version of Path."""

    def setUp(self):

        self.user = os.environ.get("USER", "rynik")
        self.home = os.environ.get("HOME", Path.home())

        c = Connection.open(self.user, None, server_name="test")
        self.p = c.Path(self.home)

    def test_cwd(self):

        self.debug(str(self.p.cwd()))
        self.debug(self.home)
        self.assertEqual(str(self.p.cwd()), self.home)


if __name__ == '__main__':
    main()
