"""Testing of SSHPath.

Test only SSH reimplemented parts, that means, no `PurePath` testing. We assume
that onece the right flavour is chosen the `PurePath` class will work as
intended.

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
import getpass
import socket
import subprocess

logging.basicConfig(stream=sys.stderr)
log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)

CI_T = os.environ.get("TRAVIS", False)
CI_G = os.environ.get("CI", False)  # github actions

CI = any((CI_T, CI_G))


class TestSSHPath(TestCase):
    """Test remote version of Path."""

    def setUp(self):

        def get_ip():
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            try:
                # doesn't even have to be reachable
                s.connect(('10.255.255.255', 1))
                IP = s.getsockname()[0]
            except Exception:
                IP = '127.0.0.1'
            finally:
                s.close()
            return IP

        self.user = os.environ.get("USER", "rynik")
        self.home = os.environ.get("HOME", Path.home())
        self.os = os.name

        # SSH to self, must have and localhost entry in config file and
        # correcponding keys present, also sshd must be installed and running
        if self.user == "rynik":
            c = Connection.get("kohn", local=False)
        # travis/git config file must change user password to desired
        else:
            c = Connection.open(self.user, "127.0.0.1", ssh_key_file=None,
                                ssh_password="12345678", server_name="test")
        # localhost = get_ip()
        # localhost = subprocess.run(["curl", "ifconfig.me"],
        #                            stdout=subprocess.PIPE,  # python 3.6
        #                            encoding="utf-8").stdout.strip()
        # Connection.add_hosts({
        #     "user": self.user,
        #     "hostname": localhost,
        #     "identityfile": "~/.ssh/id_rsa"
        # })
        # print(Connection.available_hosts)
        # c = Connection.get(localhost, local=False)

        self.p = c.pathlib.Path("/tmp")

    def test_flavour(self):
        pass

    def test_cwd(self):

        log.debug(str(self.p.cwd()))
        log.debug(self.home)
        self.assertEqual(str(self.p.cwd()), self.home)

    def test_home(self):
        pass


if __name__ == '__main__':
    main()
