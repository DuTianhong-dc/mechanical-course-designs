# -*- coding: utf-8 -*-
r"""inject_case.py —— DAFUL dfs 工况注入器（驱动 + 双斜率阻尼），通用版
================================================================================
在 Mechanical 导出的干净 dfs 上注入 v2 工况（轮跳驱动 + damper dll 阻尼），
并按「头部数字表」自动校验/重算头部计数。

用法：
  python inject_case.py <src.dfs> <out.dfs>                    # 注入 + 头部重算
  python inject_case.py <src.dfs> <out.dfs> --workdir DIR --ssc "1 100 0"
                                                               # 另建可跑目录（dfg/dfm/dfr/ssc/dll）
  python inject_case.py <src.dfs> --check                      # 只校验（打印对照表，不写文件）

头部数字表（已实证，计数 = 段实际行数，不加 1）：
  [09] 0 0 <NBODY> 0 <FBODY> <RBODY> <MARKER> 0
  [10] <表达式数(def行)> <USER数>
  [12] <SPLINE数> ...
  [13] <FIX REV TRA SCR CYL UNI COV PLA BAL ORI PAR INL PER INP DIS P2CAM C2CAM P2SURF MOTION> ... <NTR> 0 <NTN> ...
  [14] <FBODY> ... <PFSOLID> ... <FSOLID10> 0 <FSOLID15> <FSOLID20>
  [15] <T-SPRING R-SPRING BUSH MATRIX BEAMGROUP>  <T-SCALAR R-SCALAR VECTOR>  ...

注意事项：
  - 所有行匹配必须限定在段内（RBODY 段同样含 ` NN //` 行，跨段搜索会误匹配）
  - 文件为 CRLF；行内空白版式在修改时原样保留
  - 产出报告：<out>_report.txt（识别结果 + 头部对照表）

跑批（在 --workdir 目录内）：
  PATH 追加 C:\Program Files\ANSYS Inc\v242\tp\IntelMKL\2023.1.0\winx64
       和 C:\Program Files\ANSYS Inc\v242\commonfiles\CPython\3_10\winx64\Release\python
  rundfs.exe -i file -o resX -t 4
"""
import re
import sys
import os
import shutil
import argparse

# ============================ 配置（按 v2 工况实测值） ============================
DRIVE_EXPR = b"40*SIN(2*PI*TIME)"                       # 轮跳驱动公式
DRIVE_EXPR_NAME = b"Function_Expression"                # 表达式对象名（v2 口径）
DAMPER_DLL = b"damper_dual_slope.dll"                   # 阻尼 dll 文件名
DAMPER_FUNC = b"damper_dual_slope"                      # dll 内函数名
DAMPER_PARAMS = b"5.90000000e+01 3.41000000e+00 1.70000000e+00"   # 双斜率参数（59 / 3.41 / 1.7）
SPLINE_DATA = (b"0 7 "
               b"-1.50000000e+03 -5.20000000e+02 -2.00000000e+02 0.00000000e+00 "
               b"2.00000000e+02 5.20000000e+02 1.50000000e+03 "
               b"-2.55600000e+03 -8.86000000e+02 -3.41000000e+02 0.00000000e+00 "
               b"6.82000000e+02 1.77300000e+03 5.11500000e+03")
DAMPER_TRA_INDEX = 1          # 阻尼载体的平移副序号（v2 #787 与 v3 #1661 均为 TRAJOINT[1]）
SCALAR_SUFFIX = b"#982"       # T-SCALAR / 克隆 marker 的名字后缀（沿用 v2 命名）
DLL_FALLBACK_DIR = r"C:\Program Files\ANSYS Inc\v242\Motion\Solver\Console"

