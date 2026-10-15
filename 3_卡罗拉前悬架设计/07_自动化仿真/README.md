# 07 · 自动化仿真（AI 辅助全流程）

> 从"SW 改参数"到"仿真结果判读"的**全自动化链路**——与 AI 编程助手协作开发。
> 配套**基座项目**（含完整求解导出物）：下载即可用命令行直接复跑仿真。

---

## 一、流程总览（单条链）

```
① SW 改参&重建 ─② 导出 x_t─▶ ③ ANSYS 换几何 + 接线自动修复 ─④ 网格/导出 ─▶
─▶ ⑤ 工况注入（驱动+阻尼）─▶ ⑥ CLI 批处理求解 ─▶ ⑦ 结果判读（RMS/趋势）
```

| 环节 | 核心脚本 | 说明 |
|---|---|---|
| ① 改参/导出 | `flow_sw_modify_export.py` | 改 txt → SW 重建（带错误检测）→ 导出 x_t |
| ③ 换几何 | `_geo_swap_server.py`、`_geo_reload_clean_jietou.py` | `gi.Import` 原位替换 + 清自动生成接头 |
| ③ 接线修复 | `_dump_faces_live*`、`_remap_faces_swap3.py`、`_mesh_scope_fix*`、`_fix_spring_ns*`、`_spring_facefix*`、`_fix_rp_pm*`、`_fix_cs*` | 面号重配 / 网格 scoping / 弹簧 / 命名选择 / 远程点 / 点质量 / 坐标系 |
| ③ 完备性体检 | `_final_check*`、`_probe_state_tree*` | 全树扫描（UnderDefined 清零） |
| ④ 导出 | `_export8/9*` | `a.Solve()` 生成 `file.dfs` + 全套（~60 秒） |
| ⑤ 工况注入 | `inject_case.py` | 轮跳驱动 + 双斜率阻尼 + 头部计数重算 + 建可跑目录 |
| ⑥ 批处理求解 | `rundfs.exe -i file -o resX -t N`（Console 目录） | CLI 求解（不进 GUI） |
| ⑦ 判读 | `_goswap_read.py`、`_goswap_groupmap.py`、`_trend_check.py` | 趋势 / RMS / 组号映射 |
| 参数扫描 | `_d1_prep.py`、`_theory_sweep.py` | 扫描包生成 + 理论快筛（SDOF） |

**判读约定**：每轮跑批后清理 `strain`/`stress` 重型文件；`disp`/`res` 保留。

## 二、环境要求

- **ANSYS 2024 R2**（v242）+ PyMechanical 0.13.x（`transport_mode="insecure"`、`cleanup_on_exit=False`）
- Python 环境：`~/.workbuddy/binaries/python/envs/pymechanical`（含 `olefile`）
- 会话端口：**10504**（工作会话）/ 10505（金标准对照，可选）
- 求解器 PATH（跑批）：`Motion\Solver\Console` + `tp\IntelMKL\...\winx64` + `commonfiles\CPython\...\python` + `System32`

## 三、基座项目（`基座项目/`）—— 下载即用

| 文件 | 说明 |
|---|---|
| `suspension_geoswap_repaired.mechdb` | 已修复、全完备的麦弗逊悬架刚柔耦合模型（46 实体 / 38 关节 / 26 柔性件 / 44,412 节点网格） |
| `suspension_geoswap_repaired_Mech_Files/` | 项目支撑文件，**含完整求解导出物**（`Transient/file.dfs` 25MB 等） |

**直接跑一次求解**（无需打开 Mechanical）：

```bash
cd 基座项目/suspension_geoswap_repaired_Mech_Files/Transient
# PATH 追加四个求解器目录后：
rundfs.exe -i file -o resTest -t 8
```

**模型工况**：位移驱动（1Hz / ±40mm 正弦轮跳）；双斜率阻尼用户子程序（`damper_dual_slope.dll`，随包，来源工程亦在本仓库可查）。
**判读脚本**：`scripts/_goswap_read.py <disp 路径> 1.5 75`

## 四、文档索引

| 文档 | 内容 |
|---|---|
| `流程文档/自动化仿真流程_设计文档.md` | **全流程设计与实测配方（v3）**——步骤 G0~G8、四种 id 空间、坑清单、判读口径、脚本清单 |
| `流程文档/ANSYS仿真工作流.md` | 操作手册——会话管理 / 文件桥模式 / 环境坑位 |
| `rebuild/README.md` | **"从零复刻链"**——没有可用底模型时走这条（脚本族在 `rebuild/data` 配套） |

## 五、两条路线（按场景选）

| 路线 | 适用场景 | 入口文档 |
|---|---|---|
| **几何替换路线**（推荐） | 已有可用底模型，要换几何/改参数复跑 | `流程文档/自动化仿真流程_设计文档.md` §7 |
| **重建链** | 从零复现整个模型 | `rebuild/README.md` |

---

*本链为"卡罗拉（E210）前悬架设计"课程设计的工程实践副产物；自动化框架与 AI 编程助手（WorkBuddy）协作开发，物理口径与判据由作者定义。*
