from ssh_utilities import Connection
from ssh_utilities.exceptions import CalledProcessError
from pathlib import Path

with Connection("dusanko") as c:

    try:
        ls = c.run(["ls", "-l"], suppress_out=False, quiet=False,
                   capture_output=True, check=True, cwd=Path("/home/rynik"))
    except CalledProcessError as e:
        print(e)
    else:
        print(ls)

    c.download_tree(Path("/home/rynik/test"), "/home/rynik", include="*.txt",
                    remove_after=False)

    print(c.Path("/tmp"))
    files = c.Path("/tmp").glob("*")
    print(files)
    for f in files:
        print(f)


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
