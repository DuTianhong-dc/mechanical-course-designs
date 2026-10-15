# -*- coding: utf-8 -*-
r"""修复 v2：用重配后的面号重设 33 关节 scoping（服务端 unicode 名字匹配）"""
import io, json, re
from ansys.mechanical.core import connect_to_mechanical

BASE = r"C:\Users\dth15\Desktop\ANSYS"
LOG = BASE + r"\automation\logs"
OUT = LOG + r"\geo_repair_result2.json"

def unesc(s):
    if not isinstance(s, str):
        return s
    s2 = re.sub(r"\\u([0-9a-fA-F]{4})", lambda m: chr(int(m.group(1), 16)), s)
    m = re.match(r"^u?'(.*)'$", s2, re.S)
    return m.group(1) if m else s2

plan = json.load(io.open(LOG + r"\repair_plan_src.json", encoding="utf-8"))
remap = json.load(io.open(LOG + r"\face_remap_swap3.json", encoding="utf-8"))
ALIAS = {
    u"横拉杆-地（球铰）": u"横拉杆-地（通用）",
    u"平移的 - 接地 位于 无选择": u"转向节_轮心跳动（平移）",
}

def map_ids(ids):
    out = []
    for m in ids:
        v = remap.get(str(m))
        assert v, "unmapped %s" % m
        out.append(v["new"])
    return out

PLAN = []
for j in plan:
    nm = unesc(j["name"])
    if nm == u"弹簧力元素":
        continue
    mids = map_ids(j.get("mids", []))
    rids = map_ids(j.get("rids", []))
    if not mids and not rids:
        continue
    nm = ALIAS.get(nm, nm)
    PLAN.append((nm, mids, rids))

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
    rec = {"name": nm.encode("unicode_escape").decode("ascii")[:60]}
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
        rec["before"] = s(target.ObjectState)
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

out = {"results": results, "total_joints": tot, "states": states}
with io.open(OUT, "w", encoding="utf-8") as f:
    f.write(json.dumps(out, ensure_ascii=False))
print("REPAIR2 DONE")
''')

script = "\n".join(lines)
mech = connect_to_mechanical(port=10506, transport_mode="insecure", cleanup_on_exit=False)
r = mech.run_python_script(script)
print("run:", str(r)[:100])
d = json.load(io.open(OUT, encoding="utf-8"))
print("总数 =", d["total_joints"], "| 状态 =", d["states"])
okk = miss = err = 0
for rec in d["results"]:
    st = rec.get("set", "?")
    if st == "OK":
        okk += 1
        if rec.get("before") != rec.get("after"):
            print("  [%s -> %s] %s" % (rec.get("before"), rec.get("after"), rec.get("name")[:52]))
    elif st == "MISS":
        miss += 1
        print("  MISS:", rec.get("name"))
    else:
        err += 1
        print("  ERR :", rec.get("name"), st[:70])
print()
print("设置成功 %d | MISS %d | ERR %d" % (okk, miss, err))
