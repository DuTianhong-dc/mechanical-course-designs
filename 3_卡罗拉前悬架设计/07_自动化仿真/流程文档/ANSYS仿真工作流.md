# ANSYS 仿真工作流 · 卡罗拉前悬架（通用零件版）

> **建立**：2026-10-08（基于弹簧压缩仿真的完整实战）
> **环境**：ANSYS 2024 R2（v242）+ PyMechanical 0.13.3（venv：`~/.workbuddy/binaries/python/envs/pymechanical`）
> **目的**：跨零件复用、避免重复踩坑。后续零件（减振器壳、下摆臂、转向节…）照此执行。
> **★ 战略（2026-10-08 用户决策）**：**打通优先，优化后置**——先完整跑通「跳动→运动学 + 载荷→部件受力」链路；参数优化因 SW 参数化不完备等原因暂缓。决策原文见《用户决策记录.md》。

---

## 一、总原则（血泪三条）

### 1.1 「慢 ≠ 死」
- 机械的**网格生成**和**大变形求解**都会"看起来卡死"：进度条冻住、CPU 只吃 20-30%、长时间无输出。
- **真相**：它在合法地忙（单线程几何求值 / 牛顿迭代）。弹簧 46 万单元的网格跑了 **15-19 分钟**；大变形求解可跑 **30 分钟+**。
- **铁律**：判定失败必须区分「真失败（有终止/报错）」vs「还在跑」。**宁可多等，不可乱掐**（掐断=前功尽弃，多次教训）。
- **验证"在跑"的方法**：任务管理器的 CPU 累计采样（`Get-Process -Id <PID> | Select CPU`，间隔 5 秒看增量）。
- 网格生成的"失败"形态：调用返回后 `ObjectState = NotSolved`（或 UnderDefined）——**但注意**：`GenerateMesh()` 返回 ≠ 完成（有异步提交现象），须等 `mesh.IsMeshing` 变 False 再读状态。

### 1.2 「口径先行」
- **对账前先确定理论值的口径**（写进报告）：
  - 刚度 k：理论公式用**有效圈 n**（本弹簧 n=6 → k=33.3 N/mm）；FEA 模型是**全几何**（端圈参与 → 等效 ~7.1 圈）→ **两口径必然差 ~15%**，这是物理事实不是错误。
  - 应力：**τmax = 8FDK/(πd³)**（修正剪应力，K=1.157）——对应 FEA 的 **Maximum Shear Stress** 结果；von Mises ≠ 该口径。
  - 位移：区分「压缩量」vs「目标高度」——**模型实际总高 ≠ 名义自由长**（本弹簧：实测 336.75 vs 名义 330）——**位移按"压到目标高度"计算**。
- **线性自洽校验**：改位移后所有结果等比变化 → 证明材料/边界/求解链路一致。

### 1.3 「单变量 + 全程留痕」
- 每次只改一个参数；每个关键数据**写本地文件**再读（文件桥），别依赖"脚本返回值"。

---

## 二、环境与工具链

### 2.1 可见会话模式（核心资产）

**启动**（脚本 `C:\baidunetdiskdownload\spring_fea\start_visible.py`）：

```python
mech = launch_mechanical(
    batch=False,               # GUI 可见（窗口弹在屏幕上）
    port=10500,                # 固定端口（自动避让已占用）
    start_instance=True,       # 强制新实例
    transport_mode="insecure", # ★ v242 未打 SP05，必须 insecure
    cleanup_on_exit=False,     # ★ 脚本退出后 Mechanical 继续存活
    start_timeout=300,
    allow_input=False,
)
# 写 session_info.json 后 os._exit(0)
# ★ 坑：os._exit 不刷 stdout 缓冲 → 退出前必须 sys.stdout.flush()
```

**日常连接**（每次操作用独立进程）：

```python
mech = connect_to_mechanical(port=10500, transport_mode="insecure", cleanup_on_exit=False)
r = mech.run_python_script("...脚本...")
os._exit(0)   # 硬退出，绝不误关会话
```

