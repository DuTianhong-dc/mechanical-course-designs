# -*- coding: utf-8 -*-
"""
params.py —— 参数加载与公式求值器（通用，适用于所有零件）

功能：
  ① 读取 TOML 参数文件；独立参数直接生效
  ② 派生参数（"= 表达式"字符串）按依赖顺序自动求值
  ③ 【继承】自动加载同目录的两个【共享表】，零件可直接引用其中的名字：
       - 00_全局.toml   →  材料 / 整车工况 / 设计规范
       - 90_标准件.toml →  查国标表得到的紧固件尺寸（螺母厚、垫片厚…）
       直接写名字：  "= 满载单轴荷 * 1.4"   ／  "= 顶胶高 + M14螺母厚"
       或加前缀：    "= 全局.满载单轴荷"      （避免同名歧义时用）
     零件自己的定义永远覆盖共享表
  ④ 【校验】["_校验"] 区的布尔表达式：求值为 False 时报错
  ⑤ 表达式可用 math 全部函数（math.pi / math.hypot… 或裸名 pi / hypot）

用法：
  from params import load
  P = load("10_螺旋弹簧.toml")          # 自动继承同目录 00_全局.toml
  P = load("20_下摆臂.toml", auto_global=False)   # 关闭继承
  P["几何"]["自由高"]      # → 330.0
  P.flat()                 # 扁平字典（含全部求值结果）
  P.report()               # 打印

命令行：python params.py <文件.toml> [--json out.json]
"""
import json
import math
import os
import sys
import tomllib

GLOBAL_NAME = "00_全局.toml"
SHARED_NAME = "90_标准件.toml"      # 跨零件共享的标准件（查国标表得到的值），同样自动注入
CHECK_SECTION = "_校验"


class _NS(dict):
    """支持点号访问的命名空间：全局.弹簧钢"""

    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError:
            raise NameError(f"全局参数中不存在：{name}") from None


class Params(dict):
    """加载后的参数集：保留分区结构，支持扁平访问与打印"""

    def __init__(self, sections, order):
        super().__init__(sections)
        self._order = order

    def flat(self):
        out = {}
        for sec, kv in self.items():
            if isinstance(kv, dict):
                out.update(kv)
        return out

    def report(self):
        for sec, kv in self.items():
            if isinstance(kv, dict):
                print(f"── [{sec}] ──")
                for k, v in kv.items():
                    print(f"  {k} = {v:.6g}" if isinstance(v, float) else f"  {k} = {v}")

    def check(self):
        """执行 _校验 区的布尔规则；返回失败项列表"""
        rules = self.get(CHECK_SECTION, {})
        failed = []
        for name, passed in rules.items():
            if not passed:
                failed.append(name)
        return failed


def _find_bases(path):
    """在参数文件同目录查找可继承的共享参数文件（按注入顺序返回）：
    00_全局.toml（材料/工况/规范）→ 90_标准件.toml（螺母、垫片等查表值）
    后注入的覆盖先注入的；零件自己的定义永远覆盖这两者。"""
    d = os.path.dirname(os.path.abspath(path))
    me = os.path.abspath(path)
    out = []
    for name in (GLOBAL_NAME, SHARED_NAME):
        p = os.path.join(d, name)
        if os.path.exists(p) and os.path.abspath(p) != me:
            out.append(p)
    return out


def _find_global(path):
    """（兼容旧调用）只找 00_全局.toml"""
    d = os.path.dirname(os.path.abspath(path))
    p = os.path.join(d, GLOBAL_NAME)
    return p if os.path.exists(p) else None


