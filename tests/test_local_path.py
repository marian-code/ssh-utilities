"""Testring of SSHPath.

Warnings
--------
Will need to rethink this as obviously testing this functionallity in some
CI system proves rather difficult.
"""

import logging
import os
import sys
from pathlib import Path
from unittest import TestCase, main

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
        self.p = c.pathlib.Path(self.home)

    def test_cwd(self):

        log.debug(str(self.p.cwd()))
        log.debug(self.home)
        self.assertEqual(str(self.p.cwd()), str(Path.cwd()))


if __name__ == '__main__':
    main()