# 头部数字表：[头部行相对序号][token 位] = 段名（b"@EXPR" 为表达式特例，数 def 行）
COUNTERS = [
    ("[09]", 0, 2, b"NBODY"), ("[09]", 0, 4, b"FBODY"),
    ("[09]", 0, 5, b"RBODY"), ("[09]", 0, 6, b"MARKER"),
    ("[10]", 1, 0, b"@EXPR"), ("[10]", 1, 1, b"USER"),
    ("[12]", 3, 0, b"SPLINE"),
    ("[13]", 4, 0, b"FIXJOINT"), ("[13]", 4, 1, b"REVJOINT"), ("[13]", 4, 2, b"TRAJOINT"),
    ("[13]", 4, 3, b"SCRJOINT"), ("[13]", 4, 4, b"CYLJOINT"), ("[13]", 4, 5, b"UNIJOINT"),
    ("[13]", 4, 6, b"COVJOINT"), ("[13]", 4, 7, b"PLAJOINT"), ("[13]", 4, 8, b"BALJOINT"),
    ("[13]", 4, 9, b"ORIJOINT"), ("[13]", 4, 10, b"PARJOINT"), ("[13]", 4, 11, b"INLJOINT"),
    ("[13]", 4, 12, b"PERJOINT"), ("[13]", 4, 13, b"INPJOINT"), ("[13]", 4, 14, b"DISJOINT"),
    ("[13]", 4, 15, b"POINT-TO-CAM"), ("[13]", 4, 16, b"CURVE-TO-CAM"),
    ("[13]", 4, 17, b"POINT-TO-SURFACE"), ("[13]", 4, 18, b"MOTION"),
    ("[13]", 4, 21, b"NODE-TO-RIGID CST"), ("[13]", 4, 23, b"NODE-TO-NODE CST"),
    ("[14]", 5, 0, b"FBODY"), ("[14]", 5, 12, b"PFSOLID"), ("[14]", 5, 22, b"FSOLID10"),
    ("[14]", 5, 24, b"FSOLID15"), ("[14]", 5, 25, b"FSOLID20"),
    ("[15]", 6, 0, b"T-SPRING DAMPER"), ("[15]", 6, 1, b"R-SPRING DAMPER"),
    ("[15]", 6, 2, b"BUSH"), ("[15]", 6, 3, b"MATRIX"), ("[15]", 6, 4, b"BEAMGROUP"),
    ("[15]", 6, 5, b"T-SCALAR"), ("[15]", 6, 6, b"R-SCALAR"), ("[15]", 6, 7, b"VECTOR"),
]

SEG_MARK = re.compile(rb"! +([A-Z0-9\-\. ]+?) +!+")


# ============================ 基础工具 ============================
def token_spans(line):
    spans = []
    i = 0
    n = len(line)
    while i < n:
        if line[i:i + 1] == b" ":
            i += 1
            continue
        j = i
        while j < n and line[j:j + 1] != b" ":
            j += 1
        spans.append((i, j))
        i = j
    return spans


def set_tok(line, idx, newv):
    spans = token_spans(line)
    a, b = spans[idx]
    return line[:a] + newv + line[b:]


def build_sections(data):
    marks = [(m.start(), m.end(), m.group(1).strip()) for m in SEG_MARK.finditer(data)]
    secs = {}
    for k, (s, e, name) in enumerate(marks):
        bs = data.find(b"\r\n", e)
        bs = (bs + 2) if bs >= 0 else e
        be = marks[k + 1][0] if k + 1 < len(marks) else len(data)
        secs.setdefault(name, []).append((bs, be))
    return marks, secs


def get_sec(secs, name):
    lst = secs.get(name)
    if not lst:
        return None
    assert len(lst) == 1, "section %r not unique" % name
    return lst[0]


def seg_lines_pos(data, sec):
    bs, be = sec
    out = []
    pos = bs
    while pos < be:
        k = data.find(b"\r\n", pos)
        if k < 0 or k > be:
            k = be
        line = data[pos:k]
        if line.strip() and not line.lstrip().startswith(b"#"):
            out.append((pos, line))
        pos = k + 2
    return out


def seg_count(data, secs, name):
    sec = get_sec(secs, name)
    if sec is None:
        return 0
    return len(seg_lines_pos(data, sec))


def count_expr(data, secs):
    sec = get_sec(secs, b"EXPRESSION")
    if sec is None:
        return 0
    bs, be = sec
    return len(re.findall(rb"def DfFunction_\d+\(", data[bs:be]))


def insert_in_seg(data, sec, ins):
    """在段 [bs,be) 的最后一个数据行之后插入 ins（ins 自带 CRLF）；
    段内无数据行（全为空/注释）时插在段首。"""
    bs, be = sec
    lines = seg_lines_pos(data, sec)
    if not lines:
        at = bs
    else:
        pos, line = lines[-1]
        k = data.find(b"\r\n", pos + len(line))
        at = (k + 2) if k >= 0 else (pos + len(line))
    return data[:at] + ins + data[at:]


