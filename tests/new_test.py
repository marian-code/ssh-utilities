from typing import Any


class A:

    def ahoj(self):
        print("ahoj")

    def __enter__(self):
        print("enter")
        return self

    def __exit__(self, *args):
        pass


class C:

    def __new__(cls) -> Any:
        print("neeew")
        return A()
    

C().ahoj()
print("--------------")

with C() as c:
    c.ahoj()


from ssh_utilities import Connection

c = Connection("kohn")
print(c.address)
c.close()

with Connection("kohn") as c:
    print(c.address)


c = Connection["kohn"]
print(c.address)
c.close()