**会话出问题时的恢复流程**：
1. `taskkill /PID <AnsysWBU的PID> /F`（先 `Get-Process AnsysWBU` 查 PID 和标题确认）
2. 删除项目锁：`rm spring_Mech_Files/.mech_lock`
3. 重跑 `start_visible.py`（~21 秒就绪）
4. 打开项目：`ExtAPI.DataModel.Project.Open(r"…\spring.mechdb")`
5. 验证：几何数 / 材料名 / `Mesh.ObjectState`

### 2.2 文件桥模式（run_python_script 的真相）

- `run_python_script` **只回传「最后一个表达式的值」**；`print` 的内容**不回传**；复杂对象（list 等）**只给类型名**。
- **因此**：所有数据交换走「**脚本把结果写本地文件 → 外部读**」。
- **★ 中文坑**：机械服务端脚本里对 **.NET 中文属性**做 `str()`/拼接会抛异常（`'ascii' codec...`）——**这是第一次崩溃的真凶**。
  - 对策：用 `safe_str()`（见下）；写文件一律 `io.open(path, "w", encoding="utf-8")`；中文**作为"最后表达式"回传是安全的**（gRPC 层没问题）。

### 2.3 必备 helper 模板（每份脚本粘贴使用）

```python
import io
base = r"C:\baidunetdiskdownload\spring_fea"

def rec(s):                       # 结果实时落盘（每步都写，崩溃也不丢）
    try:
        f = io.open(base + "/_log.txt", "w", encoding="utf-8")
        f.write(s); f.close()
    except Exception:
        pass

def safe_str(x):                  # 防中文炸：str → repr → 占位
    try:    return str(x)
    except Exception: pass
    try:    return repr(x)
    except Exception: pass
    return "<unprintable>"
```

### 2.4 本机环境限制清单

| 限制 | 内容 | 影响/对策 |
|---|---|---|
| **HPC 许可** | 求解器**只有 4 核**（请求 16 核被拒） | 求解慢的根源；**网格端可设 `NumberOfCPUsForParallelPartMeshing = 8`**（有效） |
| GPU | 8GB（低于推荐 15GB） | 仅"加速不足"提示，不影响正确性 |
| **中文** | 服务端 str(中文属性) 会炸 | 见 2.2 |
| 回收站 | 本环境 `rm` = 归档进回收站 | 删大文件后查 C 盘空间是否真释放 |
| 提权 | AI 无法提权 | 需管理员操作时：生成 .bat → 用户右键运行 |
| 求解器工作目录 | `项目_Mech_Files/StaticStructural/` | 内含 ds.dat / solve.out / file.err / file.rst —— **取证金矿** |

---

## 三、标准作业流程 SOP（8 步）

### ① 建会话
见 2.1。可见模式下用户全程可监督。

### ② 导入几何
```python
gi = Model.GeometryImportGroup.AddGeometryImport()
gi.Import(r"C:\...\model.x_t")     # x_t / STEP / agdb 均可；中文路径 OK
```
验证：`len(Model.Geometry.Children)`（零件数）。

### ③ 几何认知（**必做，先看清再动手**）
```python
gb = Model.Geometry.Children[0].Children[0].GetGeoBody()
gb.Id            # 体 ID（后面选择要用）
gb.Volume        # 体积（校验）
gb.Faces         # 面集合 —— 每个面有 .Id / .Centroid / .Area / .SurfaceType
gb.GetBoundingBox()   # 包围盒（判总高/直径）
```
- **判"上下端面"**：面 `Centroid[2]`（Z）最小=底面、最大=顶面；`SurfaceType=GeoSurfacePlane` = 平面。
- 弹簧实测：3 个面（螺旋 BSpline + 上下两个磨平端面），底面 Id=8、顶面 Id=7。