def _eval_file(path, extra_ns=None):
    """加载并求值单个 TOML（不含继承逻辑）。
    extra_ns：额外的初始命名空间（用于把全局参数注入零件求值）"""
    with open(path, "rb") as f:
        raw = tomllib.load(f)

    pending = {}
    sections = {sec: {} for sec in raw}
    for sec, kv in raw.items():
        for k, v in kv.items():
            pending[k] = (sec, v)

    ns = {"__builtins__": {}}
    ns["math"] = math
    for n in dir(math):
        if not n.startswith("_"):
            ns[n] = getattr(math, n)
    # 兼容 SW 方程式写法：SW 的三角函数一律用【度】（Python 的 math 用弧度），强制覆盖对齐语义
    #   ★ 四个反三角全部返回【度】：atn / atan / asin / acos
    #     （原来只覆盖了 atn/asin/acos，漏了 atan，导致"写 atan 拿到弧度"这种隐蔽单位错）
    #   ★ 想要弧度就显式写 math.atan(x) —— 带 math. 前缀的永远是 Python 原生语义
    ns["atn"] = lambda x: math.degrees(math.atan(x))
    ns["atan"] = lambda x: math.degrees(math.atan(x))
    ns["asin"] = lambda x: math.degrees(math.asin(x))
    ns["acos"] = lambda x: math.degrees(math.acos(x))
    ns["sin"] = lambda x: math.sin(math.radians(x))
    ns["cos"] = lambda x: math.cos(math.radians(x))
    ns["tan"] = lambda x: math.tan(math.radians(x))
    if extra_ns:
        ns.update(extra_ns)

    unresolved = dict(pending)
    for _ in range(50):
        progress = False
        for key in list(unresolved.keys()):
            sec, val = unresolved[key]
            if isinstance(val, str) and val.startswith("="):
                try:
                    result = eval(val[1:], dict(ns))
                except NameError:
                    continue                       # 依赖未就绪，下轮再试
                except Exception as exc:
                    raise ValueError(f"[{sec}] {key} 表达式求值失败：{val!r} ({exc})")
            else:
                result = val
            ns[key] = result
            sections[sec][key] = result
            del unresolved[key]
            progress = True
        if not progress:
            break
    if unresolved:
        bad = "、".join(unresolved.keys())
        raise ValueError(f"以下参数无法求值（循环依赖或缺少依赖）：{bad}")
    return raw, sections, ns


def load(path, base_path=None, auto_global=True, run_check=True):
    """加载参数文件（自动继承共享表）。
    base_path  ：显式指定基础文件（默认自动找同目录 00_全局.toml + 90_标准件.toml）
    auto_global：False 则不做继承
    run_check  ：求值后执行 _校验 规则，失败抛异常"""
    extra = None
    if auto_global:
        bases = [base_path] if base_path else _find_bases(path)
        merged = {}
        for bp in bases:
            if not bp or not os.path.exists(bp):
                continue
            if os.path.abspath(bp) == os.path.abspath(path):
                continue
            _, _, g_ns = _eval_file(bp)
            merged.update({k: v for k, v in g_ns.items() if k != "math"})
        if merged:
            extra = dict(merged)                # 平铺注入（直接名可用）
            extra["全局"] = _NS(merged)         # 点号访问（全局.xxx）

    raw, sections, ns = _eval_file(path, extra_ns=extra)
    P = Params(sections, list(raw.keys()))
    if run_check:
        failed = P.check()
        if failed:
            raise ValueError("参数校验未通过：" + "、".join(failed))
    return P


def load_spring(params_dir):
    """便捷入口：加载螺旋弹簧参数"""
    return load(os.path.join(params_dir, "10_螺旋弹簧.toml"))


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    p = sys.argv[1]
    P = load(p)
    print(f"═══ {os.path.basename(p)} 求解结果 ═══")
    P.report()
    failed = P.check()
    if CHECK_SECTION in P:
        print(f"\n校验规则：{len(P[CHECK_SECTION])} 条" + ("，全部通过 ✓" if not failed else f"，未通过：{failed}"))
    if "--json" in sys.argv:
        out = sys.argv[sys.argv.index("--json") + 1]
        with open(out, "w", encoding="utf-8") as f:
            json.dump(P.flat(), f, ensure_ascii=False, indent=2)
        print(f"JSON 已导出：{out}")
