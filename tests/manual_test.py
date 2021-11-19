from ssh_utilities import Connection
from ssh_utilities.multi_connection import MultiConnection
from copy import deepcopy
import pickle
from ssh_utilities.utils import config_parser
from pprint import pprint

print(config_parser("/home/rynik/.ssh/config").lookup("*"))
Connection.available_hosts["wigner"]["identityfile"] = None
pprint(Connection.available_hosts)
#Connection("*")

c = Connection("wigner")
print(c.os.listdir("/home/rynik"))
print(str(c))
c1 = Connection.from_str(str(c))
print(c1.os.listdir("/home/rynik"))

"""
c = Connection("kohn", quiet=True, local=False)

pat = "home/rynik/Raid/dizertacka/train_Si/ge_DPMD/train/gen?/train[0-9]/ge_all_*.pb"

print(list(c.pathlib.Path("/").glob(pat)))

c = Connection("kohn", quiet=True, local=False)
print(c.os.path.isfile("/home/rynik/hw_config_Kohn.log"))

c1 = deepcopy(c)
c2 = pickle.loads(pickle.dumps(c))
print(c1.os.path.isfile("/home/rynik/hw_config_Kohn.log"))
print(c2.os.path.isfile("/home/rynik/hw_config_Kohn.log"))

print(id(c), id(c1), id(c2))

mc = MultiConnection(["kohn"], quiet=True)
for out in mc.os.path.isfile("/home/rynik/hw_config_Kohn.log"):
    print(out)
    mc.keys()
    mc.values()

mc1 = pickle.loads(pickle.dumps(mc))
print(id(mc), id(mc1))

for n in mc1.os.name:
    print(n)

for p in mc1.pathlib.Path("/home/rynik"):
    print(p.is_dir())

a = mc.to_dict()
mc.clear()

with MultiConnection(["kohn"], quiet=True) as mc:
    print(type(mc))
    print(type(mc.os))
    print(type(mc.os.path))
    print(type(mc.os.scandir))
    print(type(mc.os.path.isfile))
    for out in mc.os.path.isfile("/home/rynik/hw_config_Kohn.log"):
        print(out)

mcl = MultiConnection.from_dict(a, quiet=True)
k = mcl["kohn"]
print("id", id(MultiConnection))
print(k.os.path.isfile)
print(k.os.path.isfile("/home/rynik/hw_config_Kohn.log"))
#print(mcl["fock"].os.path.isfile("/home/rynik/hw_config_Kohn.log"))
print("---------------")
for o in mcl.os.path.isfile("/home/rynik/hw_config_Kohn.log"):
    print(o)


print("..............................................................")
with Connection("kohn", quiet=True, local=False) as c:
    print(c.os.path.isfile("/home/rynik/hw_config_Kohn.log"))

    con = str(c)

c = Connection.from_str(con, quiet=True)
print(c.os.path.isfile("/home/rynik/hw_config_Kohn.log"))

A = TypeVar("A")
B = TypeVar("B")
T = TypeVar("T")


class FunctorInstance(Generic[T]):
    def __init__(
        self, map: Callable[[Callable[[A], B], Kind1[T, A]], Kind1[T, B]]
    ):
        self._map = map

    def map(self, x: Kind1[T, A]) -> Kind1[T, A]:
        return self._map(f, x)


f = FunctorInstance[List]()

l: List[str] = ["a"]
reveal_type(f.map(l))

# h = HasValue[int].with_value(int)


from typing import TypeVar, Generic, List

Val = TypeVar("Val")

class MyGeneric(Generic[Val]):
    def __init__(self, a: Val): ...

T = TypeVar("T")

SingleG = MyGeneric[T]
ListG = MyGeneric[List[T]]

def listify_my_generic(g: SingleG[T]) -> ListG[T]:
    ...


listify_my_generic(MyGeneric(1))

reveal_type(listify_my_generic(MyGeneric(1)))


@kinded
def to_str(arg: Kind1[T, int]) -> Kind1[T, str]:
    ...

reveal_type(to_str([1, 2]))

with Connection("hartree") as c:

    try:
        ls = c.subprocess.run(["ls", "-l"], suppress_out=False, quiet=False,
                   stdout=PIPE, stderr=DEVNULL, check=True, cwd=Path("/home/rynik"),
                   encoding="utf-8")
    except CalledProcessError as e:
        print(e)
    else:
        print(ls)

    print(c.pathlib.Path("/tmp"))
    files = c.pathlib.Path("/tmp").glob("*")
    print(files)
    for f in files:
        print(f)

    c.shutil.download_tree(Path("/home/rynik/test"), "/home/rynik", include="*.txt",
                           remove_after=False)
"""

#c.download_tree("/home/rynik/lammps_tests", "/home/rynik/OneDrive/dizertacka/code/ssh_utilities/test", include="*.in", exclude="*data*", remove_after=False)
#c.upload_tree("/home/rynik/OneDrive/dizertacka/code/ssh_utilities/test", "/home/rynik/lammps_tests", remove_after=False)


"""

s = shelve.open("test_shelve", writeback=True)

c = Connection("fock")
c.isfile("/home/rynik")

s["c"] = c

s.close()

s = shelve.open("test_shelve", writeback=True)

s["c"].isfile("/home/rynik")




lck = Lock()

q = Queue()
q1 = Queue()
q2 = Queue()
l = list()

for i in range(100000):
    q.put(np.empty((500, 500)))
    q1.put(np.empty((500, 500)))
    q2.put(dict(a=np.empty((500, 500)), b=np.empty((500, 500))))
    l.append(np.empty((500, 500)))

t = perf_counter()

for i in range(100000):
    with lck:
        a = l[i]

print(f"list time  = {perf_counter() - t:.6f}")

t = perf_counter()

for i in range(100000):
    #a = q.get()
    #q.put(a)
    a = q.get()
    b = q1.get()
    #a, b = list(q2.get().values())


print(f"queue time = {perf_counter() - t:.6f}")

c = Connection("fock")
c.sftp
p = c.Path("/home/rynik")

print(p)
print(p.resolve())
print(p.cwd())
print(p.home())

print("create new")
new = p / "test_ssh_utils_new"
new.unlink()
#new = new.rename("test_ssh_utils_new")
print(type(new))

print(new)
#print(new.stat)
print(new.exists())
print(new.is_dir())
print(new.is_file())
new.write_text("ajhoj")
print(new.read_text())
#print([d for d in new.glob("*.v*")])


out = c.run(["ls -l"], suppress_out=True, quiet=False, capture_output=True, cwd="~/Raidd")

print("out", out.stdout)
print("err", out.stderr)
print(out.args)
print(out.returncode)
"""
