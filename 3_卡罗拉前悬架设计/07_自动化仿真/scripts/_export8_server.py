import io, json, time

OUT = r"__OUT__"

def s(x):
    try:
        return str(x)
    except:
        try:
            return repr(x)
        except:
            return "?"

out = {}

def flush():
    with io.open(OUT, "w", encoding="utf-8") as f:
        f.write(json.dumps(out, ensure_ascii=False, indent=1))

a = Model.Analyses[0]
out["pre"] = {"mesh": s(Model.Mesh.ObjectState), "geom": s(Model.Geometry.ObjectState)}
flush()

t0 = time.time()
try:
    a.Solve()
    out["solve"] = "OK"
except Exception as e:
    out["solve"] = "ERR:%r" % e
out["solve_s"] = round(time.time() - t0, 1)
flush()

import os
dr = a.SolverFilesDirectory
target = os.path.join(dr, "file.dfs")
found = False
size = 0
for i in range(300):
    try:
        if os.path.exists(target):
            found = True
            size = os.path.getsize(target)
            break
    except:
        pass
    time.sleep(2)
out["dfs_found"] = found
out["dfs_size"] = size
flush()

fs = []
try:
    for root, dirs, files in os.walk(dr):
        for f in files:
            try:
                p = os.path.join(root, f)
                fs.append([p.replace(dr, ""), os.path.getsize(p)])
            except:
                pass
except:
    pass
out["files"] = fs[:60]
flush()
print("EXPORT8 DONE")
