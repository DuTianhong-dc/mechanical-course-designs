# -*- coding: utf-8 -*-
r"""流程脚本 ①②（正式版）：SW 改参 → 重建（含错误检测）→ 导出 x_t → 回滚 → 验证
用法:
  python flow_sw_modify_export.py --part 转向节 --param "主销偏移距离轴承中心" --value 25

行为要点（设计者约定）:
 - 全程不改动模型库：txt 改后必回滚；几何不保存（关闭时丢弃）
 - 重建后做【错误检测】：EditRebuild3 返回码 + 逐特征 GetErrorCode 遍历（零件级+装配级）
 - 有错误时: 打印错误详情、不向 inbox 发布；仍尝试一次导出到 logs\ 作行为证据
 - 退出码: 0=成功(已导出) / 1=重建有错(未发布) / 2=流程异常
"""
import argparse
import datetime
import os
import re
import shutil
import sys
import time

import pythoncom
import win32com.client as w
from win32com.client import gencache

SW_BASE = r"C:\Users\dth15\Desktop\课程设计\机械设计2\03_模型"
AUTO = r"C:\Users\dth15\Desktop\ANSYS\automation"
INBOX = os.path.join(AUTO, "inbox")
LOGS = os.path.join(AUTO, "logs")
RUNLOG = os.path.join(AUTO, "runlog.csv")

os.makedirs(LOGS, exist_ok=True)

_log_f = None


def log(msg=""):
    print(msg, flush=True)
    if _log_f:
        _log_f.write(str(msg) + "\n")
        _log_f.flush()


def staticize(mod, interface, obj):
    if obj is None:
        return None
    cls = getattr(mod, interface, None)
    if cls is None:
        return obj
    for arg in (getattr(obj, "_oleobj_", None), obj):
        if arg is None:
            continue
        try:
            return cls(arg)
        except Exception:
            continue
    return obj


def open_doc(sw, path, dtype):
    try:
        d = sw.OpenDoc6(path, dtype, 1, "")
        if d is not None:
            return d
    except Exception:
        pass
    try:
        return sw.OpenDoc(path, dtype)
    except Exception as e:
        log("  打开失败: %s" % str(e)[:120])
        return None


def feature_errors(doc, tag):
    """遍历特征树，收集 GetErrorCode 非零的特征"""
    errs = []
    try:
        f = doc.FirstFeature()
    except Exception as e:
        log("  [%s] 特征遍历失败: %s" % (tag, str(e)[:100]))
        return errs
    while f is not None:
        try:
            f2 = staticize(MOD, "IFeature", f)
            code = f2.GetErrorCode()
            if code:
                try:
                    errs.append((f2.Name, f2.GetTypeName2(), code))
                except Exception:
                    errs.append(("(读名失败)", "?", code))
            f = f2.GetNextFeature()
        except Exception:
            break
    return errs


def read_volume(pd):
    mp = pd.Extension.CreateMassProperty()
    return round(mp.Volume * 1e9, 2)


def run_number():
    n = 1
    if os.path.exists(RUNLOG):
        for line in open(RUNLOG, encoding="utf-8-sig"):
            m = re.match(r"^(\d+),", line)
            if m:
                n = int(m.group(1)) + 1
    return n


