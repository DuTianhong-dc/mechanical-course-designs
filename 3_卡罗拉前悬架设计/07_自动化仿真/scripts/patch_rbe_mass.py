# -*- coding: utf-8 -*-
r"""rbe 质量回填补丁（v2→v3 保真度修复）
   源：meshtest 修复版 rbody [活塞1, 耳板#88 2, 球头#133 3, 球头#136 4, 482kg 62]
   → 目标：v3 rbody [53(活塞#1661), 9(#88/1450), 11(#133/1458), 13(#136/1466), 66(482kg)]
   方法：RBODY 段目标行就地替换 [flag, m, Ixx, Iyy, Izz, Ixy, Ixz, Iyz] 8 字段（段行数不变，无需头部重算）"""
import re, sys

SRC = r"C:\Users\dth15\Desktop\ANSYS\suspension_api_v2_meshtest_Mech_Files\Transient\file.dfs"
DFS = sys.argv[1] if len(sys.argv) > 1 else r"C:\Users\dth15\Desktop\ANSYS\v3_run_R1\file.dfs"
OUT = sys.argv[2] if len(sys.argv) > 2 else r"C:\Users\dth15\Desktop\ANSYS\automation\outbox\file_V3FIXED.dfs"
PAIR = {"53": "1", "9": "2", "11": "3", "13": "4", "66": "62"}

def seg(data, name):
    m = re.search(rb"\r\n! " + name + rb"[^\r\n]*?!!!\r\n", data)
    if not m:
        raise SystemExit("no seg " + name)
    j = m.end()
    rows = []
    while j < len(data):
        k = data.find(b"\r\n", j)
        line = data[j:k]
        if line.lstrip().startswith(b"!"):
            break
        if line.strip():
            rows.append((j, line))
        j = k + 2
    return rows

src = open(SRC, "rb").read()
dst = open(DFS, "rb").read()

srcf = {}
for pos, line in seg(src, b"RBODY"):
    tk = line.split()
    if tk and tk[0].decode() in PAIR.values():
        srcf[tk[0].decode()] = tk[2:10]

replaces = []
for pos, line in seg(dst, b"RBODY"):
    tk = line.split()
    if tk and tk[0].decode() in PAIR:
        old8, new8 = tk[2:10], srcf[PAIR[tk[0].decode()]]
        assert len(new8) == 8
        newline = b" " + b" ".join(tk[0:2] + new8 + tk[10:])
        replaces.append((pos, line, newline, tk[0].decode()))
        print("rbe %-3s: flag %s->%s  mass %s->%s" % (tk[0].decode(), old8[0].decode(), new8[0].decode(), old8[1].decode(), new8[1].decode()))

assert len(replaces) == len(PAIR), len(replaces)

newdst = dst
for pos, old, new, rid in sorted(replaces, key=lambda x: -x[0]):
    assert newdst[pos:pos + len(old)] == old
    newdst = newdst[:pos] + new + newdst[pos + len(old):]

open(OUT, "wb").write(newdst)
print("saved:", OUT, "delta=%d" % (len(newdst) - len(dst)))

v = open(OUT, "rb").read()
for pos, line in seg(v, b"RBODY"):
    tk = line.split()
    if tk and tk[0].decode() in PAIR:
        print("verify rbe %-3s: %s" % (tk[0].decode(), b" ".join(tk[2:10]).decode()))
