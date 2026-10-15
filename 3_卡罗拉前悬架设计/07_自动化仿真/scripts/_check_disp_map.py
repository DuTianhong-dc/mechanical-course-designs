# -*- coding: utf-8 -*-
r"""验证 disp 点序↔节点序映射 + 识别尾部 323 个点 + 校验关键节点坐标"""
import struct, re, io

DISP = r"C:\Users\dth15\Desktop\ANSYS\v3_run_AUTO\res5s.disp"
DFS = r"C:\Users\dth15\Desktop\ANSYS\suspension_v3_Mech_Files\Transient\file.dfs"
OUT = r"C:\Users\dth15\Desktop\ANSYS\automation\logs\disp_map_check.txt"

w = io.open(OUT, "w", encoding="utf-8")
raw = open(DISP, "rb").read()
N = 114097
FS = 2738345

def pt(fr, idx):
    off = 100 + fr * FS + 8 + idx * 24
    return struct.unpack("<3d", raw[off:off + 24])

def frames():
    return (len(raw) - 100) // FS

w.write("帧数 = %d（t = 0 .. %.2f s）\n\n" % (frames(), (frames() - 1) * 0.02))

# 1) 关键节点自检（对照 S2 输出的 FBODY MASTER 坐标）
w.write("== 关键节点坐标自检（帧0）==\n")
expect = [
    (113713, (3.7871e+01, -5.3421e+01, 1.0869e+03), "FBODY0 转向节#52 master"),
    (113714, (-1.1557e+02, -6.1654e+02, 1.2676e+03), "FBODY1 #64 master"),
    (113764, (-1.1307e+02, -5.7133e+02, 1.2572e+03), "FBODY2 #70 master"),
    (113739, (-1.0437e+02, -4.1425e+02, 1.2210e+03), "FBODY3 #73 master"),
]
for idx, exp, name in expect:
    v = pt(0, idx)
    d = max(abs(v[k] - exp[k]) for k in range(3))
    w.write("  pt[%d] %s | 实测(%.2f,%.2f,%.2f) 期望(%.1f,%.1f,%.1f) maxdiff=%.2f %s\n"
            % (idx, name, v[0], v[1], v[2], exp[0], exp[1], exp[2], d, "OK" if d < 2 else "FAIL"))

# 2) 尾部 323 个点（113774..114096）抽样看坐标
w.write("\n== 尾部点（113774..114096）抽样 ==\n")
for idx in (113774, 113775, 113776, 113780, 113800, 113850, 113900, 114000, 114096):
    v = pt(0, idx)
    w.write("  pt[%d] = (%.4f, %.4f, %.4f)\n" % (idx, v[0], v[1], v[2]))

# 3) 与 MARKER 段坐标比对（找哪些尾部点是 marker）
data = open(DFS, "rb").read()
m = re.search(rb"! MARKER !+\r\n", data)
j = m.end()
mk = []
while j < len(data):
    k = data.find(b"\r\n", j)
    line = data[j:k]
    if line.lstrip().startswith(b"!"):
        break
    if line.strip():
        tk = line.split()
        try:
            mk.append((int(tk[0]), tk[1].decode("ascii", "replace"),
                       float(tk[4]), float(tk[5]), float(tk[6])))
        except Exception:
            pass
    j = k + 2
w.write("\nmarker 数 = %d\n" % len(mk))
# 拿尾部点找最接近的 marker
import math
def d3(a, b):
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))

hit = 0
for idx in range(113774, min(114097, 113774 + 60)):
    v = pt(0, idx)
    best = None
    for mid, name, x, y, z in mk:
        dd = d3(v, (x, y, z))
        if best is None or dd < best[0]:
            best = (dd, mid, name)
    if best[1] < 999 and best[0] < 1.0:
        hit += 1
        w.write("  pt[%d] -> marker %d %s (d=%.3f)\n" % (idx, best[1], best[2][:50], best[0]))
    else:
        w.write("  pt[%d] -> 最近 marker %d %s (d=%.2f)\n" % (idx, best[1], best[2][:40], best[0]))
w.write("前 60 个尾部点中命中 marker 的 = %d\n" % hit)

# 4) 最后一行 NBODY 节点名
j = m_pos = None
m2 = re.search(rb"! NBODY !+\r\n", data)
j = m2.end()
last = None
cnt = 0
while j < len(data):
    k = data.find(b"\r\n", j)
    line = data[j:k]
    if line.lstrip().startswith(b"!"):
        break
    if line.strip():
        last = line
        cnt += 1
    j = k + 2
w.write("\nNBODY 总行数 = %d；最后一行: %r\n" % (cnt, last[:150]))

w.close()
print("done")
