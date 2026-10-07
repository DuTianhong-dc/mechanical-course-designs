# -*- coding: utf-8 -*-
"""
建材料.py —— 往 SolidWorks 自定义材质库写入材料（中文全称 + 分类正确的外观）

⚠️ 四条铁律（ 血泪教训：曾用 ElementTree 整树重写把库写坏，SW 直接打不开）
   ① 绝不用 XML 库整树重写 —— 会丢 XML 声明、重排命名空间 → SW 解析失败
   ② 只做【文本级】插入 / 替换 / 移动，保留原有声明头、命名空间、缩进、换行、编码
   ③ 写前先做一次 XML 校验解析，通过才落盘
   ④ 带时间戳备份，绝不覆盖旧备份

写入对象：两个 自定义材料.sldmat（2023 与 2026 各一份），两库都写。
★ 写完 SW 材质下拉要重启才刷新；但 **API 按名解析通常即时生效**。

命名与外观约定（ 用户定）：
  · 材料名一律用【中文全称】：10号优质碳素结构钢 / 25%玻纤增强聚甲醛（POM-GF25） …
  · 颜色按材料类别给（钢系深浅灰、塑料米白或黑、橡胶黑），不再一律 b2b2b2
  · 着色器与剖面线按类别选：钢用 matte steel + ANSI32；塑料/橡胶用塑料 shader + ANSI34
  · 分类：钢 → 「碳素结构钢」；塑料 → 「塑料」；橡胶 → 「橡胶」

用法：
   python 建材料.py              # 预览（只打印计划，不写文件）
   python 建材料.py --apply      # 真正写入
"""
import os
import re
import sys
import shutil
import datetime
import xml.etree.ElementTree as ET          # 仅用于"写前校验解析"，绝不用于写

LIBS = {
    "2023": r"C:\ProgramData\SolidWorks\SOLIDWORKS 2023\自定义材料\自定义材料.sldmat",
    "2026": r"C:\ProgramData\SolidWorks\SOLIDWORKS 2026\自定义材料\自定义材料.sldmat",
}

# ── 外观模板：照抄 SW 自带库里"能用"的结构，不凭空造 ──
#   (pwshader2 路径, pwshader2 名, cgshader2 名, 剖面线名)
TPL = {
    "钢": ("\\metal\\steel\\matte steel.p2m", "matte steel",
           "defaultplastic", "ANSI32 (钢)"),
    "铸铁": ("\\metal\\steel\\matte steel.p2m", "matte steel",
             "defaultplastic", "ANSI32 (钢)"),
    "塑料": ("\\plastic\\textured\\White-PW-MT11050.p2m", "White-PW-MT11050",
             "PlasticPolystyrene", "ANSI34 (Plastic Rubber)"),
    "橡胶": ("\\plastic\\textured\\White-PW-MT11050.p2m", "White-PW-MT11050",
             "PlasticPolystyrene", "ANSI34 (Plastic Rubber)"),
}
CLASS_OF_KIND = {"钢": "碳素结构钢", "铸铁": "铸铁", "塑料": "塑料", "橡胶": "橡胶"}

STAMP = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