def main():
    global _log_f, MOD
    ap = argparse.ArgumentParser()
    ap.add_argument("--part", required=True, help="零件名（不含扩展名）")
    ap.add_argument("--param", required=True, help="参数名（txt 中键名，不含引号）")
    ap.add_argument("--value", required=True, help="新值")
    ap.add_argument("--asm", default="麦弗逊悬架", help="含该零件的装配体名")
    ap.add_argument("--keep", action="store_true", help="正式改版模式：成功则保留新值并保存；失败仍回滚")
    ap.add_argument("--export-asm", dest="export_asm", default=None, help="收尾把该装配体导出为 x_t（仅 keep 成功时）")
    args = ap.parse_args()

    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    logf = os.path.join(LOGS, "run_%s_%s_%s.log" % (ts, args.part, args.param.replace("/", "_")))
    _log_f = open(logf, "w", encoding="utf-8")

    log("=" * 70)
    log("流程运行: %s | 零件=%s 参数=%s 新值=%s" % (ts, args.part, args.param, args.value))
    log("=" * 70)

    PART = os.path.join(SW_BASE, args.part + ".SLDPRT")
    ASM = os.path.join(SW_BASE, args.asm + ".SLDASM")
    TXT = os.path.join(SW_BASE, args.part + "_参数.txt")
    BAK = TXT + ".bak_flow_" + ts
    RUN = run_number()
    XT_OUT = os.path.join(INBOX, "%s_run%02d.x_t" % (args.part, RUN))

    for p in (PART, TXT, ASM):
        if not os.path.exists(p):
            log("!! 文件缺失: %s" % p)
            return 2

    pythoncom.CoInitialize()
    sw = w.GetActiveObject("SldWorks.Application")
    log("SW PID: %s" % sw.GetProcessID())
    global MOD
    MOD = gencache.GetModuleForTypelib("{83A33D31-27C5-11CE-BFD4-00400513BB57}", 0, 34, 0)

    # ---------- 1) 打开零件 ----------
    pd = staticize(MOD, "IModelDoc2", open_doc(sw, PART, 1))
    if pd is None:
        log("!! 零件打开失败")
        return 2
    sw.ActivateDoc3(args.part + ".SLDPRT", False, 0, 0)
    time.sleep(0.5)
    log("\n[1] 零件: %s" % pd.GetPathName())
    if pd.GetSaveFlag():
        log("!! 零件处于【已修改未保存】状态——先手动处理，流程中止")
        return 2

    vol0 = read_volume(pd)
    errs0 = feature_errors(pd, "零件-基线")
    log("    基线体积: %.2f mm^3 | 基线错误特征: %d 个" % (vol0, len(errs0)))

    # ---------- 2) 读旧值并改 txt ----------
    b = open(TXT, "rb").read()
    KEY = ('"' + args.param + '"').encode("utf-8")
    m = re.search(rb"(" + KEY + rb"\s*=\s*)([0-9.]+)(\s*\r?\n)", b)
    if not m:
        log("!! 在 txt 中未找到参数: %s" % args.param)
        return 2
    old_val = m.group(2).decode()
    log("\n[2] txt 参数: %s = %s  →  目标 %s" % (args.param, old_val, args.value))
    shutil.copy2(TXT, BAK)
    log("    已备份: %s" % os.path.basename(BAK))
    b2 = b[: m.start()] + m.group(1) + args.value.encode() + m.group(3) + b[m.end():]
    open(TXT, "wb").write(b2)

    # ---------- 3) 读入 + 重建（零件级） ----------
    em = pd.GetEquationMgr()
    ok = em.UpdateValuesFromExternalEquationFile()
    log("\n[3] UpdateValuesFromExternalEquationFile: %s  方程数: %d" % (ok, em.GetCount()))
    rc = pd.EditRebuild3()
    errs1 = feature_errors(pd, "零件-重建后")
    log("    EditRebuild3: %s | 重建后错误特征: %d 个" % (rc, len(errs1)))
    for name, tname, code in errs1[:15]:
        log("      ✗ 特征[%s] 类型[%s] 错误码=%s" % (name, tname, code))

    # ---------- 4) 装配体重建（级联检测） ----------
    log("\n[4] 装配体重建检查: %s" % args.asm)
    ad = staticize(MOD, "IModelDoc2", open_doc(sw, ASM, 2))
    rc_asm, errs_asm = None, []
    if ad is None:
        log("    装配体打开失败（跳过）")
    else:
        sw.ActivateDoc3(args.asm + ".SLDASM", False, 0, 0)
        time.sleep(0.5)
        rc_asm = ad.EditRebuild3()
        errs_asm = feature_errors(ad, "装配体")
        log("    装配体 EditRebuild3: %s | 错误特征: %d 个" % (rc_asm, len(errs_asm)))
        for name, tname, code in errs_asm[:15]:
            log("      ✗ 特征[%s] 类型[%s] 错误码=%s" % (name, tname, code))
        sw.CloseDoc(args.asm + ".SLDASM")   # 装配无改动，直接关（零件改动仍在内存）
        time.sleep(1)

    # ---------- 5) 判定与导出 ----------
    has_err = (rc is False) or bool(errs1) or (rc_asm is False) or bool(errs_asm)
    vol1 = None
    exported = False
    if has_err:
        log("\n[5] ⚠ 重建报错 —— 不向 inbox 发布")
        # 行为证据：仍尝试一次导出到 logs
        probe = os.path.join(LOGS, "%s_run%02d_ERR_probe.x_t" % (args.part, RUN))
        try:
            r = pd.Extension.SaveAs(probe, 0, 2, None, 0, 0)
            log("    探测导出(logs): %s | 文件存在: %s" % (r, os.path.exists(probe)))
        except Exception as e:
            log("    探测导出异常: %s" % str(e)[:120])
    else:
        vol1 = read_volume(pd)
        r = pd.Extension.SaveAs(XT_OUT, 0, 2, None, 0, 0)
        exported = os.path.exists(XT_OUT)
        log("\n[5] 重建无错误；体积: %.2f → %.2f (Δ=%.2f mm^3)" % (vol0, vol1, (vol1 or 0) - vol0))
        log("    导出: %s | %s (%d B)" % (r, XT_OUT, os.path.getsize(XT_OUT) if exported else 0))

    # ---------- 6) 收尾：失败回滚 / keep 保存 / 实验回滚 ----------
    asm_exported = False
    if has_err:
        shutil.copy2(BAK, TXT)
        log("\n[6] 重建报错 → txt 已从备份回滚（失败不落盘）")
        try:
            sw.CloseDoc(args.part + ".SLDPRT")
            time.sleep(1)
        except Exception as e:
            log("    关闭零件异常: %s" % str(e)[:100])
    elif args.keep:
        part_bak = PART + ".bak_flow_" + ts
        shutil.copy2(PART, part_bak)
        log("\n[6] keep 模式：保留 txt 新值；零件文件已备份: %s" % os.path.basename(part_bak))
        saved = False
        try:
            pd.SaveAs3(PART, 0, 0)
            saved = True
            log("    保存文档: SaveAs3 原位 OK")
        except Exception as e1:
            try:
                pd.Save3(0, 0, 0)
                saved = True
                log("    保存文档: Save3 OK")
            except Exception as e2:
                log("    !! 保存失败: %s | %s" % (str(e1)[:60], str(e2)[:60]))
        if not saved:
            log("    !! 未能保存——回滚 txt 以保一致")
            shutil.copy2(BAK, TXT)
        try:
            sw.CloseDoc(args.part + ".SLDPRT")
            time.sleep(1)
        except Exception as e:
            log("    关闭零件异常: %s" % str(e)[:100])
    else:
        shutil.copy2(BAK, TXT)
        log("\n[6] txt 已从备份回滚")
        try:
            sw.CloseDoc(args.part + ".SLDPRT")
            time.sleep(1)
        except Exception as e:
            log("    关闭零件异常: %s" % str(e)[:100])

    # ---------- 7) 复验 ----------
    pd2 = staticize(MOD, "IModelDoc2", open_doc(sw, PART, 1))
    verify_ok = False
    if pd2:
        vol2 = read_volume(pd2)
        if args.keep and not has_err:
            verify_ok = abs(vol2 - (vol1 if vol1 is not None else vol0)) < 1.0
            log("\n[7] 重开体积: %.2f (新几何应为 %.2f) → 落盘验证: %s" % (
                vol2, vol1 if vol1 is not None else vol0, "PASS" if verify_ok else "FAIL"))
        else:
            verify_ok = abs(vol2 - vol0) < 1.0
            log("\n[7] 重开体积: %.2f (基线 %.2f) → 回滚验证: %s" % (vol2, vol0, "PASS" if verify_ok else "FAIL"))
        sw.CloseDoc(args.part + ".SLDPRT")
        time.sleep(0.5)
    else:
        log("\n[7] 重开失败")

    # ---------- 7b) 装配体重建 + 导出（--export-asm，仅 keep 成功） ----------
    asm_xt = None
    if args.export_asm and args.keep and not has_err:
        log("\n[7b] 装配体重建与导出: %s" % args.export_asm)
        ad2 = staticize(MOD, "IModelDoc2", open_doc(sw, os.path.join(SW_BASE, args.export_asm + ".SLDASM"), 2))
        if ad2 is None:
            log("    装配体打开失败")
        else:
            sw.ActivateDoc3(args.export_asm + ".SLDASM", False, 0, 0)
            time.sleep(0.5)
            rc3 = ad2.EditRebuild3()
            errs3 = feature_errors(ad2, "装配体-复验")
            log("    装配体 EditRebuild3: %s | 错误特征: %d 个" % (rc3, len(errs3)))
            for name, tname, code in errs3[:10]:
                log("      ✗ 特征[%s] 类型[%s] 错误码=%s" % (name, tname, code))
            if rc3 is not False and not errs3:
                asm_xt = os.path.join(INBOX, "%s_run%02d.x_t" % (args.export_asm, RUN))
                try:
                    r2 = ad2.Extension.SaveAs(asm_xt, 0, 2, None, 0, 0)
                    asm_exported = os.path.exists(asm_xt)
                    log("    装配导出: %s | %s (%d B)" % (r2, asm_xt, os.path.getsize(asm_xt) if asm_exported else 0))
                except Exception as e:
                    log("    装配导出异常: %s" % str(e)[:120])
                    asm_xt = None
            else:
                log("    ⚠ 装配体重建有错——不导出")
            sw.CloseDoc(args.export_asm + ".SLDASM")
            time.sleep(1)

    # ---------- 8) runlog ----------
    status = "REBUILD_ERROR" if has_err else ("OK_KEEP" if args.keep else "OK")
    try:
        with open(RUNLOG, "a", encoding="utf-8-sig") as f:
            if not os.path.exists(RUNLOG) or os.path.getsize(RUNLOG) == 0:
                f.write("run,time,part,param,old,new,vol_before,vol_after,err_count,x_t,rollback,status\n")
            xt_field = os.path.basename(asm_xt) if asm_exported else (os.path.basename(XT_OUT) if exported else "(未发布)")
            f.write("%d,%s,%s,%s,%s,%s,%s,%s,%d,%s,%s,%s\n" % (
                RUN, ts, args.part, args.param, old_val, args.value, vol0,
                vol1 if vol1 is not None else "", len(errs1) + len(errs_asm),
                xt_field, "PASS" if verify_ok else "FAIL", status))
    except Exception as e:
        log("runlog 写入失败: %s" % str(e)[:100])

    log("\n结果: %s | 导出: %s | 验证: %s | 模式: %s" % (
        "重建报错(已检测)" if has_err else "成功",
        "是" if (asm_exported or exported) else "否",
        "PASS" if verify_ok else "FAIL",
        "keep(落盘)" if args.keep else "实验"))
    log("日志: %s" % logf)
    return 1 if has_err else 0


if __name__ == "__main__":
    sys.exit(main())
