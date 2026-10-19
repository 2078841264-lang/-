"""完整闭环验收与步长收敛，结果保存为 outputs/validation.json。"""
import json
from pathlib import Path
import numpy as np
from model import load_config
from simulation import simulate,metrics
from reference import reference


def main():
    c=load_config();results={};baseline=None
    for scenario in ('hover','position','attitude','combined','circle','fixed'):
        log=simulate(c,scenario)
        m=metrics(log);results[scenario]=m
        assert np.all(np.isfinite(log['state']))
        assert m['tail_max_position_error_m']<.02,(scenario,m)
        assert m['tail_max_attitude_error_deg']<1,(scenario,m)
        assert m['max_quaternion_norm_error']<1e-12
        print(scenario,json.dumps(m),flush=True)
        if scenario=='combined':baseline=log
    fine=c.copy();fine['dt']=c['dt']/2
    finer=simulate(fine,'combined')
    position_diff=np.max(np.linalg.norm(finer['state'][::2,:3]-baseline['state'][:,:3],axis=1))
    # q 与 -q 是同一旋转，用绝对内积比较姿态。
    dots=np.abs(np.sum(finer['state'][::2,6:10]*baseline['state'][:,6:10],axis=1))
    angle_diff=np.max(np.rad2deg(2*np.arccos(np.clip(dots,-1,1))))
    results['step_halving']={'max_position_difference_m':float(position_diff),'max_attitude_difference_deg':float(angle_diff)}
    assert position_diff<.005 and angle_diff<.1,results['step_halving']
    for name,patch,zero in [('ideal_motor',{'motor_tau':0},False),('nullspace',{'nullspace_enabled':True},False),('zero_start',{},True)]:
        cfg={**c,**patch};log=simulate(cfg,'combined',zero)
        results[name]=metrics(log)
        assert results[name]['tail_max_position_error_m']<.02,(name,results[name])
        assert results[name]['tail_max_attitude_error_deg']<1,(name,results[name])
        print(name,json.dumps(results[name]),flush=True)
    # 有限时段的不可实现加速度命令，随后恢复悬停，验证饱和恢复及积分限制。
    def stress_ref(t):
        ref=reference(t,c,'hover')
        if 1<=t<1.2:ref['a']=np.array([0,0,-100.])
        return ref
    stress=simulate(c,'hover',reference_fn=stress_ref)
    results['saturation_recovery']=metrics(stress)
    assert np.any(stress['saturated'])
    assert np.all(np.isfinite(stress['state']))
    assert np.max(np.abs(stress['integral']))<=1+1e-12
    assert results['saturation_recovery']['tail_max_position_error_m']<.02
    out=Path(__file__).parent/'outputs';out.mkdir(exist_ok=True)
    (out/'validation.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
    print('All closed-loop validation checks passed.',flush=True)


if __name__=='__main__':main()