# ════════════════════════════════════════════════════════════════
# 材料表：名字（中文全称）→ 类别 / 颜色 / 物性 / 说明
# ════════════════════════════════════════════════════════════════
MATERIALS = {
    # ── 钢（深浅灰，低碳浅、高强钢偏蓝灰）──
    "10号优质碳素结构钢": {
        "kind": "钢", "rgb": "b8b8b8",
        "note": "GB/T 699（正火）——球头总成壳体（冷挤压单壳）",
        "EX": "210000000000", "NUXY": "0.3", "GXY": "81000000000",
        "ALPX": "1.18E-05", "DENS": "7850", "KX": "58.6", "C": "461",
        "SIGXT": "335000000", "SIGYLD": "205000000",
    },
    "20号优质碳素结构钢": {
        "kind": "钢", "rgb": "b0b0b0",
        "note": "GB/T 699——衬套内外套 / 焊接衬管（可焊性好）",
        "EX": "206000000000", "NUXY": "0.3", "GXY": "79200000000",
        "ALPX": "1.15E-05", "DENS": "7850", "KX": "49.8", "C": "486",
        "SIGXT": "410000000", "SIGYLD": "245000000",
    },
    "45号优质碳素结构钢": {
        "kind": "钢", "rgb": "a6a6a6",
        "note": "GB/T 699（正火）——减振器壳筒体",
        "EX": "206000000000", "NUXY": "0.3", "GXY": "79200000000",
        "ALPX": "1.15E-05", "DENS": "7850", "KX": "49.8", "C": "486",
        "SIGXT": "600000000", "SIGYLD": "355000000",
    },
    "40Cr合金结构钢": {
        "kind": "钢", "rgb": "9a9aa6",
        "note": "GB/T 3077（调质 HB241~286）——球头销",
        "EX": "211000000000", "NUXY": "0.3", "GXY": "81200000000",
        "ALPX": "1.1E-05", "DENS": "7870", "KX": "45", "C": "460",
        "SIGXT": "980000000", "SIGYLD": "785000000",
    },
    "Q345B低合金高强度结构钢": {
        "kind": "钢", "rgb": "aeb6b6",
        "note": "GB/T 1591（t≤16mm，σs=345）——减振器壳板件",
        "EX": "206000000000", "NUXY": "0.3", "GXY": "79200000000",
        "ALPX": "1.2E-05", "DENS": "7850", "KX": "45", "C": "460",
        "SIGXT": "470000000", "SIGYLD": "345000000",
    },
    "QStE420热机械轧制高强钢": {
        "kind": "钢", "rgb": "9ea8b0",
        "note": "QStE420TM = EN 10149-2 S420MC（1.0980）——下摆臂本体（t=3）",
        "EX": "206000000000", "NUXY": "0.3", "GXY": "79200000000",
        "ALPX": "1.2E-05", "DENS": "7850", "KX": "45", "C": "460",
        "SIGXT": "480000000", "SIGYLD": "420000000",
    },
    "60Si2MnA弹簧钢": {
        "kind": "钢", "rgb": "8c94aa",
        "note": "GB/T 1222 弹簧钢——螺旋弹簧",
        "EX": "206000000000", "NUXY": "0.3", "GXY": "79200000000",
        "ALPX": "1.2E-05", "DENS": "7850", "KX": "32.6", "C": "460",
        "SIGXT": "1650000000", "SIGYLD": "1375000000",
    },
    # ── 铸铁 ──
    # 出处：GB/T 1348-2009《球墨铸铁件》力学性能表（多来源核对一致）
    #   剪切强度 405 MPa ｜ 扭转强度 405 ｜ 弹性模量 169 GPa ｜ 泊松比 0.275
    #   无缺口疲劳极限 210 ｜ 有缺口 128 ｜ 抗压强度 700 ｜ KIC 28 MPa·√m
    #   300℃ 热导率 36.2 W/(K·m) ｜ 比热 515 J/(kg·K) ｜ 线膨胀 12.5e-6 ｜ 密度 7.1
    #   抗拉强度 σb ≥ 450 MPa ｜ 屈服 σs ≥ 310 MPa ｜ 延伸率 ≥ 10% ｜ HB 160~210
    #   基体：铁素体（100%）
    # 注：齿圈铸铁 E 有 169/162 两说，取 GB/T 1348 表的 169 GPa
    "球墨铸铁（QT450-10）": {
        "kind": "铸铁", "rgb": "8e8e86",
        "note": "GB/T 1348-2009（铁素体基体）——转向节（一体铸造）",
        "EX": "169000000000", "NUXY": "0.275", "GXY": "66270000000",
        "ALPX": "1.25E-05", "DENS": "7100", "KX": "36.2", "C": "515",
        "SIGXT": "450000000", "SIGYLD": "310000000",
    },
    # ── 塑料 ──
    "聚甲醛（POM）": {
        "kind": "塑料", "rgb": "eae3cd",
        "note": "聚甲醛——球头塑料衬垫，自润滑耐磨",
        "EX": "2800000000", "NUXY": "0.35", "GXY": "1040000000",
        "ALPX": "1.1E-04", "DENS": "1410", "KX": "0.31", "C": "1500",
        "SIGXT": "65000000", "SIGYLD": "60000000",
    },
    "25%玻纤增强聚甲醛（POM-GF25）": {
        "kind": "塑料", "rgb": "404040",
        "note": ">POM-GF25，GB/T 22271——球头总成上下球座（内球面复合 PTFE）",
        "EX": "8000000000", "NUXY": "0.35", "GXY": "2963000000",
        "ALPX": "3.0E-05", "DENS": "1600", "KX": "0.31", "C": "1500",
        "SIGXT": "125000000", "SIGYLD": "125000000",
    },
    # ── 橡胶 / 弹性体 ──
    "天然橡胶（NR60）": {
        "kind": "橡胶", "rgb": "2e2e2e",
        "note": "NR，60±5 Shore A——悬架衬套弹性体（汽车 OEM 通用档）",
        "EX": "2698500", "NUXY": "0.4995", "GXY": "899800",
        "ALPX": "2.2E-04", "DENS": "1150", "KX": "0.15", "C": "1830",
        "SIGXT": "22000000", "SIGYLD": "22000000",
    },
    # 减振器压缩缓冲块。出处：多家微孔聚氨酯供应商资料（NDI/MDI 体系）
    #   密度 0.35~0.65 g/cm³（OEM 替换档 0.45~0.55）｜ 邵氏 A 70~90
    #   拉伸强度 8.0~11.0 MPa ｜ 断裂伸长率 335~450% ｜ 撕裂 29.5~44.5 kN/m
    #   使用温度 −40~+120 ℃（NDI）｜ 压缩永久变形低，50 万次疲劳验证
    # 取中档：ρ = 0.55 g/cm³、σb 取下限 8.0 MPa
    # ⚠️ 以下为【弹性体常用估算值，数据表未给】：E 由 G = 0.117·e^(0.034·Hs)（Hs=75）
    #    得 G ≈ 1.50 MPa、E = 3G ≈ 4.5 MPa；ν = 0.40（泡沫的可压缩性比实心橡胶大，
    #    表观泊松比取低于 0.5）；α/λ/c 亦为常用值。**定牌号后须实测复核。**
    # ⚠️ 缓冲块是【渐进非线性】的泡沫件，线性 E/ν 只够占位；做压缩特性分析须用
    #    载荷-变形曲线或泡沫本构（如 *FOAM / Ogden）。
    "微孔聚氨酯（PU）": {
        "kind": "橡胶", "rgb": "4a4a42",
        "note": "微孔聚氨酯（NDI/MDI）——减振器压缩缓冲块，邵氏 A 70~90",
        "EX": "4500000", "NUXY": "0.40", "GXY": "1607000",
        "ALPX": "1.5E-04", "DENS": "550", "KX": "0.20", "C": "1500",
        "SIGXT": "8000000", "SIGYLD": "8000000",
    },
}

