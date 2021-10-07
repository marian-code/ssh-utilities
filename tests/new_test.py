from ssh_utilities.remote.remote import SSHConnection
from typing import Any
from ssh_utilities import Connection
"""

with Connection("kohn") as c:
    c: SSHConnection
    for d in c.os.scandir("/home/rynik"):
        print(d.name, d.is_dir())
# !!! Function and context manager at the same time !!!
class A:

    def __init__(self) -> None:
        self.i = 0

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def __iter__(self):
        return self

    def __next__(self):
        if self.i < 10:
            try:
                return self.i
            finally:
                self.i += 1
        else:
            raise StopIteration

    def close(self):
        pass


with A() as b:
    for i in b:
        print(i)
print("----------------------------")

b = A()
for i in b:
    print(i)
#print(b.attr)

class C:

    def __new__(cls) -> Any:
        print("neeew")
        return A()
    

C().ahoj()
print("--------------")

with C() as c:
    c.ahoj()

"""

from ssh_utilities import Connection

with Connection("kohn") as c:
    #p = c.pathlib.Path("/home/rynik/test")
    #p.mkdir()
    #p.rmdir()

    #p = c.pathlib.Path("/home/rynik/.bashrc")
    #print(p.is_dir())
    #print(p.read_text())
    #print(p.read_bytes())

    p = c.pathlib.Path("/home/rynik/dpmd/selective_metad1/gen44")
    print(c.os.chmod(p, 111))
    print(c.sftp.normalize("/home/rynik/dpmd"))
    #print(p)
    #for pp in p.rglob("*"):
    #    print(pp, type(pp))
    #for root, dirs, files in c.os.walk(p):
    #    print(root, dirs, files)