### ④ 材料（**完整链条，照抄**）
```python
# 创建（复制现有材料再改名——与原件共享 ED 数据指针）
newmat = Model.Materials.Children[0].Duplicate()
newmat.Name = "60Si2MnA"

# 改数据（SI 单位！）
mc = newmat.GetEngineeringDataMaterial()
mp = mc.MaterialProperties                    # .Count 可用，len() 不行
# 按 Name 找属性（"Density" / "Elasticity" / "Tensile Ultimate Strength"）
# → p.MaterialPropertyDatas[0] → .AllVariables（按 Name 找变量）
v.SetDoubleData(0, 2.06e11)                   # 写（Pa）
v.GetAsDouble(0)                              # 读（验证）
```
- **密度 7850 kg/m³、E 2.06e11 Pa、ν 0.3、σb 1.65e9 Pa**
- 死路（别走）：`GetMaterialAsDictionary`、`PropertyByAPIName`、`Materials.AddMaterial`。
- 材料列表长这样：两条同名条目（复制品+原件共享数据）属正常现象。

### ⑤ 网格（**本流程最重的活**）
```python
mesh = Model.Mesh
mesh.ClearGeneratedData()                       # 清旧（可反复重来，永远干净）
mesh.ElementSize = Quantity(2, "mm")            # ★ 必须 Quantity（字符串报错）
mesh.AutomaticMeshBasedDefeaturing = True       # 去特征（治端部碎面，可写）
mesh.NumberOfCPUsForParallelPartMeshing = 8     # 并行核数（实测有效！）
mesh.GenerateMesh()
# 等待：while mesh.IsMeshing: sleep —— 然后读状态
# 结果周期：16 核环境约 9.5-19 分钟（46 万单元）
```
- **状态词**：`Solved` 完成 ｜ `NotSolved` 未完成/失败 ｜ `UnderDefined` 缺定义
- **单元计数**（安全读法）：`mesh.Tet10` / `mesh.Hex8`（数值属性）；**别碰 `Nodes`/`Elements`（大集合会拉爆）**
- **方法控制（Sweep 等）**：`m = mesh.AddAutomaticMethod()` → `m.Location = <SelectionInfo>` → `m.Method = MethodType.Sweep` → `m.SourceTargetSelection = 4`
  - ⚠️ **螺旋体 Sweep 会被引擎静默回退**（生成结果仍是 Tet10）——扫掠适用"回转体/直线扫掠体"（**减振器壳这类回转件应优先试 Sweep**）
  - ⚠️ 方法对象**必须设 Location**，否则 `UnderDefined`（不生成）
- **选择机制（通用）**：
  ```python
  sel = ExtAPI.SelectionManager.CreateSelectionInfo(SelectionTypeEnum.GeometryEntities)
  sel.Ids = [8]        # 几何 Id 列表（面/体）
  obj.Location = sel
  ```
  （Worksheet 式 Named Selection 路线**未走通**，弃用）

### ⑥ 分析 + 边界条件
```python
a = Model.AddStaticStructuralAnalysis()        # 独立会话里先建分析
fixed = a.AddFixedSupport();  fixed.Location = sel_bottom
disp = a.AddDisplacement();   disp.Location = sel_top
disp.DefineBy = LoadDefineBy.Components
disp.ZComponent.Output.DiscreteValues = [Quantity(-155.5, "mm")]   # ★ 直接赋列表！
# X/Y 不设 = Free（径向自由）
a.AnalysisSettings.LargeDeflection = True      # 大变形（压缩量>10-15% 必开）
```
- ⚠️ **位移设值别用 `SetDiscreteValue`**（Free 状态下报 NullReference）——**用「直接赋 DiscreteValues 列表」**。
- **大变形模式**：`a.AnalysisSettings.LargeDeflection = True`。

### ⑦ 求解
```python
a.Solve()      # 同步阻塞（线性 92 秒；大变形 30 分钟+，勿掐）
# 等待 Solution.ObjectState == "Solved"
```

### ⑧ 结果读取 + 存档
```python
sol = a.Solution
d  = sol.AddTotalDeformation()
s  = sol.AddEquivalentStress()
s2 = sol.AddMaximumShearStress()
fr = sol.AddForceReaction();  fr.BoundaryConditionSelection = <FixedSupport对象>
sol.EvaluateAllResults()       # ★ 不 Evaluate 全是 0！
d.Maximum / s.Maximum / s2.Maximum / fr.Total   # 读数（mm / MPa / N）
ExtAPI.DataModel.Project.Save()                 # 里程碑必存档
```
（结果对象若已存在，遍历 `sol.Children` 按类型找回来复用，别重复 Add。）

