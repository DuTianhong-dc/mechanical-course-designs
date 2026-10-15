import io, json
OUT = r"C:\Users\dth15\Desktop\ANSYS\automation\logs\geo_finalize.json"
def s(x):
    try:
        return str(x)
    except Exception:
        return "?"
out = {}
def flush():
    with io.open(OUT, "w", encoding="utf-8") as f:
        f.write(json.dumps(out, ensure_ascii=False))

# 1) 找残余 UD（排除接头）
uds = []
for g in Model.Connections.Children:
    for j in g.Children:
        try:
            st = s(j.ObjectState)
            nm = j.Name
        except Exception:
            continue
        if st == "UnderDefined" and not nm.startswith(u"\u63a5\u5934"):
            rec = {"name": nm.encode("unicode_escape").decode("ascii")[:60], "grp": s(g.Name).encode("unicode_escape").decode("ascii")[:20]}
            try:
                rec["sup"] = s(j.Suppressed)
            except Exception:
                pass
            uds.append(rec)
out["residual_ud"] = uds
flush()

# 2) 清接头
deleted = 0
for g in Model.Connections.Children:
    for j in list(g.Children):
        try:
            if j.Name.startswith(u"\u63a5\u5934"):
                j.Delete()
                deleted += 1
        except Exception:
            pass
out["deleted_jietou"] = deleted
flush()

# 3) 复查 + 保存
tot = 0
states = {}
names = []
for g in Model.Connections.Children:
    for j in g.Children:
        tot += 1
        try:
            st = s(j.ObjectState)
        except Exception:
            st = "?"
        states[st] = states.get(st, 0) + 1
out["total_after"] = tot
out["states_after"] = states
flush()
try:
    ExtAPI.DataModel.Project.Save()
    out["save"] = "OK"
except Exception as e:
    out["save"] = "ERR:%r" % e
flush()
out["stage"] = "FINALIZE DONE"
flush()
print("FINALIZE DONE")