# 旧名 → 新名（原地重命名，并把物性/外观一并纠正）
OLD_ALIAS = {
    "10#": "10号优质碳素结构钢",
    "20#": "20号优质碳素结构钢",
    "45#": "45号优质碳素结构钢",
    "40Cr": "40Cr合金结构钢",
    "Q345B": "Q345B低合金高强度结构钢",
    "QStE420": "QStE420热机械轧制高强钢",
    "60Si2MnA": "60Si2MnA弹簧钢",
    "POM": "聚甲醛（POM）",
    "POM-GF25": "25%玻纤增强聚甲醛（POM-GF25）",
    "橡胶_NR60": "天然橡胶（NR60）",
}

# 要清除的材料（别的项目留下的 / 已废弃的名字）
# ★ 删前必须确认没有模型引用：改名前逐个数 SLDPRT/SLDASM 里的 UTF-16LE 字节串，
#   本批已全盘扫描 834 个模型文件，确认零引用。
DELETE = ["自定义塑料", "舵机材料", "电池材料"]

NODE_TMPL = """\t\t<material name="{name}" description="-" propertysource="">
\t\t\t<shaders>
\t\t\t\t<pwshader2 name="{shname}" isNewShader="1" path="{shpath}"/>
\t\t\t\t<cgshader2 name="{cg}"/>
{tex}\t\t\t</shaders>
\t\t\t<swatchcolor RGB="{rgb}">
\t\t\t\t<sldcolorswatch:Optical Ambient="1.00000" Transparency="0.00000" Diffuse="1.00000" Specularity="1.00000" Shininess="0.200000" Emission="0.300000"/>
\t\t\t</swatchcolor>
\t\t\t<xhatch name="{hatch}" angle="0.0" scale="1.0"/>
\t\t\t<physicalproperties>
\t\t\t\t<EX displayname="弹性模量" value="{EX}" usepropertycurve="0"/>
\t\t\t\t<NUXY displayname="泊松比" value="{NUXY}" usepropertycurve="0"/>
\t\t\t\t<GXY displayname="抗剪模量" value="{GXY}" usepropertycurve="0"/>
\t\t\t\t<ALPX displayname="热膨胀系数" value="{ALPX}" usepropertycurve="0"/>
\t\t\t\t<DENS displayname="质量密度" value="{DENS}" usepropertycurve="0"/>
\t\t\t\t<KX displayname="热导率" value="{KX}" usepropertycurve="0"/>
\t\t\t\t<C displayname="比热" value="{C}" usepropertycurve="0"/>
\t\t\t\t<SIGXT displayname="张力强度" value="{SIGXT}" usepropertycurve="0"/>
\t\t\t\t<SIGYLD displayname="屈服强度" value="{SIGYLD}" usepropertycurve="0"/>
\t\t\t</physicalproperties>
\t\t\t<sustainability linkId="" dbName=""/>
\t\t</material>"""

