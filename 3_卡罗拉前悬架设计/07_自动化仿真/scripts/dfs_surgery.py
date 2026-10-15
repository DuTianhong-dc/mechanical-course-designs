# -*- coding: utf-8 -*-
r"""dfs 手术 v2：用 v3 自家"活塞-筒身"成功样式构造"活塞↔顶胶_内层"平移副
  71 = v3 marker 55 复制（改 id/名字）           body 53（活塞侧）
  72 = v3 marker 56 复制（改 id/名字/body→56）    body 56（#70 顶胶_内层侧）
  TRAJOINT 行 = v3 #1661 行复制（改 id=2/名字/marker 引用 71 72）
"""
import re, sys, os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import inject_case as ic

V3 = r"C:\Users\dth15\Desktop\ANSYS\suspension_v3_Mech_Files\Transient\file.dfs"
OUT = r"C:\Users\dth15\Desktop\ANSYS\automation\outbox\file_V3REP.dfs"

def seg_lines(data, name):
    m = re.search(rb"! " + name + rb"[^\r\n]*\r\n", data)
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

v3 = open(V3, "rb").read()

# 1) 取 v3 的 55/56 和 #1661 TRAJOINT 行
mk = {}
for pos, line in seg_lines(v3, b"MARKER"):
    tk = line.split()
    if tk[0] in (b"55", b"56"):
        mk[tk[0].decode()] = line
tj1661 = None
for pos, line in seg_lines(v3, b"TRAJOINT"):
    if b"#1661" in line:
        tj1661 = line
assert len(mk) == 2 and tj1661 is not None

NAME = b"//________________"

def retag(line, old_id, new_id, new_name):
    toks = line.split()
    assert toks[0] == old_id, toks[0]
    toks[0] = new_id
    toks[1] = new_name
    return b" " + b" ".join(toks)

# 2) 构造
mk71 = retag(mk["55"], b"55", b"71", NAME + b"/ActionMarker")
mk72 = retag(mk["56"], b"56", b"72", NAME + b"/BaseMarker")
# 72 的 body：52 -> 56
toks = mk72.split()
assert toks[2] == b"3" and toks[3] == b"52", toks[2:4]
toks[3] = b"56"
mk72 = b" " + b" ".join(toks)

tjt = tj1661.split()
assert tjt[0] == b"1", tjt[0]
tjt[0] = b"2"
tjt[1] = NAME
assert tjt[2] == b"55" and tjt[3] == b"56", tjt[2:4]
tjt[2] = b"71"; tjt[3] = b"72"
tj2 = b" " + b" ".join(tjt)

print("mk71:", mk71[:95])
print("mk72:", mk72[:95])
print("tj2 :", tj2[:95])

# 3) 插入
def insert_after_last(data, name, ins):
    rows = seg_lines(data, name)
    pos, line = rows[-1]
    at = pos + len(line) + 2
    return data[:at] + ins + b"\r\n" + data[at:]

data = v3
data = insert_after_last(data, b"MARKER", mk71 + b"\r\n" + mk72)
data = insert_after_last(data, b"TRAJOINT", tj2)

# 4) 头部重算
report = []
data, _ = ic.recount(data, fix=True, report=report)
for r in report[-8:]:
    print(r)

open(OUT, "wb").write(data)
print("saved:", OUT, "delta=%d" % (len(data) - len(v3)))
