from ssh_utilities import Connection, PIPE, DEVNULL
from ssh_utilities.exceptions import CalledProcessError
from pathlib import Path


# PythonDecorators/decorator_with_arguments.py
class decorator_with_arguments(object):

    def __new__(cls, decorated_function=None, **kwargs):

        self = super().__new__(cls)
        self._init(**kwargs)

        if not decorated_function:
            return self
        else:
            return self.__call__(decorated_function)

    def _init(self, arg1="default", arg2="default", arg3="default"):
        self.arg1 = arg1
        self.arg2 = arg2
        self.arg3 = arg3

    def __call__(self, decorated_function):

        def wrapped_f(*args):
            print("Decorator arguments:", self.arg1, self.arg2, self.arg3)
            print("decorated_function arguments:", *args)
            decorated_function(*args)

        return wrapped_f

@decorator_with_arguments(arg1=5)
def sayHello(a1, a2, a3, a4):
    print('sayHello arguments:', a1, a2, a3, a4)


sayHello(1, 2, 3, 4)


"""
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

c = Connection.get_connection("fock")
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

c = Connection.get_connection("fock")
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
