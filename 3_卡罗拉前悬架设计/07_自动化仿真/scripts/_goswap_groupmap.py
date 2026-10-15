# -*- coding: utf-8 -*-
r"""GOSWAP disp 组号映射 v2：直存格式（96B/实体 = pos(3d) + rot(9d)）"""
import struct, json, math, io
from collections import defaultdict

DISP = r'C:/Users/dth15/Desktop/ANSYS/v3_run_GOSWAP/resG0.disp'
FACES = r'C:/Users/dth15/Desktop/ANSYS/automation/logs/faces_live_rep.json'
OUT = r'C:/Users/dth15/Desktop/ANSYS/automation/logs/goswap_groupmap.json'

FS = 1074353
NB = 44412
NG = 88

raw = open(DISP, 'rb').read()

def entpos(fr, g):
    base = 108 + fr * FS + (NB + g * 4) * 24
    x, y, z = struct.unpack_from('<3d', raw, base)
    return (x, y, z)

groups = []
for g in range(NG):
    pos = entpos(0, g)
    groups.append({"g": g, "pos_mm": [round(v, 3) for v in pos]})

print("=== all 88 entity positions (mm) ===")
for rec in groups:
    print("g%-3d %10.3f %10.3f %10.3f" % (rec["g"], rec["pos_mm"][0], rec["pos_mm"][1], rec["pos_mm"][2]))

d = json.load(io.open(FACES, encoding='utf-8'))

def nm(h):
    return bytes.fromhex(h).decode('utf-8') if h else '?'

agg = defaultdict(lambda: [0.0, 0.0, 0.0, 0.0])
for r in d['faces']:
    name = nm(r[1])
    a = r[3]
    agg[name][0] += r[4] * a
    agg[name][1] += r[5] * a
    agg[name][2] += r[6] * a
    agg[name][3] += a
cent = {}
for name, (sx, sy, sz, sa) in agg.items():
    if sa > 0:
        cent[name] = [sx / sa, sy / sa, sz / sa]

targets = ["顶胶_内层", "顶胶_法兰层", "转向节", "下摆臂_本体内层", "下摆臂_本体外层", "活塞", "上弹簧座", "减振器壳_筒身", "缓冲块", "转向横拉杆_本体", "球头总成_球壳_下摆臂", "衬套_内层金属1"]
result = {"ng": NG, "matches": {}}
print()
print("=== nearest group per target centroid ===")
for t in targets:
    if t not in cent:
        print("target missing:", t)
        continue
    cx, cy, cz = cent[t]
    best = None
    for rec in groups:
        x, y, z = rec["pos_mm"]
        d2 = math.sqrt((x - cx * 1000) ** 2 + (y - cy * 1000) ** 2 + (z - cz * 1000) ** 2)
        if best is None or d2 < best[0]:
            best = (d2, rec["g"])
    result["matches"][t] = {"g": best[1], "dc_mm": round(best[0], 2),
                            "centroid_mm": [round(cx * 1000, 2), round(cy * 1000, 2), round(cz * 1000, 2)]}
    print("%s -> g%d (dc=%.2f mm; centroid %.1f,%.1f,%.1f)" % (t, best[1], best[0], cx * 1000, cy * 1000, cz * 1000))

pm = (-104.34010572064437, -413.73129797501036, 1220.856314368297)
best = None
for rec in groups:
    x, y, z = rec["pos_mm"]
    d2 = math.sqrt((x - pm[0]) ** 2 + (y - pm[1]) ** 2 + (z - pm[2]) ** 2)
    if best is None or d2 < best[0]:
        best = (d2, rec["g"])
result["matches"]["点质量482kg"] = {"g": best[1], "dc_mm": round(best[0], 2)}
print("点质量482kg -> g%d (dc=%.2f mm)" % (best[1], best[0]))

io.open(OUT, 'w', encoding='utf-8').write(json.dumps(result, ensure_ascii=False, indent=1))
print("saved:", OUT)
