# 双轴倾转四旋翼闭环模型

这是一个用于理解控制流程、修改参数和验证算法的 Python 仿真。采用用户给定的 6 kg 机体和实测单桨油门查表；每个模块有两个倾转角、同速反转双桨，因此共有 **8 个角度和 4 个模块油门**。没有实测 rpm 数据，不将油门冒充转速。

## 在 VS Code 中运行

直接用 VS Code **打开 `tiltrotor_sim` 文件夹**。当前机器已创建 `.venv` 并安装依赖，终端运行：

```powershell
.\.venv\Scripts\python.exe main.py --scenario combined
```

或者选择项目虚拟环境解释器，按 F5 使用“运行双轴倾转仿真”。需要 VS Code 的 Python 与 Python Debugger 扩展；终端运行不依赖调试扩展。

迁移到其他电脑后，安装 Python 3.12，再运行：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
.\.venv\Scripts\python.exe main.py
```

`requirements-lock.txt` 记录本次验证环境，`requirements.txt` 提供允许的依赖范围。无需激活虚拟环境，也无需改 PowerShell 执行策略。每次运行会覆盖同名输出目录；需保留结果时使用 `--output`。

## 像 MATLAB 一样缩放曲线与读取数值

新增 `--show` 后，仿真完成会打开四个 Matplotlib 交互曲线窗口和一个可旋转的三维动画窗口，并照常保存 PNG、CSV、GIF 和统计数据。Windows 标准 Python 自带的 tkinter 即可支持，无需新增依赖。

```powershell
# 重新运行仿真，打开交互图窗
.\.venv\Scripts\python.exe main.py --scenario combined --show
# 使用自己的位置、姿态目标
.\.venv\Scripts\python.exe main.py --scenario fixed --target-position 1 0 -1 --target-rpy 10 -8 20 --show --output outputs/my_case
# 直接打开已保存的结果，不必重新仿真；也可传入 flight.csv 的路径
.\.venv\Scripts\python.exe view_results.py outputs/combined
```

窗口可以最大化。底部工具栏的 **Zoom（放大镜）** 用于框选放大，**Pan（十字箭头）** 用于拖动平移，**Home（房子）** 恢复初始全局范围，前进/后退箭头切换浏览范围。各窗口内的时间轴联动，纵轴可分别缩放；保存按钮可导出当前视图。所有图窗关闭后，终端命令才结束。

再次点击当前 Zoom/Pan 按钮退出工具模式后：**左键点击曲线**显示最近时间采样点的曲线名称、时间和原始数值；**右键点击子图**可输入 `xmin xmax ymin ymax` 四个数，精确设置该子图范围，支持科学计数法。例如在力分配残差子图输入 `6 20 -2e-14 2e-14`，可检查 6～20 s 的浮点舍入波动。读数使用原始采样数据，不作平滑，也不把像素位置当成仿真数值。VS Code 的运行调试列表另提供“运行仿真并打开交互曲线”和“打开已有 combined 交互曲线”。

分配残差是 `desired-achievable`，表示分配及静态推力限幅后的误差。若纵轴标注 `1e-14` N / `1e-15` N·m，密集波动通常属于浮点舍入量级，不代表实际推力发生同等视觉幅度的振荡。为避免近零数据自动撑满整张图，当最大绝对分配残差小于 `1e-9` 时，初始纵轴范围为 ±`1e-9`，标题显示原始峰值；超过此值时正常自动缩放。该规则只调整显示范围，CSV、曲线数值、统计和动力学均保留原始结果。实际执行器输出需看 `wrench` 图中的 `actual`，其中另显示 `desired` 和 `achievable` 供比较。

## 可旋转的三维动画

GIF 保存的是固定视角的二维帧，不能在播放时旋转空间。使用三维交互窗口，可以在任意时刻从不同角度检查机体与四个实际推力箭头。所有六种工况都支持。

```powershell
# 新仿真：保存 GIF，并打开交互曲线与可旋转的三维动画
.\.venv\Scripts\python.exe main.py --scenario attitude --target-rpy 10 0 30 --show
# 已有结果：只打开三维动画，不重新仿真，也不重新导出 GIF
.\.venv\Scripts\python.exe view_results.py outputs/attitude --3d
# 本项目已生成的示例
.\.venv\Scripts\python.exe view_results.py outputs/animation_examples/combined --3d
# 如需快速查看新仿真，可跳过 GIF 导出
.\.venv\Scripts\python.exe main.py --scenario circle --show --no-animate
```

在三维窗口内，退出工具栏的 Zoom/Pan 模式后，**左键拖动场景旋转，中键拖动平移，滚轮或右键拖动缩放**。拖动场景或滚动时自动暂停。**Play/Pause** 和空格键控制播放/暂停；**Time 滑块**定位到原始采样时刻并暂停，左右方向键可前后移动 0.1 s。**Top** 切到俯视，**Side** 从北向观察，**Reset view** 恢复初始视角与全局范围。播放不会重置鼠标选择的视角，到末尾自动暂停，再按 Play 从头播放。

播放器复用 GIF 的实际四元数、实际倾转角和实际油门，显示模块编号、姿态角与推力大小，不重新计算动力学。历史结果的 `flight.csv` 与同目录的 `parameters_used.json` 必须一起保留，后者用于恢复本次运行的尺寸和推力标定。播放器使用计时器按经过时间选择采样点；绘图较慢时可能跳过部分帧，时间滑块仍可定位所有原始采样点。

```powershell
# 平滑地移动到北 1 m、东 0.6 m、高度 0.8 m，同时改变姿态
.\.venv\Scripts\python.exe main.py --scenario combined
# 固定六维目标从 t=0 生效；姿态角单位为度，地向负值表示升高
.\.venv\Scripts\python.exe main.py --scenario fixed --target-position 1 0 -1 --target-rpy 10 -8 20
# 圆轨迹（所有工况默认生成三维动画）
.\.venv\Scripts\python.exe main.py --scenario circle
# 可选对照
.\.venv\Scripts\python.exe main.py --ideal-motor --output outputs/ideal
.\.venv\Scripts\python.exe main.py --nullspace --output outputs/nullspace
.\.venv\Scripts\python.exe main.py --zero-start --output outputs/zero_start
```

工况为 `hover`（原点悬停）、`position`（平移）、`attitude`（定点转姿态）、`combined`（同时变化）、`circle`（渐入圆轨迹）、`fixed`（不平滑的固定目标）。除 `fixed` 外，点到点指令在 1～6 s 之间进行五次多项式平滑。默认时长 20 s，步长 0.002 s，可用 `--duration`、`--dt` 修改。`hover` 始终保持原点和零姿态；定制固定悬停位置应使用 `fixed`。

## 闭环与文件职责

```mermaid
flowchart LR
  A[位置和姿态参考] --> B[位置 PID 与 SO3 姿态控制]
  B --> C[机体系六维期望力与力矩]
  C --> D[最小范数分配与倾转角反解]
  D --> E[8 个角度和 4 个油门]
  E --> F[电机一阶响应及推力查表]
  F --> G[实际三轴力和三轴力矩]
  G --> H[刚体动力学与四元数积分]
  H -->|位置 速度 姿态 角速度| B
