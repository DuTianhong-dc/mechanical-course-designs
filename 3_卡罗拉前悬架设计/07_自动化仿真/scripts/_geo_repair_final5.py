# -*- coding: utf-8 -*-
r"""最后一口：设置 4 球座-球壳 + 修复关节（用修正后的面号），复查，保存"""
import io, json
from ansys.mechanical.core import connect_to_mechanical

LOG = r"C:\Users\dth15\Desktop\ANSYS\automation\logs"
OUT = LOG + r"\geo_repair_final5.json"

fix = json.load(io.open(LOG + r"\ball_remap_fix.json", encoding="utf-8"))
balls = fix["balls"]
fx = fix["fixjoint"]

PLAN = []
for nm, v in balls.items():
    PLAN.append((nm + u"（固定）", v["mids"], v["rids"]))
PLAN.append((u"平移的 - 无选择 位于 无选择", [fx["mid(活塞)"]], [fx["ref(顶胶_内层)"]]))

def esc_u(u):
    return u.encode("unicode_escape").decode("ascii")

lines = []
lines.append("import io, json")
lines.append('OUT = r"%s"' % OUT)
lines.append("def s(x):")
lines.append("    try: return str(x)")
lines.append("    except Exception:")
lines.append("        try: return repr(x)")
lines.append("        except Exception: return '?'")
lines.append("PLAN = [")
for nm, mids, rids in PLAN:
    lines.append('  (u"%s", %s, %s),' % (esc_u(nm), mids, rids))
lines.append("]")
lines.append(r'''
def mk(ids):
    sel = ExtAPI.SelectionManager.CreateSelectionInfo(SelectionTypeEnum.GeometryEntities)
    sel.Ids = list(ids)
    return sel

allj = []
for g in Model.Connections.Children:
    for j in g.Children:
        allj.append(j)

results = []
for (nm, mids, rids) in PLAN:
    rec = {"name": nm.encode("unicode_escape").decode("ascii")[:70]}
    target = None
    for j in allj:
        try:
            if j.Name == nm:
                target = j
                break
        except Exception:
            pass
    if target is None:
        rec["find"] = "MISS"
        results.append(rec)
        continue
    try:
        if mids:
            target.MobileLocation = mk(mids)
        if rids:
            target.ReferenceLocation = mk(rids)
        rec["set"] = "OK"
        rec["after"] = s(target.ObjectState)
    except Exception as e:
        rec["set"] = "ERR:%r" % e
        try:
            rec["after"] = s(target.ObjectState)
        except Exception:
            rec["after"] = "?"
    results.append(rec)

tot = 0
states = {}
for g in Model.Connections.Children:
    for j in g.Children:
        tot += 1
        try:
            st = s(j.ObjectState)
        except Exception:
            st = "?"
        states[st] = states.get(st, 0) + 1

out = {"results": results, "total": tot, "states": states}
try:
    ExtAPI.DataModel.Project.Save()
    out["save"] = "OK"
except Exception as e:
    out["save"] = "ERR:%r" % e

with io.open(OUT, "w", encoding="utf-8") as f:
    f.write(json.dumps(out, ensure_ascii=False))
print("FINAL5 DONE")
''')

script = "\n".join(lines)
mech = connect_to_mechanical(port=10506, transport_mode="insecure", cleanup_on_exit=False)
r = mech.run_python_script(script)
print("run:", str(r)[:100])
d = json.load(io.open(OUT, encoding="utf-8"))
for rec in d["results"]:
    print(" ", json.dumps(rec, ensure_ascii=False)[:160])
print("总数 =", d["total"], "| 状态 =", d["states"], "| 保存 =", d.get("save"))
