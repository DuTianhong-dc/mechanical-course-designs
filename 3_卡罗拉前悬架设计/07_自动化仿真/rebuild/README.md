# 复刻工具包（rebuild）—— v2 工况 → 新几何 全链复刻流程

> **场景**：拿到一版新几何（或修改后的模型），要"从零复现 v2 的全部设置 + 工况"并跑出结果。
> **★ 姊妹路线（2026-10-13 打通）**：**「几何替换路线」**——从 meshtest 底模型原位换几何（`gi.Import`）+ 全 API 接线修复，**免 dfs 手术、工况对象原生、网格配方继承**。配方见 `课程设计\自动化仿真流程_设计文档.md` 第 7 节；工程现场 `suspension_geoswap_repaired.mechdb`。**两者取舍**：底模型完好时优先替换路线；从零/底模型不可用时走本重建链。
> **组成**：本 README（流程单）+ `data/`（数据包）。执行脚本在 `../scripts/`（全部为自足客户端，自动连接 10504 会话）。
> **末次全链验证**：2026-10-12（φ27 版 v3：复刻完成 + 驱动/阻尼注入 + 5s 求解跑通）；
> **2026-10-13 补修链（"第二刀"）落地**：dfs 手术 + rbe 质量回填 → v3-fixed 治愈实锤（见第二节 9b/9c）。

---

## 环境常量