---

## 三·B、后处理：Post API 直读（2026-10-10 打通 ★★★）

> **目标**：**不开 Post 软件**，直接从结果目录读出任意连接/实体的曲线数据 → CSV
> **工具**：`C:\baidunetdiskdownload\spring_fea\工具\post_api_query.py`（已固化，自动处理环境）

### 配方（三步）

1. **环境变量 `PYTHONNET_RUNTIME=netfx`** —— pythonnet 3 默认 coreclr 加载不了 Ansys 的 .NET Framework 程序集（"命名空间空转"的病根）；工具脚本已内置 subprocess 自重启自动补上（注意：是 subprocess，不是 os.execve——后者传参会出幺蛾子）；
2. **双程序集加载**（都在 `C:\Program Files\ANSYS Inc\v242\Motion\bin`）：
   - `VM.Models.OutputReader`（提供 `PlotParameters`）
   - `VM.Post.API.OutputReader`（提供 `OutputReader`）
3. **名称口径**：
   - **Target = Post 里显示的名字**（如衬套-地1 就叫 `____1____`，**不是** "Fix Joint 1"）；**大小写敏感**
   - **Path = 特征/分量**（如 `Force on Action Marker/X`、`Displacement/X`）

### 用法

```
python 工具\post_api_query.py <结果目录> <Target> <Path1> [Path2 ...] -o out.csv

例（衬套-地1 三分力）：
python 工具\post_api_query.py "…\_v2_coupled_post" "____1____" "Force on Action Marker/X" "Force on Action Marker/Y" "Force on Action Marker/Z" -o bush1.csv
```

### 已核实算例（2026-10-10）

衬套-地1 三分力（501 点）：**X −170~0 / Y −1202~5508 / Z −7807~13363** —— 与 Post 画面逐项一致（其"大曲线 13.5k"↔ Z 分量）。

### 官方资料位置（本地硬盘就有！）

