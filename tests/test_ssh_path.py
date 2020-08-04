"""Testring of SSHPath.

Warnings
--------
Will need to rethink this as obviously testing this functionallity in some
CI system proves rather difficult.
"""

import logging
from ssh_utilities.constants import CONFIG_PATH
import sys
from unittest import TestCase, main
import os
from pathlib import Path
import subprocess

from ssh_utilities import Connection

logging.basicConfig(stream=sys.stderr)
log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)

CI = os.environ.get("TRAVIS", False)


class TestSSHPath(TestCase):
    """Test remote version of Path"""

    def setUp(self):

        self.user = os.environ.get("USER", "rynik")
        self.home = os.environ.get("HOME", Path.home())

        if CI:
            self.os = os.environ.get("TRAVIS_OS_NAME", "linux")

        # SSH to self, must have and localhost entry in config file and
        # correcponding keys pressent, also sshd must be installed and running
        if self.user == "rynik":
            c = Connection.get("localhost", local=False)
        else:
            """
            try:
                if self.os == "linux":
                    subprocess.run(["echo", f"'{self.user}:12345678'", "|",
                                    "sudo", "chpasswd"], check=True)
                elif self.os == "windows":
                    raise NotImplementedError
                elif self.os == "osx":
                    raise NotImplementedError
                else:
                    raise ValueError
            except subprocess.CalledProcessError as e:
                log.exception(e)
                raise e
            else:
            """
            c = Connection.open(self.user, "127.0.0.1", sshKey=None,
                                sshPassword="12345678", server_name="test")

        self.p = c.Path("/tmp")

    def test_cwd(self):

        log.debug(str(self.p.cwd()))
        log.debug(self.home)
        self.assertEqual(str(self.p.cwd()), self.home)


if __name__ == '__main__':
    main()