| 项 | 值 |
|---|---|
| Mechanical 会话 | 端口 **10504**（GUI 可见，脚本退出后存活） |
| Python 解释器 | `C:\Users\dth15\.workbuddy\binaries\python\envs\pymechanical\Scripts\python.exe` |
| 脚本目录 | `C:\Users\dth15\Desktop\ANSYS\automation\scripts\` |
| 数据包 | `C:\Users\dth15\Desktop\ANSYS\automation\rebuild\data\`（本包；脚本默认读 `../logs/`，**复刻前恢复**：`copy rebuild\data\* logs\`，或改脚本顶部路径） |
| 新几何 | `麦弗逊悬架_run04.x_t`（φ27 版；换版时改 `import_geometry_10504.py` 路径常量） |
| 求解器 | `C:\Program Files\ANSYS Inc\v242\Motion\Solver\Console\rundfs.exe` |
| 阻尼 dll | `damper_dual_slope.dll`（Console 目录常驻；注入器会自动往 workdir 补） |

---

## 一、机械侧复刻链（按序执行，每步看验证文件）

| 序 | 脚本 | 干什么 | 验证点（logs/） |
|---|---|---|---|
| 0 | `_launch_fresh_session.py` | 启动干净 10504 会话 | 打印 `SESSION READY`；`session_info_10504.json` |
| 1 | `import_geometry_10504.py` | 导入新几何 + 侦察容器 | `import_recon_10504.json`（part/body 数） |
| 2 | `apply_rebuild_10504.py` | ①改名 ②分组 ③抑制 ④材料 | `apply_rebuild_result.json`（四块统计全绿） |
| 3 | `build_joints2_10504.py` | ⑤全量 6 组 37 关节 + Bushing 刚度/阻尼 + 清 87 自动接触 | `build_joints2_result.json`（37/37、mb/rb 全配） |
| 4 | `build_spring_10504.py` | ⑥弹簧力元素（k=33.3 / Load=4730 / 预载类型） | `build_spring_result.json` |
| 4b | `fix_springjoint_10504.py` | 补丁：弹簧-筒身 mobile 侧补选 | `fix_springjoint.json` |
| 4c | `fix_spring_params_10504.py` | 补丁：k/Load 用 Quantity + PreloadType 后置 | `fix_spring_params.json`（回读值对） |
| 5 | `build_pm_ns3_10504.py` | ⑦点质量 482.16kg + 4 命名选择 | `build_pm_ns3.json` |
| 5b | `fix_pm_behavior_10504.py` | 补丁：Behavior=Rigid | `fix_pm_behavior.json` |
| 6 | `vt_final_v3.py` | 虚拟拓扑（19 参数 → 116 VirtualCell） | `vt_final_v3.json`（cell 数） |
| 7 | `build_analysis_v3_10504.py` | 分析层：Motion 分析 + EarthGravity | `build_analysis_v3.json` |
| 7b | `fix_eg_jl_v3.py` | 补丁：重力方向 PositiveYAxis（+Y！） | `fix_eg_jl_v3.json` |
| 7c | `fix_sup_dof_v3.py` | 补丁：4 关节抑制对齐 v2（顶胶-地/弹簧-筒身/活塞-导向块/活塞-缓冲块） | `fix_sup_dof_v3.json` |
| 8 | `export_v3.py` | 导出求解输入（GenerateInputOnly） | `export_v3.json`（dfs 路径） |

> **补丁脚本（4b/4c/5b/7b/7c）不能跳过**：上游脚本未改，重跑时会犯同样的错，补丁是链条的一部分。
> 全部跑完后：**在 UI 里 `Save()` 存档**（`SaveAs` 会报 already exists）。

## 二、工况注入 + 跑批（dfs 侧）

| 序 | 命令 | 说明 |
|---|---|---|
| 9 | `python inject_case.py <suspension_v3_Mech_Files\Transient\file.dfs> <out\file_CASE.dfs> --workdir <v3_run_X> --ssc "5 250 0"` | 一键注入：轮跳驱动（40·SIN）+ 阻尼（dll/SPLINE/T-SCALAR/markers）+ 头部计数自动重算 + 建可跑目录。产出 `<out>_report.txt` 校验表（应"修正 5-6 项、其余 OK"） |
| 10 | 在 workdir 内：`rundfs.exe -i file -o res5s -t 4`（PATH 追加 `v242\tp\IntelMKL\2023.1.0\winx64` 与 `v242\commonfiles\CPython\3_10\winx64\Release\python`） | 5s/250 点 ≈ 4-6 h（v3 规模）；产物 disp/res/strain/stress |

**ssc 三位含义**：`<结束时间s> <输出步数> <开始时间s>`。
- `5 250 0` → 5.0s、dt=0.02、~252 帧（**体积 ~9.3GB**，C 盘友好）
- `5 500 0` → dt=0.01、~502 帧（**体积 ~18.5GB**，需先腾磁盘）
- 体积估算 = 帧数 × 113774 节点 × (24B disp / 96B res / 136B strain / 68B stress)

### 9b/9c 补修链（"第二刀"，2026-10-13 新增，**必跑**）

**为什么**：v3 的复刻源 = 修复前 v2。相比用户验收的修复版（meshtest）还缺两样：
① `活塞↔顶胶内层` 平移副（修复关节 #1388）——**缺它 = 长时程失稳**（簧上质量 0.8s 坠 1.3m，10-13 三维对照实验实锤）；
② 4 个 rbe 的质量/惯性（482kg 块 I=5.906e7=59kg·m²、活塞 0.35kg、球头×2 0.199kg、耳板 0.75kg——重建未带）。

| 序 | 命令 | 说明 |
|---|---|---|
| 9b | `python dfs_surgery.py`（路径常量在脚本头） | dfs 手术：补 TRAJOINT#2 + markers 71/72（照 #1661 样式：帧 O_B、体 53↔56）。产出 `outbox/file_V3REP.dfs` |
| 9c | `python patch_rbe_mass.py <in.dfs> <out.dfs>` | rbe 质量回填：从 meshtest 原文拷 5 组 [flag,m,I…]（b53/b9/b11/b13/b66）。默认 `v3_run_R1/file.dfs` → `outbox/file_V3FIXED.dfs` |

**推荐全链**：`export → dfs_surgery.py → inject_case.py → patch_rbe_mass.py → 跑批目录`。

**⚠️ 验证判据（10-13 教训，务必遵守）**：
- **10ms 冒烟判不出发病与否**（"-25mm 穿透" = 正常静载下沉瞬态 δ≈20mm，健康/病态在 10ms 几乎逐帧相同）——10ms 只验证"能跑 + 零错误 + dll 加载"。
- **疗效判读必须 ≥0.2s**：`python _trend_check.py <disp>` → 治愈 = 482kg Y @0.2s < 5mm；病态 = 加速下坠（@0.2s ≈ 72mm、@0.8s ≈ 1300mm）。
- 金标准 → `spring_fea\_5s版档案\5s刚柔耦合版验证报告.md`（修复版 5s 稳态："#70 相对活塞 0.4~7.3mm 周期浮动"）。

## 三、数据包（`rebuild/data/`）

| 文件 | 用途 | 被谁读 |
|---|---|---|
| `rebuild_pack.json` | 46 实体 + 7 组 38 关节（映射后新面 ID） | apply_rebuild / build_joints2 |
| `import_structure_10504.json` | 新几何导入结构（gid 清单） | apply_rebuild |
| `v2_readback_full.json` | v2 全量读回（51 part / 38 关节 / Bushing 值 / 材料…） | apply_rebuild / build_joints2 / build_pm_ns3 |
| `v2_extra2.json` | v2 body→材料映射 | apply_rebuild |
| `surftype_10504.json` / `surftype_v2.json` | 面类型表（新/旧） | build_pm_ns3（选面判据） |
| `face_map_final_v4.csv` | 面映射结果 130/130（三重判据） | 溯源用（重建 rebuild_pack 时） |

## 四、操作级坑（会直接导致失败）

1. **中文转义铁律**：服务端脚本里的中文必须 `\uXXXX`（IronPython 2.7）；客户端"生成器模式"拼接，**不要用 heredoc 传含 `\u` 的脚本**。
2. **弹簧 Load 必须在 PreloadType 之后设置**才生效；k/Load 用 `Quantity(值,单位)`。
3. **VT 参数**用 `Quantity`；枚举类名 = `VirtualCellGroupAutomaticBehaviorType` / `YesNoType` / `VirtualCellGroupMethodType` / `VirtualCellGroupRepairBehaviorType`（写错类名会静默不生效）。
4. **点质量 Behavior** 枚举 = `LoadBehavior.Rigid`。
5. **关节 API**：`g=AddConnectionGroup(); j=g.AddJoint()`；选面 `CreateSelectionInfo(GeometryEntities)` 1 参；Bushing 上三角索引 Kx0…Krz5。
6. **会话保活**：启动器结尾必须 `sys.exit(0)`（`os._exit` 会父死子亡带走 Mechanical）；强杀会留 `.mech_lock`，移走即解。
7. **改名要改两层**：Part 名 + `part.Children[0].Name`（Body 名才是树里显示的名字）。
8. **同会话内改名/分组后树 UI 不刷新** → 重开项目再看；名字校验用 len+codepoints。
9. **跑批永远走 CLI**（GUI/API 求解后 Mechanical 主进程会"延迟猝死"）；`damper_dual_slope.dll` 须在求解工作目录或 Console 目录。

## 五、验证基线（上次全链的对照数字）

- apply_rebuild：改名 46 / 分组 4 / 抑制 16 / 材料 46
- build_joints2：**37/37 关节** + 3 组 Bushing 刚度阻尼回读一致 + 接触清零
- VT：**116 VirtualCell**（v2=140，差异因几何面片化程度不同）
- 注入报告：`修正 6 项，其余 OK`（MARKER/EXPR/USER/SPLINE/MOTION/T-SCALAR）
- 冒烟（10ms）：正常退出 + dll 加载（进程模块表可查）+ 表达式通道输出 `40·sin(2πt)`
- **0.2s 趋势判读基线（10-13 实测定档）**：手术版 482kg Y@0.2s=**0.02mm**（治愈）；无手术对照 = **72.4mm** 且加速（与 res5s 逐点吻合）；两者 disp 用 `_trend_check.py` 一跑便知