def head_rows(data):
    m = re.search(rb"# SYSTEM CONFIGURATION #+\r\n", data)
    assert m, "no SYSTEM CONFIGURATION"
    pos = m.end()
    rows = []
    for _ in range(10):
        k = data.find(b"\r\n", pos)
        assert k > 0, "header too short"
        rows.append((pos, k, data[pos:k]))
        pos = k + 2
    return rows


def apply_edits(data, edits):
    """edits = [(abs_start, abs_end, new_bytes)]，从后往前应用"""
    for s, e, nb in sorted(edits, key=lambda t: t[0], reverse=True):
        data = data[:s] + nb + data[e:]
    return data


def name_prefix_from_expr(data, secs):
    """从 0 号表达式名提取名字前缀（v2='/ANSYS/'，v3='//'）"""
    sec = get_sec(secs, b"EXPRESSION")
    for pos, line in seg_lines_pos(data, sec):
        tk = line.split()
        if len(tk) >= 2 and tk[1].startswith(b"/"):
            m = re.match(rb"^(//|/ANSYS/)", tk[1])
            if m:
                return m.group(1)
    return b"//"


def with_scalar_suffix(name, suf=SCALAR_SUFFIX):
    """//_________#1661/ActionMarker -> //_________#1661#982/ActionMarker"""
    m = re.match(rb"^(.*#\d+)(/.*)$", name)
    if m:
        return m.group(1) + suf + m.group(2)
    return name + suf


def base_scalar_name(marker_name, suf=SCALAR_SUFFIX):
    """//_________#1661/ActionMarker -> //_________#1661#982"""
    n = with_scalar_suffix(marker_name, suf)
    k = n.rfind(b"/")
    return n[:k] if k > 0 else n


# ============================ 关节识别 ============================
def read_marker_table(data, secs):
    mk = {}
    sec = get_sec(secs, b"MARKER")
    for pos, line in seg_lines_pos(data, sec):
        tk = line.split()
        try:
            mk[int(tk[0])] = tk
        except ValueError:
            pass
    return mk


def read_trajoints(data, secs, mk):
    """返回 TRAJOINT 列表：dict(idx, name, mA, mB, bodyA, bodyB, grounded, line)"""
    out = []
    sec = get_sec(secs, b"TRAJOINT")
    if sec is None:
        return out
    for pos, line in seg_lines_pos(data, sec):
        tk = line.split()
        idx = int(tk[0])
        mA, mB = int(tk[2]), int(tk[3])
        bodyA = int(mk[mA][3]) if mA in mk else -1
        bodyB = int(mk[mB][3]) if mB in mk else -1
        out.append(dict(idx=idx, name=tk[1], mA=mA, mB=mB,
                        bodyA=bodyA, bodyB=bodyB,
                        grounded=(bodyA == 0 or bodyB == 0), line=line))
    return out


# ============================ 注入 ============================
def inject_drive(data, report):
    """驱动：表达式 + MOTION 行（每次插入后重扫段偏移）"""
    _, secs = build_sections(data)
    prefix = name_prefix_from_expr(data, secs)
    n_expr = count_expr(data, secs)
    expr_block = (b" %d " % n_expr + prefix + DRIVE_EXPR_NAME + b" 0\r\n"
                  b"def DfFunction_%d(TIME):\\n\\treturn " % n_expr + DRIVE_EXPR + b"\r\n"
                  b" DfFunction_%d 0\r\n" % n_expr)
    data = insert_in_seg(data, get_sec(secs, b"EXPRESSION"), expr_block)
    report.append("EXPRESSION: +1 (DfFunction_%d, %s)" % (n_expr, DRIVE_EXPR.decode()))

    _, secs = build_sections(data)
    mk = read_marker_table(data, secs)
    tra = read_trajoints(data, secs, mk)
    drives = [t for t in tra if t["grounded"]]
    assert drives, "no grounded translational joint found"
    drive = drives[0]
    motion_line = (b" 0 " + drive["name"] + b"/DriverFunction"
                   b" 0 1 0 3 0 0 1 0 0.00000000e+00 0.00000000e+00\r\n")
    data = insert_in_seg(data, get_sec(secs, b"MOTION"), motion_line)
    report.append("MOTION: %s/DriverFunction (TRAJOINT[%d], markers %d/%d)"
                  % (drive["name"].decode("ascii", "replace"), drive["idx"], drive["mA"], drive["mB"]))
    return data


