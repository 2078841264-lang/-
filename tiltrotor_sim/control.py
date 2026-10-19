"""位置 PID 与 SO(3) 几何姿态控制；增益集中于 config.json。"""
import numpy as np
from model import rotation,vee


class Controller:
    def __init__(self,c):
        self.c=c
        self.integral=np.zeros(3)

    def command(self,state,ref):
        c=self.c
        R=rotation(state[6:10])
        w=state[10:13]
        ep=state[:3]-ref['p']
        ev=state[3:6]-ref['v']
        force_N=(-c['position_kp']*ep-c['position_kd']*ev-c['position_ki']*self.integral
                 -c['mass']*np.array([0,0,c['gravity']])+c['mass']*ref['a'])
        Q=R.T@ref['R']
        er=0.5*vee(Q.T-Q)
        ew=w-Q@ref['w']
        torque=(-c['attitude_kp']*er-c['attitude_kd']*ew+np.cross(w,c['inertia']@w)
                -c['inertia']@(np.cross(w,Q@ref['w'])-Q@ref['wdot']))
        return np.r_[R.T@force_N,torque]

    def update_integral(self,state,ref,desired,achievable,saturated,dt):
        ep=state[:3]-ref['p']
        # 仅依据幅值饱和残差抗积分饱和；电机暂态滞后不误判为幅值饱和。
        deficit_N=rotation(state[6:10])@(desired[:3]-achievable[:3])
        blocked=np.any(saturated)&((-self.c['position_ki']*ep)*deficit_N > 1e-10)
        self.integral=np.clip(self.integral+np.where(blocked,0,ep)*dt,
                              -self.c['integral_limit'],self.c['integral_limit'])