```

| 文件 | 职责与主要接口 |
|---|---|
| `config.json` | 实机数据、控制增益、限幅、步长和目标值 |
| `model.py` | 坐标工具、查表、执行器正向模型、RK4 动力学 |
| `reference.py` | `reference(t,c,scenario)` 返回参考状态及解析导数 |
| `control.py` | `Controller.command(state,ref)` 返回 6 维期望 wrench |
| `allocation.py` | `allocate(wrench,previous)` 返回角度、油门、饱和标记与静态可实现 wrench |
| `simulation.py` | `simulate(...)` 连接完整闭环并记录数组日志 |
| `reporting.py` | CSV、曲线、交互图窗和三维 GIF |
| `main.py` | 命令行入口 |
| `tests/test_model.py`、`validate.py` | 代数测试、完整闭环验收及步长收敛 |

状态 `state` 长度为 13，顺序为 `p_NED[3], v_NED[3], q_xyzw[4], omega_FRD[3]`。参考字典包含 `p,v,a,R,w,wdot`，其中角速度及其导数位于期望机体系。自定义轨迹可修改 `reference.py`，或者调用 `simulate(..., reference_fn=函数)`。不要将欧拉角导数直接当成机体角速度。

## 坐标、单位与编号

机体系是 **FRD：x 前、y 右、z 下**，地理系是 **NED：北、东、地**，均为右手系。`R` 从机体系映射到地理系；机体水平朝北时 `R=I`。位置以 m 表示，地向 `D` 增大为下降，高度 `h=-D`。角速度是机体系 rad/s，力是 N，力矩是 N·m。

姿态输入为滚转、俯仰、偏航（度），使用 `Rz(yaw) Ry(pitch) Rx(roll)`。正滚转使右侧下沉，正俯仰使机头抬起，正偏航从北转向东。内部不积分欧拉角；曲线中的欧拉角仅用于显示，接近 ±90° 俯仰时显示可能不唯一，姿态测地误差仍有效。标准 SO(3) 误差在恰好 180° 处存在不期望平衡点，本模型不宣称该点必然收敛。

旋翼编号：1 前右 `(l,b,0)`，2 后右 `(-l,b,0)`，3 后左 `(-l,-b,0)`，4 前左 `(l,-b,0)`。`l=0.390 m`，`b=0.4035 m`，均以重心为原点。惯量为用户提供的 `diag(0.0215,0.116,0.157)` kg·m²。

`angles` 数组形状为 `(4,2)`，每行为 `[alpha,beta]`。两角是数学倾转约定：先绕机体 y 轴转 alpha，再绕旋转后的 x 轴转 beta。未经硬件标定，不等同于具体舵机的编码器正负号或机械零点。

## 方程与执行时序

位置误差为 `ep=p-pd`、`ev=v-vd`，控制力：

```text
F_N = -Kp*ep - Kd*ev - Ki*integral(ep) - m*[0,0,g] + m*ad
F_B = R.T @ F_N
```

位置增益量纲分别为 N/m、N·s/m、N/(m·s)；积分上限单位为 m·s。积分始终限幅，并根据静态分配残差冻结继续加剧饱和的分量；不会把电机暂态滞后误判成幅值饱和。

姿态使用论文式 (10)～(11)：

```text
Q = R.T @ Rd
eR = 0.5 * vee(Q.T-Q)
ew = omega-Q@omega_d
tau = -KR*eR-Kw*ew + omega×(J@omega)
      -J@(omega×(Q@omega_d)-Q@omega_dot_d)
