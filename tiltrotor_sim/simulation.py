"""离散闭环：参考 -> 控制 -> 分配 -> 实际执行器 -> 刚体 -> 反馈。"""
import numpy as np
from scipy.spatial.transform import Rotation
from model import rotation,thrust_to_throttle,motor_step,wrench_from_actuators,integrate
from allocation import Allocator
from control import Controller
from reference import reference


def simulate(c,scenario='combined',zero_start=False,reference_fn=None):
    if scenario not in ('hover','position','attitude','combined','circle','fixed'):
        raise ValueError('未知工况')
    allocator=Allocator(c);controller=Controller(c)
    state=np.zeros(13);state[9]=1
    angles=np.zeros((4,2))
    u=np.zeros(4) if zero_start else np.full(4,thrust_to_throttle(c['mass']*c['gravity']/4,c))
    names=('time','state','reference_position','reference_rpy_deg','rpy_deg','reference_velocity',
           'reference_omega','desired_wrench','achievable_wrench','actual_wrench','angles_deg',
           'throttle_command','throttle_actual','saturated','allocation_residual','tracking_residual',
           'position_error','attitude_error_deg','integral')
    logs={key:[] for key in names}
    steps=int(np.ceil(c['duration']/c['dt']))
    for k in range(steps+1):
        t=min(k*c['dt'],c['duration'])
        ref=reference(t,c,scenario) if reference_fn is None else reference_fn(t)
        desired=controller.command(state,ref)
        angles,cmd,saturated,achievable=allocator.allocate(desired,angles)
        # 舵机瞬时跟随；电机当前状态在本时刻记录，随后演化至下一采样时刻。
        if c['motor_tau']==0:
            u=cmd.copy()
        actual=wrench_from_actuators(angles,u,c)
        R=rotation(state[6:10])
        err=np.rad2deg(Rotation.from_matrix(ref['R'].T@R).magnitude())
        values=(t,state.copy(),ref['p'],Rotation.from_matrix(ref['R']).as_euler('xyz',degrees=True),
                Rotation.from_matrix(R).as_euler('xyz',degrees=True),ref['v'],ref['w'],
                desired,achievable,actual,np.rad2deg(angles),cmd,u.copy(),saturated,
                desired-achievable,desired-actual,state[:3]-ref['p'],err,controller.integral.copy())
        for name,value in zip(names,values):
            logs[name].append(value)
        if k==steps:
            break
        dt=min(c['dt'],c['duration']-t)
        controller.update_integral(state,ref,desired,achievable,saturated,dt)
        # 使用周期中点的实际油门重建 wrench，降低执行器离散引入的误差。
        mid_u=motor_step(u,cmd,dt/2,c['motor_tau'])
        state=integrate(state,wrench_from_actuators(angles,mid_u,c),dt,c)
        u=motor_step(u,cmd,dt,c['motor_tau'])
    return {name:np.asarray(values) for name,values in logs.items()}


def metrics(log):
    tail=log['time']>=max(0,log['time'][-1]-5)
    error=np.linalg.norm(log['position_error'],axis=1)
    return {
        'duration_s':float(log['time'][-1]),
        'tail_max_position_error_m':float(np.max(error[tail])),
        'tail_rms_position_error_m':float(np.sqrt(np.mean(error[tail]**2))),
        'tail_max_attitude_error_deg':float(np.max(log['attitude_error_deg'][tail])),
        'max_allocation_force_residual_n':float(np.max(np.linalg.norm(log['allocation_residual'][:,:3],axis=1))),
        'max_allocation_torque_residual_nm':float(np.max(np.linalg.norm(log['allocation_residual'][:,3:],axis=1))),
        'saturated_sample_fraction':float(np.mean(np.any(log['saturated'],axis=1))),
        'max_quaternion_norm_error':float(np.max(np.abs(np.linalg.norm(log['state'][:,6:10],axis=1)-1))),
    }
