import io, json
OUT = r"C:\Users\dth15\Desktop\ANSYS\automation\logs\geo_reload_clean.json"
def s(x):
    try:
        return str(x)
    except Exception:
        return "?"
out = {}
def flush():
    with io.open(OUT, "w", encoding="utf-8") as f:
        f.write(json.dumps(out, ensure_ascii=False))
deleted = 0
errs = []
for g in Model.Connections.Children:
    for j in list(g.Children):
        try:
            nm = j.Name
            if nm.startswith(u"\u63a5\u5934"):
                j.Delete()
                deleted += 1
        except Exception as e:
            errs.append(repr(e)[:80])
out["deleted"] = deleted
out["errs"] = errs[:6]
flush()
# 复查
tot = 0
states = {}
for g in Model.Connections.Children:
    try:
        n = len(g.Children)
        tot += n
        for j in g.Children:
            st = "?"
            try:
                st = s(j.ObjectState)
            except Exception:
                pass
            states[st] = states.get(st, 0) + 1
    except Exception:
        pass
out["after_total"] = tot
out["after_states"] = states
flush()
out["stage"] = "CLEAN DONE"
flush()
print("CLEAN DONE")