- **手册**：《Postprocessor API for Python.pdf》+ 示例代码 zip + API 教程 → `C:\Program Files\ANSYS Inc\v242\Motion\Document\`
- **参考**：手册附录列了**所有实体类型（Rigid Body/Constraint/Marker/Contact/FE Node…）的 Target/Path 写法全表**

### 坑位（API 专属）

| 症状 | 根因 | 解法 |
|---|---|---|
| `import` 成功但 `dir()` 空 | pythonnet 默认运行时加载不了老式程序集 | `PYTHONNET_RUNTIME=netfx` |
| `cannot import name 'PlotParameters'` | 只加载了 Post.API dll | 补加载 `VM.Models.OutputReader` |
| `EntityNotFoundException: xxx was not found` | Target 名不是"显示名" | 用 Post 里的名字（`____1____` 这种） |
| 空结果（无异常） | Path 名打错/大小写 | 对照手册附录或 Post 图例核对 |

---

## 四、坑位清单（症状 → 根因 → 解法）

| # | 症状 | 根因 | 解法 |
|---|---|---|---|
| 1 | 脚本崩：`'ascii' codec can't decode byte 0` | 服务端 `str()` 中文 .NET 属性 | safe_str + 文件桥（2.2） |
| 2 | `GenerateMesh` 秒返回但 `NotSolved` | 异步提交/未完成 | 等 `IsMeshing` 变 False 再判 |
| 3 | 网格"卡 5%"、"卡在下端面" | 表面三角化慢（BSpline 螺旋）+ 低并行 | 耐心（15-19 分钟）；去特征 + 8 核并行（→9.5 分钟） |
| 4 | 网格调用 168 秒后 `NotSolved` | **没跑完被误判**（真超时线更长） | 慢≠死，勿掐（总原则 1.1） |
| 5 | `mesh.ElementSize = "2 [mm]"` 报 `expected Quantity` | 字符串不行 | `Quantity(2, "mm")` |
| 6 | `DefeatureTolerance` 设不上 | 全局属性只读 | 用 `AutomaticMeshBasedDefeaturing = True` |
| 7 | 方法对象 `UnderDefined` | 缺 Location 作用域 | SelectionManager 选体后赋 `m.Location` |
| 8 | Sweep 了但还是 Tet10 | 螺旋体不可扫掠，引擎回退 | 接受四面体 / 回转体才用 Sweep |
| 9 | 位移设值报 `Object reference not set` | 分量处于 Free（无值槽） | 直接赋 `Output.DiscreteValues = [Quantity(...)]` |
| 10 | 结果读数是 0 | 未求值 | `sol.EvaluateAllResults()` |
| 11 | `ForceReaction.BoundaryCondition` 不存在 | 属性名错 | `fr.BoundaryConditionSelection = <fixed>`；读数 `fr.Total` |
| 12 | 会话卡死/窗口无响应 | 网格任务僵住（UI 假死） | kill → 删锁 → 重启会话 → Open 项目 |
| 13 | `os._exit` 后无输出 | 缓冲未刷 | 退出前 `sys.stdout.flush()` |
| 14 | 对账差 15% | 有效圈 vs 全几何口径 | 报告里说明口径（总原则 1.2） |
| 15 | 结果文件巨大 | ds.dat 139MB / file.rst 294MB | 正常（46 万单元规模）；备份只抄 .mechdb（37MB） |
| 16 | 项目"打开时被锁"（`locked by <user>`） | 强杀会话残留 `<项目>_Mech_Files/.mech_lock`（内容=用户名） | 移走锁文件即解（先备份）；**预防：关会话优先 `mech.exit()`，不强杀** |
| 17 | API 改名/分组后**树 UI 不刷新**（ExpandBranch/Refresh/FullRedraw 全无效） | 独立会话树控件文本缓存 | **重开项目**（重启会话→Open）即正确；数据层不受影响 |
| 18 | 中文 key `in` 判定恒 False（名字核对假失败） | IronPython `unicode in .NET String` 不可靠 | 校验一律 **len + codepoints 逐字符**（数字比对） |
| 19 | Part 名被写成 `u'\u886c\u5957` 字面文本 | **safe_str 的输出（repr 壳）被当内容写回属性** | 写属性用**真 unicode**；脚本里用 `\uXXXX` 转义嵌入（由客户端生成，防手写码点错） |
| 20 | 树里名字还是坏的（明明改过名） | **树显示的是 Body 名**（Part 名不显示）；两层名字要分清 | 改 **Body 名**（`part.Children[0].Name`）+ **重开会话**才刷新显示 |
| 21 | 批量建材料后**所有条目都变成最后一个** | 此环境 `Material.Duplicate()` = **浅引用共享**（多条目共用同一材料定义，改一个=全改） | **禁用批量 Duplicate**；见 #22 |
| 22 | 材料库批量建的正确姿势 | — | **自制 EngineeringData XML + `Model.Materials.Import()`**：复制官方样本（`Samples\General_Materials.xml`）的 Structural Steel 块 ×N + 改 `<Name>` 与 **pa6/pa11/pa12/pa19/pa20** 的 `<Data>`（保留文件尾 Metadata 区）；导入后重开验证 |
| 23 | Open 报 "project is locked by" | 强杀/异常退出残留 `<项目>_Mech_Files/.mech_lock` | 移走锁文件即解；**`exit()` 遇未保存改动会卡对话框**（先处置未保存内容再退） |
| 24 | `CreateSelectionInfo(type, ids)` 报 "takes exactly 1 argument" | 签名是**先建后填** | `sel = CreateSelectionInfo(SelectionTypeEnum.GeometryEntities)` → **`sel.Ids = [ids]`** → 赋给 `j.MobileLocation` |
| 25 | 遍历 `Model.Connections.Children` 找不到/删不掉 Joint | **`AddJoint` 建的 Joint 自动进"新建 ConnectionGroup"**（两层结构） | 遍历要 **两层**（ConnectionGroup → Children）；`Delete()` 倒序删 |
| 26 | 想让 joint 进指定组（组好命名好维护） | `Connections.AddJoint()` 永远自动新建组 | **先 `g = Connections.AddConnectionGroup()` 命名 → `j = g.AddJoint()`**（在组上建即入组）；组可 `Delete()` |
| 27 | 会话"自己没了"（窗口消失/项目打不开） | **启动/连接类脚本用 `os._exit(0)` 强制退出** → Mechanical 子进程被"父死子亡"带走 + **残留 `.mech_lock`** | **此类脚本一律用 `sys.exit(0)`**（正常退出）；善后：移走 `.mech_lock` 重新 Open |

