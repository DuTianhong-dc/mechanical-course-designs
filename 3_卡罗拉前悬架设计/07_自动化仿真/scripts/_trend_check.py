# -*- coding: utf-8 -*-
r"""长时程趋势判读（0.2s+ 冒烟/长跑通用，支持部分帧）
   用法: python _trend_check.py <disp路径> [总时长s=5.0] [总步数=250]
   判据（v3 规模）:
     - 治愈: 482kg Y 振荡有界（±160mm 内 = 近共振物理大摆）；rel(56-6) 浮动 ±5-8mm
     - 病态: 482kg Y 单调加速下坠（0.2s≈72mm、0.8s≈1300mm）；rel 发散
   ⚠️ 10ms 内的 -25mm "穿透" = 正常静载下沉瞬态，无判读价值（2026-10-13 定案）"""
import struct, math, sys

FS = 2738345  # v3 规模帧长（113709 节点 + 388 实体点，各 24B + 8B 时间 + 9B 尾）

def ent(raw, fr, g):
    return struct.unpack_from("<3d", raw, 100 + fr * FS + 8 + (113709 + g * 4) * 24)

def main(path, tmax=5.0, ntotal=250):
    raw = open(path, "rb").read()
    NF = (len(raw) - 100) // FS
    p56, p6, p66, p5 = (ent(raw, 0, g) for g in (56, 6, 66, 5))
    ax = (0.0539, 0.9731, -0.2241)  # 减振器杆轴（strut-down）
    dt = tmax / ntotal
    print("== %s | 已写 %d/%d 帧 | dt=%.1fms | 已覆盖 %.3fs" % (path, NF, ntotal + 1, dt * 1000, (NF - 1) * dt))
    print("t(s)   | 482kgY |  内层Y  |  法兰Y  | rel|d| 轴向 | 转向节Y")
    mx66 = 0.0
    for fr in range(0, NF, max(1, NF // 20)):
        d66 = ent(raw, fr, 66)[1] - p66[1]
        mx66 = max(mx66, abs(d66))
        d5 = ent(raw, fr, 5)[1] - p5[1]
        d56 = [ent(raw, fr, 56)[i] - p56[i] for i in range(3)]
        d6 = [ent(raw, fr, 6)[i] - p6[i] for i in range(3)]
        rel = [d56[i] - d6[i] for i in range(3)]
        a = sum(rel[i] * ax[i] for i in range(3))
        mag = math.sqrt(sum(x * x for x in rel))
        print("%6.3f | %7.2f | %7.2f | %7.2f | %6.2f %7.2f | %7.2f" %
              (fr * dt, d66, d56[1], d6[1], mag, a, d5))
    fr = NF - 1
    d66 = ent(raw, fr, 66)[1] - p66[1]
    print("末帧: 482kgY=%.2f 内层Y=%.2f 法兰Y=%.2f 转向节Y=%.2f" %
          (d66, ent(raw, fr, 56)[1] - p56[1], ent(raw, fr, 6)[1] - p6[1], ent(raw, fr, 5)[1] - p5[1]))
    if abs(d66) < 5 and mx66 < 30:
        print("[判读] 治愈（482kg 稳）")
    elif abs(d66) < 160:
        print("[判读] 振荡有界（疑似健康；峰值 %.0fmm，看向上部是否回摆）" % mx66)
    else:
        print("[判读] 病态（482kg 坠 %.0fmm）" % d66)

if __name__ == "__main__":
    a = sys.argv
    main(a[1] if len(a) > 1 else r"C:\Users\dth15\Desktop\ANSYS\v3_run_R1\resR1L.disp",
         float(a[2]) if len(a) > 2 else 0.2,
         int(a[3]) if len(a) > 3 else 100)