def inject_damper(data, report):
    """阻尼：USER + SPLINE + markers 克隆 + T-SCALAR（每次插入后重扫段偏移）"""
    _, secs = build_sections(data)
    prefix = name_prefix_from_expr(data, secs)

    # USER 行
    user_line = (b" 0 " + prefix + b"User_Subroutine 0 0 1 " + DAMPER_DLL + b" "
                 + DAMPER_FUNC + b" 3 " + DAMPER_PARAMS + b"\r\n")
    data = insert_in_seg(data, get_sec(secs, b"USER"), user_line)
    report.append("USER: %s (%s)" % (DAMPER_DLL.decode(), user_line.split()[5].decode()))

    # SPLINE 行
    _, secs = build_sections(data)
    spline_line = b" 0 " + prefix + b"Spline " + SPLINE_DATA + b"\r\n"
    data = insert_in_seg(data, get_sec(secs, b"SPLINE"), spline_line)
    report.append("SPLINE: 7 点数据")

    # 定位阻尼关节
    _, secs = build_sections(data)
    mk = read_marker_table(data, secs)
    tra = read_trajoints(data, secs, mk)
    assert len(tra) > DAMPER_TRA_INDEX, "TRAJOINT[%d] not found" % DAMPER_TRA_INDEX
    damper = tra[DAMPER_TRA_INDEX]
    assert not damper["grounded"], "damper joint must be BodyToBody"
    report.append("DAMPER JOINT: TRAJOINT[%d] %s (markers %d/%d, bodies %d/%d)"
                  % (damper["idx"], damper["name"].decode("ascii", "replace"),
                     damper["mA"], damper["mB"], damper["bodyA"], damper["bodyB"]))

    # 克隆 markers（新 id = max+1 / +2）
    newA = max(mk.keys()) + 1
    newB = newA + 1

    def clone_marker(src_id, new_id):
        tk = list(mk[src_id])
        tk[0] = b"%d" % new_id
        tk[1] = with_scalar_suffix(tk[1])
        if tk[-1] == b"2":
            tk[-1] = b"1"
        return b" " + b" ".join(tk) + b"\r\n"

    clone_block = clone_marker(damper["mA"], newA) + clone_marker(damper["mB"], newB)
    data = insert_in_seg(data, get_sec(secs, b"MARKER"), clone_block)
    report.append("MARKER: clone %d->%d, %d->%d" % (damper["mA"], newA, damper["mB"], newB))

    # T-SCALAR 行
    _, secs = build_sections(data)
    ts_name = base_scalar_name(mk[damper["mA"]][1])
    ts_line = b" 0 " + ts_name + b" %d %d 0 0 1 0\r\n" % (newA, newB)
    data = insert_in_seg(data, get_sec(secs, b"T-SCALAR"), ts_line)
    report.append("T-SCALAR: %s (%d %d)" % (ts_name.decode("ascii", "replace"), newA, newB))
    return data


# ============================ 头部校验 / 重算 ============================
def recount(data, fix, report):
    """按头部数字表校验（fix=True 时把不符的计数改成实测段行数）"""
    _, secs = build_sections(data)
    rows = head_rows(data)
    row_mods = {}          # 行级聚合：head_idx -> [(token_idx, new_val)]
    n_ok = 0
    for label, hi, ti, sname in COUNTERS:
        row_pos, row_end, row = rows[hi]
        tk = row.split()
        cur = tk[ti]
        want = count_expr(data, secs) if sname == b"@EXPR" else seg_count(data, secs, sname)
        want_b = b"%d" % want
        if cur == want_b:
            n_ok += 1
            report.append("%-5s [%2d] %-22s = %-8s OK" % (label, ti, sname.decode(), cur.decode()))
        else:
            act = "FIXED" if fix else "MISMATCH"
            if fix:
                row_mods.setdefault(hi, []).append((ti, want_b))
            report.append("%-5s [%2d] %-22s = %-8s %s (实测 %d)"
                          % (label, ti, sname.decode(), cur.decode(), act, want))
    edits = []
    for hi, mods in row_mods.items():
        row_pos, row_end, row = rows[hi]
        for ti, v in mods:
            row = set_tok(row, ti, v)
        edits.append((row_pos, row_end, row))
    if edits:
        data = apply_edits(data, edits)
    n_fix = sum(len(m) for m in row_mods.values())
    report.append("头部校验：OK %d 项，修正 %d 项" % (n_ok, n_fix))
    return data, (n_ok, n_fix)