```

分配将 `[F_B,tau_B]` 映射为四个三维推力：`t=pinv(M)@wrench`，其中每个模块的矩阵块为 `[I; hat(r_i)]`。这是论文式 (15)/(44) 的最小范数推力分配。`analytic()` 提供其解析等价式并用于交叉验证；它最小化推力向量平方和，不把实测功耗直接当作该目标。

在 FRD 下，零倾转角推力朝上：

```text
d(alpha,beta) = [-sin(alpha)*cos(beta), sin(beta), -cos(alpha)*cos(beta)]
t_i = 2*T_single(u_i)*d(alpha_i,beta_i)
F_B = sum(t_i)
tau_B = sum(r_i × t_i)
```

两组角度解为 `(atan2(-dx,-dz), asin(dy))` 和 `(alpha+pi, pi-beta)`，分别加入可行的 2π 周期，联合选择距离当前角度最近的解。零推力保持原角度；在推力沿 ±y 轴时保留自由的 alpha。跨越奇异点附近时仍可能产生很大的角度变化，开启零空间修正可作为对照，不保证所有工况的机械可行性。

用户表格的克力按 `9.8*0.001` 换算为 N；`3.218*9.8` 的结果是 **31.5364 N，而非 kg**。单模块推力按两桨之和计算，悬停单桨推力 7.35 N，油门约 0.40785。反向查表用于分配器，正向查表用于执行机构，两者均为分段线性插值。

实际油门满足 `du/dt=(u_cmd-u)/0.2`，采用指数精确离散更新。每周期先根据当前状态计算指令，再使用周期中点实际油门重建机体系力与力矩，保持该 wrench 进行 RK4 刚体积分，并更新末端油门。舵机立即到达指令角度。日志记录采样时刻的当前实际油门，不能直接把期望 wrench 作为实际动力学输入。

```text
pdot = v
vdot = [0,0,g] + R@F_B/m
omega_dot = inv(J)@(tau_B-omega×(J@omega))
qdot = 0.5 * q ⊗ [omega,0]       # 存储顺序 xyzw
```

默认初态位置和速度为零、姿态水平朝北、角速度为零，电机配平悬停。`--zero-start` 将初始油门改为零，允许自由下落后恢复；没有地面接触模型。

## 论文对应与两处符号修正

参考用户提供的 **MorphQuad: Morphable Quadrotor for Superhuman Maneuverability, Manipulation, and Resiliency**：动力学见第 32～33 页，控制见第 34 页，分配见第 36～38 页，零空间基底见第 50 页，最小范数等价证明见第 55 页。

1. 原文式 (17) 第二分支 beta 的符号与式 (3) 正向关系不一致。本实现使用 `beta_2=pi-beta_1`，保证正向回代得到相同推力。
2. 原文式 (22) 中 `N_M.T` 最后一行第 5 项为 `-1`，与该行第 2 项相加产生非零 y 合力，违反 `M@N=0`。本实现将第 5 项改为 `+1`，保留其余基底与对应系数，并通过代数测试验证。

可选零空间修正使用 `t=pinv(M)@w + scale*N@c`。论文基底的坐标用 `S=diag(1,-1,-1)` 旋转到 FRD，再按 `[2,3,4,1]` 转换模块编号；式 (19) 的系数先在原文坐标计算，避免在换基后错误沿用系数。`nullspace_scale_n=1.0` 是本模型显式指定的牛顿幅度，论文未给出其清晰物理标定。它默认关闭，会增加内部推力抵消；饱和后不能再保证实际 wrench 不变。

## 输出、测试与局限

每次运行产生 `flight.csv`（完整状态与执行器日志）、`parameters_used.json`（实际使用参数）、`metrics.json`、四张 PNG：`tracking`、`wrench`、`actuators`、`diagnostics`，以及 **默认生成的 `flight.gif`**。`hover`、`position`、`attitude`、`combined`、`circle`、`fixed` 六种工况和理想电机、零油门启动、零空间修正等对照均使用同一个动画输出流程；无需额外添加 `--animate`，原有 `--animate` 命令仍可使用。只需数据和曲线时可添加 `--no-animate`。

动画使用 N/E/高度坐标，实际四元数决定机体姿态，红线表示机头，橙色箭头按 **0.035 m/N** 表示各模块的实际推力（包含电机惯性），不是下洗气流方向。模块编号为 **1 前右、2 后右、3 后左、4 前左**。动画底部显示实际滚转/俯仰/偏航角（度）及四个模块的推力大小（N）；坐标范围包含机体与推力箭头端点。每段动画最多 240 帧，以 10 fps 播放，通过画面时间标注读取实际仿真时刻，播放并非严格实时。

```powershell
# 单独观察姿态及推力方向，自动生成 outputs/attitude/flight.gif
.\.venv\Scripts\python.exe main.py --scenario attitude --target-rpy 10 0 30
# 六种工况分别生成完整结果及 GIF
foreach ($case in 'hover','position','attitude','combined','circle','fixed') {
    .\.venv\Scripts\python.exe main.py --scenario $case
}
# 快速计算时跳过 GIF
.\.venv\Scripts\python.exe main.py --scenario combined --no-animate
```

CSV 中 `achievable_wrench` 为考虑推力限幅但不含电机滞后的静态可实现值；`actual_wrench` 为包含滞后的实际值；`allocation_residual=desired-achievable`，`tracking_residual=desired-actual`。所有 wrench 均在机体系。8 个倾转角保留连续周期，不强制包裹到 ±180°。

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe validate.py
```

