"""论文式 (15)/(18) 的推力分配及 FRD 下的双轴角度反解。"""
import numpy as np
from model import hat, directions, thrust_to_throttle, wrench_from_actuators


class Allocator:
    def __init__(self, c):
        self.c = c
        self.M = np.vstack((np.tile(np.eye(3),(1,4)),np.hstack([hat(r) for r in c['arms']])))
        self.pinv = np.linalg.pinv(self.M)
        l,b = c['half_length'],c['half_width']
        # 论文式 (22)，基底不能随意替换为 SVD 基底后仍沿用式 (19) 的系数。
        paper_N = np.array([
            [0,0,-1, 0,0,1, 0,0,-1, 0,0,1],
            [-l/b,-1,0, l/b,0,0, 0,0,0, 0,1,0],
            [-1,0,0, 0,0,0, 0,0,0, 1,0,0],
            [-l/b,-1,0, l/b,0,0, 0,1,0, 0,0,0],
            [0,0,0, -1,0,0, 1,0,0, 0,0,0],
            # 原文最后一行第 5 项为 -1，与零合力矛盾；改为 +1 满足 M N=0。
            [0,-1,0, 0,1,0, 0,0,0, 0,0,0]],dtype=float).T
        # 论文 x前/y左/z上 -> FRD：S=diag(1,-1,-1)。编号变为 [2,3,4,1]。
        self.S = np.diag([1,-1,-1])
        # 对每个力都进行S变换
        self.N = np.vstack([self.S@paper_N[3*i:3*i+3] for i in [1,2,3,0]])
        if not np.allclose(self.M@self.N,0,atol=1e-12):
            raise ValueError('零空间基底坐标或编号转换错误')

    def analytic(self, wrench):
        """论文式 (15) 的坐标无关写法，供解析/伪逆交叉验证。"""
        r = self.c['arms']
        l,b = self.c['half_length'],self.c['half_width']
        mu = wrench[3:]/(4*np.array([b*b,l*l,l*l+b*b]))
        #  对于当前对称矩形构型，这个解析解与伪逆最小范数解一致
        return wrench[:3]/4+np.cross(np.broadcast_to(mu,r.shape),r)

    def vectors(self, wrench):
        # 进行零空间修正
        thrust = self.pinv@wrench
        if self.c['nullspace_enabled'] and np.linalg.norm(wrench[:3]) > 1e-12:
            f = self.S@wrench[:3]/np.linalg.norm(wrench[:3])
            coeff = np.zeros(6)
            coeff[[0,2,4]] = f[1]
            if f[0] > 0:
                coeff[1],coeff[3] = -f[0],f[0]
            else:
                coeff[5] = -f[0]
            thrust += self.c['nullspace_scale_n']*(self.N@coeff)
        return thrust.reshape(4,3)

    def inverse_angles(self, vector, previous):
        norm = np.linalg.norm(vector)
        if norm < 1e-12:
            return previous.copy()
        # 反解推力角度
        d = vector/norm
        beta = np.arcsin(np.clip(d[1],-1,1))
        alpha = previous[0] if np.hypot(d[0],d[2]) < 1e-12 else np.arctan2(-d[0],-d[2])
        limit = np.deg2rad(self.c['servo_limit_deg'])
        candidates = []
        for base in (np.array([alpha,beta]),np.array([alpha+np.pi,np.pi-beta])):
            # 每组解中的两个角度可分别加 2π，先找各自最近的可行周期。
            low = np.ceil((-limit-base)/(2*np.pi))
            high = np.floor((limit-base)/(2*np.pi))
            if np.all(low <= high):
                turns = np.clip(np.rint((previous-base)/(2*np.pi)),low,high)
                candidates.append(base+2*np.pi*turns)
        if not candidates:
            raise ValueError('舵机角度范围不足以实现推力方向')
        return min(candidates,key=lambda a: np.sum((a-previous)**2))

    def allocate(self, wrench, previous):
        thrust = self.vectors(wrench)
        angles = np.array([self.inverse_angles(t,p) for t,p in zip(thrust,previous)])
        magnitudes = np.linalg.norm(thrust,axis=1)
        throttle = thrust_to_throttle(magnitudes,self.c)
        saturated = magnitudes > 2*self.c['thrust_table'][-1]+1e-10
        achievable = wrench_from_actuators(angles,throttle,self.c)
        return angles,throttle,saturated,achievable
