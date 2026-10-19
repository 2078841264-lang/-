"""参数、坐标工具和刚体动力学。所有运算采用 FRD/NED 右手坐标系。"""
import json
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation


def load_config(path=None):
    with open(path or Path(__file__).with_name('config.json'), encoding='utf-8') as f:
        c = json.load(f)
    for key in ('inertia', 'throttle_table', 'single_thrust_grams', 'single_torque_nm',
                'position_kp', 'position_kd', 'position_ki', 'integral_limit',
                'attitude_kp', 'attitude_kd', 'target_position_ned', 'target_rpy_deg'):
        c[key] = np.asarray(c[key], dtype=float)
    l, b = c['half_length'], c['half_width']
    c['arms'] = np.array([[l,b,0],[-l,b,0],[-l,-b,0],[l,-b,0]])
    # 用户数据使用 9.8 将克力转为 N，不受仿真重力配置变化影响。
    c['thrust_table'] = c['single_thrust_grams'] * 0.001 * 9.8
    c['J_inv'] = np.linalg.inv(c['inertia'])
    if min(c['mass'], l, b, c['dt'], c['duration'], c['servo_limit_deg']) <= 0:
        raise ValueError('质量、尺寸、步长、时长与舵机范围必须为正')
    if c['motor_tau'] < 0 or c['nullspace_scale_n'] < 0:
        raise ValueError('时间常数和零空间幅度不能为负')
    if not np.allclose(c['inertia'], c['inertia'].T) or np.min(np.linalg.eigvalsh(c['inertia'])) <= 0:
        raise ValueError('惯量必须对称正定')
    if not (len(c['throttle_table']) == len(c['thrust_table']) == len(c['single_torque_nm'])):
        raise ValueError('插值表长度不一致')
    if not (np.all(np.diff(c['throttle_table']) > 0) and np.all(np.diff(c['thrust_table']) > 0)):
        raise ValueError('油门和推力表必须严格递增')
    if c['throttle_table'][0] != 0 or c['throttle_table'][-1] != 1 or c['thrust_table'][0] != 0:
        raise ValueError('插值表必须覆盖零推力及 [0,1] 油门')
    return c


def hat(v):
    x,y,z = v
    return np.array([[0,-z,y],[z,0,-x],[-y,x,0]])


def vee(a):
    return np.array([a[2,1], a[0,2], a[1,0]])


def rpy_matrix(rpy):
    return Rotation.from_euler('xyz', rpy).as_matrix()


def rotation(q):
    # 四元数存储顺序为 [qx,qy,qz,qw]，表示机体系到 NED。
    return Rotation.from_quat(q).as_matrix()


def directions(angles):
    a, b = np.asarray(angles).T
    return np.column_stack((-np.sin(a)*np.cos(b), np.sin(b), -np.cos(a)*np.cos(b)))


def module_thrust(u, c):
    return 2*np.interp(np.clip(u,0,1), c['throttle_table'], c['thrust_table'])


def thrust_to_throttle(force, c):
    return np.interp(np.maximum(force,0)/2, c['thrust_table'], c['throttle_table'])


def wrench_from_actuators(angles, u, c):
    thrust = directions(angles)*module_thrust(u,c)[:,None]
    return np.r_[thrust.sum(axis=0), np.cross(c['arms'],thrust).sum(axis=0)]


def motor_step(u, cmd, dt, tau):
    return np.clip(cmd if tau == 0 else u + (-np.expm1(-dt/tau))*(cmd-u),0,1)


def derivative(state, wrench, c):
    # 状态为 [p_NED(3), v_NED(3), q_xyzw(4), omega_FRD(3)]。
    v,q,w = state[3:6], state[6:10], state[10:13]
    qv,qw = q[:3],q[3]
    qdot = 0.5*np.r_[qw*w+np.cross(qv,w), -qv@w]
    acc = np.array([0,0,c['gravity']])+rotation(q)@wrench[:3]/c['mass']
    wdot = c['J_inv']@(wrench[3:]-np.cross(w,c['inertia']@w))
    return np.r_[v,acc,qdot,wdot]


def integrate(state, wrench, dt, c):
    """一个控制周期内保持机体系实际 wrench，RK4 积分刚体状态。"""
    k1 = derivative(state,wrench,c)
    k2 = derivative(state+dt*k1/2,wrench,c)
    k3 = derivative(state+dt*k2/2,wrench,c)
    k4 = derivative(state+dt*k3,wrench,c)
    result = state+dt*(k1+2*k2+2*k3+k4)/6
    result[6:10] /= np.linalg.norm(result[6:10])
    if not np.all(np.isfinite(result)):
        raise FloatingPointError('动力学出现非有限值，请检查增益和步长')
    return result
