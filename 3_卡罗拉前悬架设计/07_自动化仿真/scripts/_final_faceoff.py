# -*- coding: utf-8 -*-
r"""终局对照：同角色关节的 marker 全字段（弹簧/轴承REV/压接等）+ T-SPRING 行
   注：meshtest/v3 中大量 RBODY 帧=单位阵，此时 marker 字段==全局帧，可直接对拍"""
import re, io

FILES = {
    "MESHTEST": (r"C:\Users\dth15\Desktop\ANSYS\suspension_api_v2_meshtest_Mech_Files\Transient\file.dfs",
                 ["75", "76", "61", "62", "63", "64", "55", "56", "57", "58", "13", "14", "77", "78"]),
    "V3R1":     (r"C:\Users\dth15\Desktop\ANSYS\v3_run_R1\file.dfs",
                 ["67", "68", "57", "58", "59", "60", "51", "52", "53", "54", "9", "10", "69", "70",
                  "55", "56", "71", "72"]),
}
OUT = r"C:\Users\dth15\Desktop\ANSYS\automation\logs\final_faceoff.txt"

def seg(data, name):
    m = re.search(rb"\r\n! " + name + rb"[^\r\n]*?!!!\r\n", data)
    if not m:
        return []
    j = m.end()
    rows = []
    while j < len(data):
        k = data.find(b"\r\n", j)
        line = data[j:k]
        if line.lstrip().startswith(b"!"):
            break
        if line.strip():
            rows.append(line)
        j = k + 2
    return rows

w = io.open(OUT, "w", encoding="utf-8")
for tag, (path, targets) in FILES.items():
    data = open(path, "rb").read()
    w.write("\n######################## %s\n" % tag)
    for line in seg(data, b"MARKER"):
        tk = line.split()
        if tk and tk[0].decode() in targets:
            w.write("  %s\n" % line.decode("latin-1"))
    for line in seg(data, b"T-SPRING DAMPER"):
        w.write("[TSPRING] %s\n" % line.decode("latin-1"))
    for line in seg(data, b"REVJOINT"):
        w.write("[REV] %s\n" % line.decode("latin-1")[:200])
w.close()
print("done ->", OUT)