TEX_LINE = '\t\t\t\t<swtexture path="images\\textures\\plastic\\polished\\pplastic2.jpg"/>'


def target_class(name):
    return CLASS_OF_KIND[MATERIALS[name]["kind"]]


def build_node(name, nl):
    cfg = MATERIALS[name]
    shpath, shname, cg, hatch = TPL[cfg["kind"]]
    tex = (TEX_LINE + nl) if cfg["kind"] != "钢" else ""
    return NODE_TMPL.format(name=name, shpath=shpath, shname=shname, cg=cg,
                            hatch=hatch, tex=tex, **{k: cfg[k] for k in
                            ("EX", "NUXY", "GXY", "ALPX", "DENS", "KX", "C",
                             "SIGXT", "SIGYLD", "rgb")}).replace("\n", nl) + nl


def mat_names(text):
    return re.findall(r'<material name="([^"]*)"', text)


def node_pattern(name):
    return re.compile(r'<material name="%s".*?</material>' % re.escape(name), re.S)


def class_of(text, name):
    for m in re.finditer(r'<classification name="([^"]*)">(.*?)</classification>',
                         text, re.S):
        if re.search(r'<material name="%s"' % re.escape(name), m.group(2)):
            return m.group(1)
    return None


def move_node(text, name, target, nl):
    """把已存在的材料节点从原分类搬到 target 分类末尾"""
    m = node_pattern(name).search(text)
    if not m:
        return text, False
    body = m.group(0)
    rest = text[:m.start()] + text[m.end():]
    i = rest.find('<classification name="%s">' % target)
    if i == -1:
        cls = ('\t<classification name="%s">' % target + nl + body + nl
               + '\t</classification>' + nl)
        j = rest.rfind("</mstns:materials>")
        return rest[:j] + cls + rest[j:], True
    j = rest.find("</classification>", i)
    return rest[:j] + body + nl + rest[j:], True


