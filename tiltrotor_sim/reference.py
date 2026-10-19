"""参考轨迹接口：返回 p/v/a（NED）、R、w/wdot（期望机体系）。"""
import numpy as np
from scipy.spatial.transform import Rotation
from model import rpy_matrix


def blend(t,start=1.0,duration=5.0):
    s=np.clip((t-start)/duration,0,1)
    h=10*s**3-15*s**4+6*s**5
    hd=(30*s**2-60*s**3+30*s**4)/duration
    hdd=(60*s-180*s**2+120*s**3)/duration**2
    return h,hd,hdd


def reference(t,c,scenario):
    h,hd,hdd=blend(t)
    p=np.zeros(3);v=p.copy();a=p.copy()
    target=c['target_position_ned']
    rotvec=np.zeros(3)
    if scenario in ('position','combined','fixed'):
        p,v,a=target*h,target*hd,target*hdd
    if scenario in ('attitude','combined','fixed','circle'):
        rotvec=Rotation.from_matrix(rpy_matrix(np.deg2rad(c['target_rpy_deg']))).as_rotvec()
    if scenario=='fixed':
        h,hd,hdd=1.0,0.0,0.0
        p,v,a=target.copy(),np.zeros(3),np.zeros(3)
    if scenario=='circle':
        # 渐入圆轨迹，起点位于原点；提供解析速度与加速度。
        rate=0.3
        phase=rate*(t-1)
        base=np.array([np.cos(phase)-1,np.sin(phase),-0.8])
        db=np.array([-rate*np.sin(phase),rate*np.cos(phase),0])
        ddb=np.array([-rate**2*np.cos(phase),-rate**2*np.sin(phase),0])
        p=h*base;v=hd*base+h*db;a=hdd*base+2*hd*db+h*ddb
    return dict(p=p,v=v,a=a,R=Rotation.from_rotvec(h*rotvec).as_matrix(),
                w=hd*rotvec,wdot=hdd*rotvec)
