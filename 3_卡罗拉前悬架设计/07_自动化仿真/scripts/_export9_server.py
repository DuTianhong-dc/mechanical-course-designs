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

# 1) save first (keep user's change)
try:
    ExtAPI.DataModel.Project.Save()
    out["save"] = "OK"
except Exception as e:
    out["save"] = "ERR:%r" % e
flush()

a = Model.Analyses[0]

# report subroutine / formula states
findings = []
for c in a.Children:
    try:
        nm = c.Name.encode("utf-8").encode("hex")
        st = s(c.ObjectState)
        findings.append([nm, st])
    except:
        pass
out["analysis_children"] = findings
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
for i in range(240):
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
print("EXPORT9 DONE")