def write_lib(path, apply=False):
    if not os.path.exists(path):
        print(f"  ✗ 库不存在：{path}")
        return False
    raw = open(path, "rb").read()
    if raw[:2] != b"\xff\xfe":
        print(f"  ✗ BOM 不是 UTF-16 LE（{raw[:4].hex()}），中止")
        return False
    t = raw.decode("utf-16")
    nl = "\r\n" if "\r\n" in t else "\n"

    print(f"  现有材料：{'、'.join(mat_names(t))}")
    plan, new_t = [], t

    # ① 旧名 → 新名（原地整节点替换：名字、物性、外观一起纠正）
    for old, new in OLD_ALIAS.items():
        if re.search(r'<material name="%s"' % re.escape(new), new_t):
            continue
        m = node_pattern(old).search(new_t)
        if m:
            new_t = new_t[:m.start()] + build_node(new, nl).rstrip(nl) + new_t[m.end():]
            plan.append(f"重命名 {old} → {new}（物性/外观一并纠正）")

    # ② 缺失的补齐
    for name in MATERIALS:
        if re.search(r'<material name="%s"' % re.escape(name), new_t):
            continue
        node = build_node(name, nl)
        cls = target_class(name)
        i = new_t.find('<classification name="%s">' % cls)
        if i != -1:
            j = new_t.find("</classification>", i)
            new_t = new_t[:j] + node + "\t" + new_t[j:]
            plan.append(f"插入 {name}（到已有「{cls}」分类）")
        else:
            c = ('\t<classification name="%s">' % cls + nl + node
                 + '\t</classification>' + nl)
            j = new_t.rfind("</mstns:materials>")
            new_t = new_t[:j] + c + new_t[j:]
            plan.append(f"插入 {name}（新建「{cls}」分类）")

    # ③ 分类归属纠正
    for name in MATERIALS:
        cur = class_of(new_t, name)
        want = target_class(name)
        if cur and cur != want:
            new_t, ok = move_node(new_t, name, want, nl)
            if ok:
                plan.append(f"移分类 {name}：「{cur}」→「{want}」")

    # ④ 清除废弃材料（连前面的缩进一起删，不留空行）
    for name in DELETE:
        m = re.search(r'[ \t]*<material name="%s".*?</material>' % re.escape(name),
                      new_t, re.S)
        if m:
            new_t = new_t[:m.start()] + new_t[m.end():]
            plan.append(f"删除 {name}")

    if not plan:
        print("  = 无需改动")
        return False
    for p in plan:
        print("  · " + p)

    # ⑤ 写前 XML 校验
    try:
        ET.fromstring(new_t)
    except Exception as exc:
        print(f"  ✗ XML 校验失败，已中止（原文件未动）：{exc}")
        return False
    if not new_t.lstrip().startswith("<?xml"):
        print("  ✗ 声明头丢失，已中止（原文件未动）")
        return False
    print("  ✓ XML 校验通过，声明头完好")

    if not apply:
        print("  （预览模式：未写入）")
        return True

    bak = path + ".bak_" + STAMP
    shutil.copy2(path, bak)
    with open(path, "wb") as f:
        f.write(b"\xff\xfe" + new_t.encode("utf-16-le"))
    after = open(path, "rb").read()
    print(f"  ✓ 已写入（{len(raw)} → {len(after)} B，BOM={after[:2].hex()}，"
          f"备份 {os.path.basename(bak)}）")
    print(f"    现在材料：{'、'.join(mat_names(after.decode('utf-16')))}")
    return True


def main():
    apply = "--apply" in sys.argv
    print(f"【{'写入' if apply else '预览'}】材料表（中文全称 / 类别 / 颜色）")
    for name, cfg in MATERIALS.items():
        print(f"   {name:<26} {cfg['kind']:<4} #{cfg['rgb']}   {cfg['note']}")
    print("=" * 70)
    for tag, path in LIBS.items():
        print(f"── {tag} 库")
        write_lib(path, apply=apply)
    print("=" * 70)
    if apply:
        print("完成。★ SW 材质下拉需重启才刷新（API 按名解析通常即时生效）。")
    else:
        print("预览完毕。加 --apply 才会真正写入。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