验收检查包括坐标正负号、悬停配平、推力表、0.2 s 电机响应、最小范数分配、零空间条件、随机方向角度回代、周期连续性、饱和抗积分、六种闭环工况、步长减半、理想电机、零空间增强、零油门启动和饱和恢复。完整验收写入 `outputs/validation.json`；点到点工况末 5 s 的最大位置误差要求小于 2 cm、姿态测地误差小于 1°。

本次交付验证：5 项单元测试全部通过，完整闭环验收全部通过。默认增益为位置 `Kp=[12,12,12]`、`Kd=[18,18,18]`、`Ki=[3,3,3]`，已针对 0.2 s 电机惯性检查。代表结果如下（20 s 仿真，统计末 5 s 最大位置误差）：

| 工况 | 最大位置误差 |
|---|---:|
| 平滑位置与姿态同步变化 | 0.298 mm |
| 固定六维目标阶跃 | 1.989 mm |
| 零油门启动后跟踪 | 1.104 mm |
| 短时超限指令后的饱和恢复 | 4.166 mm |

步长从 0.002 s 减半到 0.001 s，代表轨迹全过程最大位置差为 0.189 mm，最大姿态差为 0.000494°。修改参数后请重新运行验收，不应沿用这里的数值。

这是已知精确状态、理想舵机、固定惯量的简化模型。当前油门限制采用逐模块截断，并非约束最优再分配；极端指令可能无法达到。没有标定同轴效率、推力方向气动损失、舵机速率、外部风力、结构变形或不等速反扭矩。小仿真误差不能解释为实机精度或全姿态稳定性证明。
