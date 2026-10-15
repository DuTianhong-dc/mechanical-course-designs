# -*- coding: utf-8 -*-
r"""球区面重配修正：用 gid（所属body）约束消除同心球面的交叉错配 + 输出修复关节的面号"""
import io, json, math

LOG = r"C:\Users\dth15\Desktop\ANSYS\automation\logs"

src = json.load(io.open(LOG + r"\surftype_10504.json", encoding="utf-8"))["geom_surftype"]
tgt = json.load(io.open(LOG + r"\surftype_swap3.json", encoding="utf-8"))["geom_surftype"]
remap = json.load(io.open(LOG + r"\face_remap_swap3.json", encoding="utf-8"))

src_idx = {}
for gid, rows in src.items():
    if gid.startswith("ERR"):
        continue
    for r in rows:
        if len(r) >= 6 and r[2] is not None:
            src_idx[r[0]] = (gid, r[1], r[2], r[3], r[4], r[5])

tgt_by_gid = {}
tgt_all = []
for gid, rows in tgt.items():
    if gid.startswith("ERR"):
        continue
    lst = []
    for r in rows:
        if len(r) >= 6 and r[2] is not None:
            lst.append((r[0], r[1], r[2], r[3], r[4], r[5]))
    tgt_by_gid[gid] = lst
    tgt_all.extend([(gid,) + x for x in lst])

def nm_tp(t):
    return t.split(".")[-1] if isinstance(t, str) else str(t)

# --- gid 对应表：从高置信重配投票 ---
votes = {}
for fid, v in remap.items():
    if v["ok"] and v["dc_mm"] < 0.8:
        votes.setdefault(v["src_gid"], {})
        votes[v["src_gid"]][v["tgt_gid"]] = votes[v["src_gid"]].get(v["tgt_gid"], 0) + 1

gid_map = {}
for sg, cand in votes.items():
    gid_map[sg] = max(cand.items(), key=lambda kv: kv[1])[0]
print("gid 对应（投票）:")
for k in sorted(gid_map, key=lambda x: int(x)):
    print("  %s -> %s" % (k, gid_map[k]))

def best_in(fid, restrict_gid=None):
    f = src_idx.get(fid)
    if f is None:
        return None
    sg, area, cx, cy, cz, tp = f
    pool = tgt_by_gid.get(restrict_gid, []) if restrict_gid else [(g,) + x for x in tgt_all]
    # 统一 pool 元素: (gid, id, area, cx, cy, cz, tp)
    if restrict_gid:
        pool = [(restrict_gid, x[0], x[1], x[2], x[3], x[4], x[5]) for x in tgt_by_gid.get(restrict_gid, [])]
    best = None
    bestc = 1e9
    for (tgid, tid, tarea, tcx, tcy, tcz, ttp) in pool:
        if nm_tp(ttp) != nm_tp(tp):
            continue
        dc = math.sqrt((cx - tcx) ** 2 + (cy - tcy) ** 2 + (cz - tcz) ** 2) * 1000.0
        da = abs(tarea - area) / max(area, 1e-12) * 100.0
        c = dc + da * 0.05
        if c < bestc:
            bestc = c
            best = (tid, dc, da, tgid)
    return best

BALL = {
    u"下球座-球壳（下摆臂）": ([3061, 3062, 3063, 3064], [2832, 2833, 2835, 2836]),
    u"上球座-球壳（下摆臂）": ([3036, 3037], [2836, 2837, 2838]),
    u"下球座-球壳（横拉杆）": ([3073, 3074, 3075, 3076], [2971, 2972, 2974, 2975]),
    u"上球座-球壳（横拉杆）": ([3051, 3052], [2975, 2976, 2977]),
}

fixed = {}
print()
print("=== 球区重配（gid 约束）===")
for nm, (mids, rids) in BALL.items():
    print(" ", nm)
    mm = []
    rr = []
    for fid in mids:
        sg = src_idx[fid][0]
        tg = gid_map.get(sg)
        b = best_in(fid, tg)
        mm.append(b[0] if b else None)
        print("    mid %5d (srcgid %s -> tgtgid %s) => %s  dc=%.2f da=%.2f%%" % (fid, sg, tg, b[0] if b else None, b[1] if b else -1, b[2] if b else -1))
    for fid in rids:
        sg = src_idx[fid][0]
        tg = gid_map.get(sg)
        b = best_in(fid, tg)
        rr.append(b[0] if b else None)
        print("    ref %5d (srcgid %s -> tgtgid %s) => %s  dc=%.2f da=%.2f%%" % (fid, sg, tg, b[0] if b else None, b[1] if b else -1, b[2] if b else -1))
    fixed[nm] = {"mids": mm, "rids": rr}

# 修复关节（来自 meshtest 读回：活塞 2526 ↔ 顶胶_内层 2376）
print()
print("=== 修复关节面号 ===")
fx = {}
for tag, fid in [("mid(活塞)", 2526), ("ref(顶胶_内层)", 2376)]:
    sg = src_idx.get(fid, ("?",))[0]
    tg = gid_map.get(sg)
    b = best_in(fid, tg)
    print("  %s %d (srcgid %s -> tgtgid %s) => %s dc=%.2f da=%.2f%%" % (tag, fid, sg, tg, b[0] if b else None, b[1] if b else -1, b[2] if b else -1))
    fx[tag] = b[0] if b else None

json.dump({"balls": fixed, "fixjoint": fx}, io.open(LOG + r"\ball_remap_fix.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print()
print("saved -> ball_remap_fix.json")
