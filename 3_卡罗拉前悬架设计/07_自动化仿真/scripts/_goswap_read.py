# -*- coding: utf-8 -*-
r"""GOSWAP 趋势判读（0.2s+ 通用，支持部分帧）
   组号（2026-10-13 位置交叉锚定）：
     482kg 质量块 = g61  (v3 g66, pos -116.275,-629.227,1270.485)
     内层 = g50 (v3 g56)  法兰 = g8 (v3 g6)  转向节 = g11 (v3 g5)
   用法: python _goswap_read.py <disp路径> [总时长s=0.2] [总步数=100]"""
import struct, math, sys

FS = 1074353
NB = 44412

G_482 = 61
G_IN = 50   # 顶胶内层
G_FL = 8    # 顶胶法兰层
G_KNU = 11  # 转向节(轮心)

def ent(raw, fr, g):
    base = 108 + fr * FS + (NB + g * 4) * 24
    return struct.unpack_from("<3d", raw, base)

def main(path, tmax=0.2, ntotal=100):
    raw = open(path, "rb").read()
    NF = (len(raw) - 100) // FS
    p482 = ent(raw, 0, G_482)
    p50 = ent(raw, 0, G_IN)
    p8 = ent(raw, 0, G_FL)
    p11 = ent(raw, 0, G_KNU)
    ax = (0.0539, 0.9731, -0.2241)  # 减振器杆轴
    dt = tmax / ntotal
    print("== %s | 已写 %d/%d 帧 | dt=%.1fms | 已覆盖 %.3fs" % (path.split('/')[-1], NF, ntotal + 1, dt * 1000, (NF - 1) * dt))
    print("t(s)   | 482kgY |  内层Y  |  法兰Y  | rel|d| 轴向 | 转向节Y")
    mx = 0.0
    for fr in range(0, max(NF, 1), max(1, NF // 20)):
        d482 = ent(raw, fr, G_482)[1] - p482[1]
        mx = max(mx, abs(d482))
        d50 = ent(raw, fr, G_IN)[1] - p50[1]
        d8 = ent(raw, fr, G_FL)[1] - p8[1]
        d11 = ent(raw, fr, G_KNU)[1] - p11[1]
        r3 = [ent(raw, fr, G_IN)[i] - p50[i] - (ent(raw, fr, G_FL)[i] - p8[i]) for i in range(3)]
        a = sum(r3[i] * ax[i] for i in range(3))
        mag = math.sqrt(sum(x * x for x in r3))
        print("%6.3f | %7.2f | %7.2f | %7.2f | %6.2f %7.2f | %7.2f" %
              (fr * dt, d482, d50, d8, mag, a, d11))
    fr = NF - 1
    d482 = ent(raw, fr, G_482)[1] - p482[1]
    print("末帧: 482kgY=%.2f 内层Y=%.2f 法兰Y=%.2f 转向节Y=%.2f" %
          (d482, ent(raw, fr, G_IN)[1] - p50[1], ent(raw, fr, G_FL)[1] - p8[1], ent(raw, fr, G_KNU)[1] - p11[1]))
    if abs(d482) < 5 and mx < 30:
        print("[判读] 482kg 稳（治愈口径）")
    elif abs(d482) < 160:
        print("[判读] 振荡有界（峰值 %.1fmm，健康口径）" % mx)
    else:
        print("[判读] 病态（482kg 坠 %.0fmm）" % d482)

if __name__ == "__main__":
    a = sys.argv
    main(a[1] if len(a) > 1 else r"C:\Users\dth15\Desktop\ANSYS\v3_run_GOSWAP02\resG02.disp",
         float(a[2]) if len(a) > 2 else 0.2,
         int(a[3]) if len(a) > 3 else 100)
