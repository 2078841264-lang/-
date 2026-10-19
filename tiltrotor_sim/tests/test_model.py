"""代数、坐标及执行器验证；pytest 从项目根目录运行。"""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import numpy as np
from numpy.testing import assert_allclose
from model import load_config,rpy_matrix,directions,module_thrust,thrust_to_throttle,motor_step,derivative
from allocation import Allocator
from control import Controller


def test_coordinates_and_hover():
    c=load_config()
    assert_allclose(directions(np.zeros((4,2))),np.tile([0,0,-1],(4,1)),atol=1e-15)
    assert (rpy_matrix([.1,0,0])@np.array([0,1,0]))[2]>0
    assert (rpy_matrix([0,.1,0])@np.array([1,0,0]))[2]<0
    assert (rpy_matrix([0,0,.1])@np.array([1,0,0]))[1]>0
    s=np.zeros(13);s[9]=1
    assert_allclose(derivative(s,np.array([0,0,-58.8,0,0,0]),c),0,atol=1e-13)
    assert_allclose(thrust_to_throttle(58.8/4,c),.4078488372093023)


def test_tables_and_motor():
    c=load_config()
    assert_allclose(module_thrust(c['throttle_table'],c),2*c['thrust_table'])
    assert_allclose(thrust_to_throttle(2*c['thrust_table'],c),c['throttle_table'])
    assert_allclose(module_thrust(np.array([-1,2]),c),[0,63.0728])
    assert_allclose(thrust_to_throttle(np.array([-1,1e6]),c),[0,1])
    assert_allclose(motor_step(np.zeros(4),np.ones(4),.2,.2),1-np.exp(-1))


def test_allocation_and_nullspace():
    c=load_config();a=Allocator(c)
    assert np.linalg.matrix_rank(a.M)==6
    assert_allclose(a.M@a.N,0,atol=1e-12)
    rng=np.random.default_rng(42)
    for _ in range(80):
        wrench=rng.normal(size=6)*np.array([4,4,40,.5,.5,.5])
        assert_allclose(a.vectors(wrench),a.analytic(wrench),atol=1e-12)
        angles,u,sat,ach=a.allocate(wrench,np.zeros((4,2)))
        assert not sat.any()
        assert_allclose(ach,wrench,atol=1e-10)
    c['nullspace_enabled']=True
    for wrench in [np.array([30,0,0,0,0,0.]),np.array([-30,0,0,0,0,0.]),
                   np.array([0,30,0,0,0,0.]),np.array([0,-30,0,0,0,0.])]:
        assert_allclose(a.M@a.vectors(wrench).ravel(),wrench,atol=1e-12)
        vectors=a.vectors(wrench)
        assert np.all(np.linalg.norm(vectors[:,[0,2]],axis=1)>1e-6)


def test_angle_edge_cases():
    c=load_config();a=Allocator(c);last=np.array([4*np.pi+.1,-2*np.pi+.2])
    assert_allclose(a.inverse_angles(np.zeros(3),last),last)
    rng=np.random.default_rng(11)
    for v in [np.array([0,1,0]),np.array([1e-10,-1,0]),*rng.normal(size=(100,3))]:
        ans=a.inverse_angles(v,last)
        assert np.max(np.abs(ans))<=6*np.pi+1e-12
        assert_allclose(directions(ans[None,:])[0],v/np.linalg.norm(v),atol=1e-9)
        last=ans
    last=np.array([np.pi-.001,0])
    new=a.inverse_angles(directions(np.array([[np.pi+.001,0]]))[0],last)
    assert np.linalg.norm(new-last)<.003


def test_saturation_and_antiwindup():
    c=load_config();a=Allocator(c);control=Controller(c)
    desired=np.array([0,0,-1000.,0,0,0])
    angles,u,sat,ach=a.allocate(desired,np.zeros((4,2)))
    assert sat.all();assert_allclose(u,1)
    assert_allclose(ach[:3],[0,0,-4*63.0728],atol=1e-10)
    state=np.zeros(13);state[9]=1
    ref={'p':np.array([0,0,-100.])}
    control.update_integral(state,ref,desired,ach,sat,.1)
    assert_allclose(control.integral,0)
    ref['p'][2]=100
    control.update_integral(state,ref,desired,ach,sat,.1)
    assert control.integral[2]<0
