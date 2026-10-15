# -*- coding: utf-8 -*-
r"""SDOF 基础激励快筛 v2（用已验证的积分/差分逻辑）
   输出：理论 c_reb→RMS 曲线（k=33.3 与 240 N/mm 两条）+ 仿真点对照"""
import math

M = 482.0
A1 = 0.040
W = 2 * math.pi * 1.0
DT = 0.0005
TS = 0.02
T_END = 1.6
C_COMP = 1700.0

def run_case(c_reb, k):
    n = int(T_END / DT)
    se = int(round(TS / DT))
    z = 0.0
    zd = 0.0
    ys = []
    for i in range(n + 1):
        t = i * DT
        y1 = A1 * math.sin(W * t)
        y1dd = -A1 * W * W * math.sin(W * t)
        c = c_reb if zd >= 0 else C_COMP
        zdd = (-c * zd - k * z) / M - y1dd
        zd += zdd * DT
        z += zd * DT
        if i % se == 0:
            ys.append(z + y1)
    acc = []
    for j in range(1, len(ys) - 1):
        a = (ys[j+1] - 2*ys[j] + ys[j-1]) / (TS*TS)
        acc.append(a)
    sel = [a for idx, a in enumerate(acc, start=1) if 0.5 <= idx*TS <= 1.38]
    return math.sqrt(sum(v*v for v in sel)/len(sel)) if sel else 0.0

print("=== 理论 vs 仿真（RMS m/s2 | 0.5-1.38s 口径）===")
print("仿真实测: 2.0→1.693 | 3.41→1.493 | 4.5→1.411 | (6.0 待出)")
print()
for k in [33.3e3, 240e3]:
    fn = math.sqrt(k/M)/(2*math.pi)
    print("---- k=%.1f N/mm (fn=%.2f Hz) ----" % (k/1000, fn))
    curve = []
    for c in range(1000, 16501, 500):
        r = run_case(float(c), k)
        curve.append((c/1000.0, r/1000))
    best = min(curve, key=lambda x: x[1])
    print("理论最优: c_reb=%.2f N·s/mm → RMS_min=%.3f" % best)
    for c in [2.0, 3.41, 4.5, 6.0]:
        r = run_case(c*1000.0, k)
        print("  仿真点 c_reb=%.2f → 理论RMS=%.3f" % (c, r/1000))
    s = "  curve: "
    for c, r in curve[::4]:
        s += "(%.1f,%.3f)" % (c, r)
    print(s)
    print()