**对地连接（Joint）配方（2026-10-09 实测）**：
```python
from Ansys.Mechanical.DataModel.Enums import JointType, JointScopingType
j = Model.Connections.AddJoint()
j.Name = "..."
j.Type = JointType.Fixed            # Revolute=1 / Spherical=6 / Fixed=0 …
j.ConnectionType = JointScopingType.BodyToGround   # 对地（BodyToBody=0）
sel = ExtAPI.SelectionManager.CreateSelectionInfo(SelectionTypeEnum.GeometryEntities)
sel.Ids = [f.Id for f in <NamedSelection>.Entities]
j.MobileLocation = sel              # 读回 j.MobileBody 验证自动识别
```
- 命名选择按**转义文本**匹配：`"\\u9876\\u80f6" in ns.Name.encode("unicode_escape")`
- 跨多个实体时 `MobileBody` 显示 **"多倍"（Multiple）**——求解若报错则改为单实体或换 Bushing

**衬套单元（Bushing）刚度/阻尼设置配方（2026-10-09 实测 6/6）**：
```python
ws = bushingJoint.BushingWorksheet          # JointBushingWorksheet 对象
# 12 个通道：6 刚度 + 6 阻尼（"上三角矩阵"索引——对角项如下）
ws.SetBushingStiffnessPerUnitX(0, Kx)       # 平动 X
ws.SetBushingStiffnessPerUnitY(1, Ky)       # 平动 Y
ws.SetBushingStiffnessPerUnitZ(2, Kz)       # 平动 Z
ws.SetBushingStiffnessPerThetaUnitX(3, Krx) # 转动 θX（偏摆）
ws.SetBushingStiffnessPerThetaUnitY(4, Kry) # 转动 θY（偏摆）
ws.SetBushingStiffnessPerThetaUnitZ(5, Krz) # 转动 θZ（绕轴扭转）
# 阻尼同理：SetBushingDampingPerUnitX/Y/Z、SetBushingDampingPerThetaUnitX/Y/Z（同索引）
# Get 系列用同索引读回（Set 后立即 Get(索引) 验证）
```
- ⚠️ **索引 = 上三角行号**：X 列 0-5｜Y 列 1-5｜Z 列 2-5（传错 range 报 ValueError）
- 刚度单位 N/mm；转动刚度 N·mm/度；方向由 `ElementCoordinateSystem` 定义（默认程序控制）

**名字两层（2026-10-08 血泪教训）**：`Part.Name`=组织名（树里**不显示**）｜`Body.Name`=`part.Children[0].Name`（树里**显示的就是它**）。
修复壳文本的标准套路：**从壳无损解码还原 → `\uXXXX` 转义嵌入 → 赋值 → 回读 len+codepoints 校验**（拿不准就先只读诊断再写）。

**树组织（分组）补充（2026-10-08 悬架实战）**：
- `Model.AddTreeGroupingFolder([对象])` = **树分组文件夹**（= UI 右键 Group 同款；**非几何归并**——Mechanical 无 Form New Part，那是 DM 专属）
- `folder.Suppressed = True` → **自动传导到全部成员**（"整组压缩"一步完成）✓
- `Tree.Ungroup(folder)` 可逆；`Tree.CanAddTreeGroupingFolder(obj)` 预检；`Tree.TryGetFolder()` v242 有 bug（恒 NullRef）勿用
- 分组后 **`Model.Geometry.Children` 仍返回全部 Part**（folder 是"组织层"，不改几何归属）——成员清单看 `folder.Children`

---

## 五、零件预案（本项目路线图）

> 工况来源：`01_设计计算`（01 节载荷 + 08 节校核汇总）

