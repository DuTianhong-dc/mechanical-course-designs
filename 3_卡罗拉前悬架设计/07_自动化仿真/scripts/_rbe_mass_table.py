# -*- coding: utf-8 -*-
r"""RBODY 质量/惯性/位置 全表对拍（按"角色名"配对：去掉 /RBE号码 后缀）"""
import re, io
from collections import defaultdict

FILES = {
    "MESHTEST": r"C:\Users\dth15\Desktop\ANSYS\suspension_api_v2_meshtest_Mech_Files\Transient\file.dfs",
    "V3R1":     r"C:\Users\dth15\Desktop\ANSYS\v3_run_R1\file.dfs",
}
OUT = r"C:\Users\dth15\Desktop\ANSYS\automation\logs\rbe_mass_table.txt"

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

def role_of(name):
    # 去掉 /RBE12345_X 或 /RBE12345 后缀
    r = re.sub(rb"/RBE\d+(_[RM])?$", b"", name)
    return r.replace(b"/", b"").decode("latin-1").strip("_")

tables = {}
for tag, path in FILES.items():
    data = open(path, "rb").read()
    t = defaultdict(list)
    for line in seg(data, b"RBODY"):
        tk = line.split()
        if not tk or not tk[0].isdigit():
            continue
        nm = next((x for x in tk if x.startswith(b"//")), b"")
        nums = [float(x) for x in tk[2:] if re.match(rb"^-?[\d.]+(e[+-]\d+)?$", x)]
        if len(nums) >= 11:
            rec = {"id": tk[0].decode(), "name": nm.decode("latin-1"),
                   "flag": nums[0], "m": nums[1], "I": nums[2:8],
                   "pos": nums[8:11]}
        else:
            rec = {"id": tk[0].decode(), "name": nm.decode("latin-1"), "raw": True}
        t[role_of(nm)].append(rec)
    tables[tag] = t

w = io.open(OUT, "w", encoding="utf-8")
roles = sorted(set(list(tables["MESHTEST"].keys()) + list(tables["V3R1"].keys())))
for role in roles:
    a = sorted(tables["MESHTEST"].get(role, []), key=lambda r: r.get("pos", [9e9, 0, 0])[:1] if not r.get("raw") else [9e9])
    b = sorted(tables["V3R1"].get(role, []), key=lambda r: r.get("pos", [9e9, 0, 0])[:1] if not r.get("raw") else [9e9])
    n = max(len(a), len(b))
    for i in range(n):
        ra = a[i] if i < len(a) else None
        rb = b[i] if i < len(b) else None
        def fmt(r):
            if r is None:
                return "(缺)"
            if r.get("raw"):
                return "raw"
            return "id%-3s f%s m=%.4g I=(%.4g,%.4g,%.4g) pos=(%.2f,%.2f,%.2f)" % (
                r["id"], int(r["flag"]), r["m"], r["I"][0], r["I"][1], r["I"][2],
                r["pos"][0], r["pos"][1], r["pos"][2])
        flag = " <<<" if ((ra is None) != (rb is None)) else ""
        if ra and rb and not ra.get("raw") and not rb.get("raw"):
            dmass = abs(ra["m"] - rb["m"]) > 1e-6
            dinertia = max(abs(ra["I"][j] - rb["I"][j]) for j in range(6)) > 1e-6
            if dmass or dinertia or int(ra["flag"]) != int(rb["flag"]):
                flag = " ***"
        w.write("%-28s | %s | %s%s\n" % (role[:28], fmt(ra), fmt(rb), flag))
w.close()
print("done ->", OUT)
