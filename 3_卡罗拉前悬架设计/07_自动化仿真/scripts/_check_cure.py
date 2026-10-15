# -*- coding: utf-8 -*-
r"""疗效判读：读 resR1i.disp，检验"活塞↔顶胶_内层"平移副是否治愈病症
  组号 = RBODY 0-66 + FBODY 0-29（97 组）
  关键对：
    组 56 //_____#70/RBE1693_R  (顶胶_内层)
    组 6  //______#64/RBE1442_R (顶胶_法兰层)
    组 5  转向节 / 组 66 482kg / 组 28 上弹簧座(?)
  判据（10ms）：
    S3 病症版：顶胶内层-法兰层 相对位移 ≈ -25mm
    治愈版：  应 < 1mm
"""
import struct, io, sys

DISP = sys.argv[1] if len(sys.argv) > 1 else r"C:\Users\dth15\Desktop\ANSYS\v3_run_R1\resR1i.disp"
OUT = r"C:\Users\dth15\Desktop\ANSYS\automation\logs\cure_check.txt"

raw = open(DISP, "rb").read()
FS = 2738345
NF = (len(raw) - 100) // FS

def pt(fr, idx):
    return struct.unpack_from("<3d", raw, 100 + fr * FS + 8 + idx * 24)

def ent(fr, g):
    return pt(fr, 113709 + g * 4)

w = io.open(OUT, "w", encoding="utf-8")
w.write("帧数 = %d (t=0..%.1fms)\n\n" % (NF, (NF - 1)))

# 关键组 Y 位移序列 + 相对位移
GRP = {"turnknuckle": 5, "topflange64": 6, "topinner70": 56, "mass482": 66, "seat": 28}
p0 = {}
for k, g in GRP.items():
    p0[k] = ent(0, g)

w.write("t(ms)  | 转向节Y | 顶胶内层Y | 顶胶法兰Y | 内层-法兰(相对) | 482kg Y\n")
worst = 0.0
for fr in range(NF):
    y5 = ent(fr, 5)[1] - p0["turnknuckle"][1]
    y56 = ent(fr, 56)[1] - p0["topinner70"][1]
    y6 = ent(fr, 6)[1] - p0["topflange64"][1]
    y66 = ent(fr, 66)[1] - p0["mass482"][1]
    rel = y56 - y6
    if abs(rel) > abs(worst):
        worst = rel
    w.write("%6.1f | %8.3f | %9.3f | %9.3f | %13.3f | %8.3f\n" % (fr * 1.0, y5, y56, y6, rel, y66))

w.write("\n=== 判读 ===\n")
w.write("顶胶内层-法兰层 相对位移 max|Δ| = %.3f mm\n" % worst)
if abs(worst) < 1.0:
    w.write(">>> 治愈！(S3 病症版为 -25mm)\n")
elif abs(worst) < 5.0:
    w.write(">>> 大幅改善但仍有余量\n")
else:
    w.write(">>> 仍存在明显病症\n")
w.close()
print(w.read() if False else "done -> %s" % OUT)