| 零件 | 几何特点 | 网格策略 | 工况（待定） | 状态 |
|---|---|---|---|---|
| **螺旋弹簧** | BSpline 螺旋体（不可扫掠） | 四面体 + 去特征 + 8 核；46 万单元 ~9.5 分钟 | 压缩到装配态（-155.5mm） | **✅ 线性版完成**；大变形 99% 不收敛（16GB 内存 out-of-core）已搁置 |
| **减振器壳** | **回转体**（筒身+支架） | **优先试 Sweep/扫掠**（回转体是扫掠甜点区）；失败退四面体 | 侧向力、弯矩（07 节） | 待开始 |
| **下摆臂** | 冲压焊接板件（两片对扣箱形） | 四面体偏细（板件薄壁注意单元质量）；考虑壳单元方案 | 静载/侧弯（06 节，手算 147.7MPa） | 待开始（**交付重点**） |
| **转向节** | 复杂铸锻件（有锥孔/耳板） | 四面体 + 必要加密；去特征必开 | 复合载荷 | 待开始 |
| 副车架/横拉杆 | 沿用件 | 按需 | 按需 | 非交付 |

**建议顺序**：弹簧（收尾）→ **下摆臂**（交付重点 + 手算粗 + FEA 价值最大）→ 减振器壳 → 转向节。

---

## 六、对账方法论（报告素材模板）

### 6.1 弹簧对账汇总表（样例，可直接入报告）

| 量 | 理论（01 文档） | FEA（线性） | FEA（大变形） | 差异归因 |
|---|---|---|---|---|
| 反力 @装配态 | 4.96 kN（n=6 口径） | 4.37 kN | 待回填 | 有效圈口径（端圈参与，等效 ~7.1 圈） |
| τmax | 701 MPa | 1157.5 MPa | 待回填 | 端部效应 + 大变形（46% 压缩） |
| 变形 | 155.5（给定） | 157.3 mm | 待回填 | — |

### 6.2 图形清单（出报告用）
- 网格图（统计：单元数/质量）
- 最大剪应力云图（热点位置标注）
- 位移云图、力反应表格

---

## 附录 A：文件与目录索引

| 内容 | 路径 |
|---|---|
| 可见会话启动脚本 | `C:\baidunetdiskdownload\spring_fea\start_visible.py` |
| 弹簧项目（主） | `C:\Users\dth15\Desktop\ANSYS\spring.mechdb` |
| 弹簧 v1 备份（46 万四面体版） | `C:\Users\dth15\Desktop\ANSYS\spring_v1_tet46w.mechdb` |
| 求解工作目录（ds.dat/solve.out/file.err） | `…\ANSYS\spring_Mech_Files\StaticStructural\` |
| 脚本与日志归档 | `C:\baidunetdiskdownload\spring_fea\` |
| **Post API 手册+示例（官方）** | `C:\Program Files\ANSYS Inc\v242\Motion\Document\`（Postprocessor API for Python.pdf / .zip） |
| **通用取数工具（API 直读）** | `…\spring_fea\工具\post_api_query.py`（pythonnet 装在 default venv） |
| **5s 刚柔耦合版结果（最新）** | `…\spring_fea\_v2_coupled_run\`（求解产物）/ `_v2_coupled_post\`（Post 可读版） |
| 设计计算文档 | `…\机械本科的课程设计\3_卡罗拉前悬架设计\01_设计计算\` |

## 附录 B：常用命令速查

```bash
# 查机械进程
tasklist | grep -i ansyswbu

# 杀会话（防误杀：先看标题）
taskkill /PID <pid> /F

# 读求解日志
grep -E "Number of|Elapsed" solve.out

# Post API 直读（不开软件取曲线数据；工具自带 netfx 环境处理）
C:\Users\dth15\.workbuddy\binaries\python\envs\default\Scripts\python.exe \
  C:\baidunetdiskdownload\spring_fea\工具\post_api_query.py <结果目录> <Target> <Path...> -o out.csv
```

```python
# 一切脚本的骨架：connect → 文件桥脚本 → 读 log → os._exit(0)
```

---

*本工作流随项目推进持续更新。每完成一个零件，回填「零件预案」与「对账表」。*
