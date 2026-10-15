# -*- coding: utf-8 -*-
r"""指纹重配：surftype_10504(pack 面号空间) → surftype_swap3(reload 副本面号空间)"""
import io, json, math, re

BASE = r"C:\Users\dth15\Desktop\ANSYS"
LOG = BASE + r"\automation\logs"

src = json.load(io.open(LOG + r"\surftype_10504.json", encoding="utf-8"))["geom_surftype"]
tgt = json.load(io.open(LOG + r"\surftype_swap3.json", encoding="utf-8"))["geom_surftype"]

src_idx = {}
for gid, rows in src.items():
    if gid.startswith("ERR"):
        continue
    for r in rows:
        if len(r) >= 6 and r[2] is not None:
            src_idx[r[0]] = (gid, r[1], r[2], r[3], r[4], r[5])

tgt_list = []
for gid, rows in tgt.items():
    if gid.startswith("ERR"):
        continue
    for r in rows:
        if len(r) >= 6 and r[2] is not None:
            tgt_list.append((gid, r[0], r[1], r[2], r[3], r[4], r[5]))

print("src faces =", len(src_idx), "| tgt faces =", len(tgt_list))

plan = json.load(io.open(LOG + r"\repair_plan_src.json", encoding="utf-8"))
need = set()
for j in plan:
    need.update(j.get("mids", []))
    need.update(j.get("rids", []))
print("需要重配的面号 =", len(need))

def nm_tp(t):
    return t.split(".")[-1] if isinstance(t, str) else str(t)

mapping = {}
bad = []
for fid in sorted(need):
    f = src_idx.get(fid)
    if f is None:
        bad.append((fid, "NO_SRC"))
        continue
    gid, area, cx, cy, cz, tp = f
    best = None
    bestc = 1e9
    for (tgid, tid, tarea, tcx, tcy, tcz, ttp) in tgt_list:
        if nm_tp(ttp) != nm_tp(tp):
            continue
        dc = math.sqrt((cx - tcx) ** 2 + (cy - tcy) ** 2 + (cz - tcz) ** 2) * 1000.0
        da = abs(tarea - area) / max(area, 1e-12) * 100.0
        c = dc + da * 0.05
        if c < bestc:
            bestc = c
            best = (tid, dc, da, tgid)
    if best is None:
        bad.append((fid, "NO_MATCH"))
        continue
    tid, dc, da, tgid = best
    ok = (dc < 3.0 and da < 5.0)
    mapping[str(fid)] = {"new": tid, "dc_mm": round(dc, 3), "da_pct": round(da, 3), "src_gid": gid, "tgt_gid": tgid, "ok": ok}
    if not ok:
        bad.append((fid, "WEAK dc=%.2f da=%.2f%% -> %s" % (dc, da, tid)))

json.dump(mapping, io.open(LOG + r"\face_remap_swap3.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

oks = [v for v in mapping.values() if v["ok"]]
print("重配成功(严判) = %d / %d" % (len(oks), len(need)))
dcs = sorted(v["dc_mm"] for v in mapping.values())
das = sorted(v["da_pct"] for v in mapping.values())
print("质心差中位/最大 = %.3f / %.3f mm" % (dcs[len(dcs)//2], dcs[-1]))
print("面积差中位/最大 = %.3f / %.3f %%" % (das[len(das)//2], das[-1]))
print()
print("=== 非严判通过项 ===")
for fid, why in bad:
    print("  ", fid, why)
# 顺带展示几个样例
print()
print("=== 样例（前 8）===")
for fid in sorted(mapping, key=lambda x: int(x))[:8]:
    v = mapping[fid]
    print("  %5s -> %5d  dc=%.3fmm da=%.3f%%" % (fid, v["new"], v["dc_mm"], v["da_pct"]))
