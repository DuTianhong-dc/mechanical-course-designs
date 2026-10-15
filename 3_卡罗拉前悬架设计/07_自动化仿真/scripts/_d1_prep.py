# -*- coding: utf-8 -*-
r"""D1 轮 prep：从 file_GOSWAP_INJ.dfs 生成 4 个 c_reb 扫描点（等宽文本替换）
   点：D1a=2.0 / D1b=2.8 / D1c=4.5 / D1d=6.0  （c_comp 固定 1.70）
   ssc：1.5s / 75 点 / dt20ms（与基线同口径）"""
import os
import shutil

BASE = r"C:/Users/dth15/Desktop/ANSYS"
SRC = BASE + "/automation/outbox/file_GOSWAP_INJ.dfs"
DLL = BASE + "/v3_run_G05/damper_dual_slope.dll"
SSC_SRC = BASE + "/v3_run_G05/file.ssc"  # "5 250 0"

OLD = b"3.41000000e+00"
PTS = [
    ("D1a", "2.00000000e+00"),
    ("D1b", "2.80000000e+00"),
    ("D1c", "4.50000000e+00"),
    ("D1d", "6.00000000e+00"),
]

data = open(SRC, "rb").read()
n = data.count(OLD)
print("src:", SRC)
print("occurrences of old c_reb:", n)
assert n == 2, "unexpected occurrence count!"

ssc = open(SSC_SRC, "rb").read()
ssc_new = ssc.replace(b"5 250 0", b"1.5 75 0")
assert ssc_new != ssc, "ssc replace failed!"
if b"1.5 75 0" not in ssc_new:
    raise SystemExit("ssc target not written")

for name, val in PTS:
    d = BASE + "/v3_run_" + name
    os.makedirs(d, exist_ok=True)
    n_src = data.count(val.encode())          # 目标值在源里原本的个数
    new = data.replace(OLD, val.encode())
    cnt = new.count(val.encode())
    assert cnt == n_src + 2, "delta != +2 for " + name  # 恰好新增 2 处
    assert new.count(OLD) == 0, "old value remains in " + name
    open(d + "/file.dfs", "wb").write(new)
    shutil.copy(DLL, d + "/damper_dual_slope.dll")
    open(d + "/file.ssc", "wb").write(ssc_new)
    print("%s: c_reb=%s | new-count=%d (was %d) | old-count=0 | ssc 1.5/75 | OK" % (name, val, cnt, n_src))

print("ALL 4 CASES READY")