# ============================ 主流程 ============================
def run(src, out, workdir=None, ssc=None, check_only=False):
    data = open(src, "rb").read()
    report = []
    report.append("== inject_case.py ==")
    report.append("SRC: %s (%d bytes)" % (src, len(data)))

    if check_only:
        _, n_fix = recount(data, fix=False, report=report)
        txt = "\n".join(report)
        print(txt)
        return

    # 注入（每次插入后函数内部重扫段偏移）
    data = inject_drive(data, report)
    data = inject_damper(data, report)

    # 头部重算
    data, _ = recount(data, fix=True, report=report)

    open(out, "wb").write(data)
    report.append("OUT: %s (%d bytes)" % (out, len(data)))

    # 可选：运行目录
    if workdir:
        os.makedirs(workdir, exist_ok=True)
        sd = os.path.dirname(os.path.abspath(src))
        for f in ("file.dfg", "file.dfm", "file.dfr"):
            p = os.path.join(sd, f)
            if os.path.exists(p):
                shutil.copy2(p, os.path.join(workdir, f))
        if ssc:
            io = open(os.path.join(workdir, "file.ssc"), "w", newline="")
            io.write("#DAFUL SOLVER SIMULATION SCENARIO#\r\n"
                     "4 0\r\n#SIMULATION SCENARIO\r\n"
                     "#SIMULATION 1\r\nPOSITION\r\n1\r\n0\r\n"
                     "#SIMULATION 2\r\nVELOCITY\r\n1\r\n0\r\n"
                     "#SIMULATION 3\r\nACCELERATION\r\n1\r\n0\r\n"
                     "#SIMULATION 4\r\nDYNAMICS\r\n" + ssc + "\r\n0\r\n"
                     "#SIMULATION CONDITION\r\n#INITIAL CONDITION\r\n#IMPORT ICF\r\n0\r\n"
                     "#EXPORT ICF\r\n0\r\n#END OF DAFUL SOLVER SIMULATION SCENARIO#\r\n")
            io.close()
            report.append("SSC: %s" % ssc)
        dll_src = os.path.join(sd, DAMPER_DLL.decode())
        if os.path.exists(dll_src):
            shutil.copy2(dll_src, os.path.join(workdir, DAMPER_DLL.decode()))
        elif os.path.exists(os.path.join(DLL_FALLBACK_DIR, DAMPER_DLL.decode())):
            shutil.copy2(os.path.join(DLL_FALLBACK_DIR, DAMPER_DLL.decode()),
                         os.path.join(workdir, DAMPER_DLL.decode()))
        shutil.copy2(out, os.path.join(workdir, "file.dfs"))
        report.append("WORKDIR: %s (dfg/dfm/dfr/ssc/dll/file.dfs 就位)" % workdir)

    txt = "\n".join(report)
    print(txt)
    rep_path = out + "_report.txt"
    with open(rep_path, "w", encoding="utf-8") as f:
        f.write(txt + "\n")
    print("\nreport -> %s" % rep_path)


def main():
    ap = argparse.ArgumentParser(description="DAFUL dfs 工况注入器")
    ap.add_argument("src", help="源 dfs（Mechanical 导出的干净文件）")
    ap.add_argument("out", nargs="?", help="输出 dfs")
    ap.add_argument("--workdir", help="另建可跑目录")
    ap.add_argument("--ssc", help='动力学设置，如 "1 100 0"（结束时间s/输出步数/起始时间s）')
    ap.add_argument("--check", action="store_true", help="只校验头部数字表")
    a = ap.parse_args()
    if not a.check and not a.out:
        ap.error("需要 out 参数（或 --check）")
    run(a.src, a.out, a.workdir, a.ssc, a.check)


if __name__ == "__main__":
    main()
