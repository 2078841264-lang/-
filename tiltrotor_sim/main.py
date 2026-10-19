"""命令行入口；在 VS Code 中打开本文件或使用已配置的调试入口。"""
import argparse
import json
from pathlib import Path
from model import load_config
from simulation import simulate,metrics


def main():
    p=argparse.ArgumentParser(description='双轴倾转四旋翼 FRD/NED 闭环仿真')
    p.add_argument('--config',type=Path)
    p.add_argument('--scenario',choices=['hover','position','attitude','combined','circle','fixed'],default='combined')
    p.add_argument('--duration',type=float)
    p.add_argument('--dt',type=float)
    p.add_argument('--target-position',nargs=3,type=float,metavar=('N','E','D'))
    p.add_argument('--target-rpy',nargs=3,type=float,metavar=('ROLL','PITCH','YAW'))
    p.add_argument('--ideal-motor',action='store_true')
    p.add_argument('--nullspace',action='store_true')
    p.add_argument('--zero-start',action='store_true')
    animation=p.add_mutually_exclusive_group()
    animation.add_argument('--animate',dest='animate',action='store_true',default=True,
                           help='生成三维 GIF（所有工况默认开启，保留原命令兼容性）')
    animation.add_argument('--no-animate',dest='animate',action='store_false',
                           help='跳过三维 GIF，仅导出数据和曲线')
    p.add_argument('--show',action='store_true',help='打开交互曲线和可旋转、暂停、拖动时间轴的三维动画')
    p.add_argument('--output',type=Path)
    args=p.parse_args();c=load_config(args.config)
    import numpy as np
    for key in ('duration','dt'):
        if getattr(args,key) is not None:
            if getattr(args,key)<=0:p.error(key+' 必须为正')
            c[key]=getattr(args,key)
    if args.target_position is not None:c['target_position_ned']=np.array(args.target_position)
    if args.target_rpy is not None:c['target_rpy_deg']=np.array(args.target_rpy)
    if args.ideal_motor:c['motor_tau']=0
    if args.nullspace:c['nullspace_enabled']=True
    out=args.output or Path(__file__).parent/'outputs'/args.scenario
    log=simulate(c,args.scenario,args.zero_start)
    from reporting import save_results,save_animation,show_flight,show_results
    save_results(log,c,out,show=args.show)
    if args.animate:
        print('正在生成三维动画 flight.gif ...',flush=True)
        save_animation(log,c,out)
    print(json.dumps(metrics(log),indent=2))
    print('Output:',out.resolve())
    if args.show:
        show_flight(log,c)
        print('图窗：Zoom 框选放大，Pan 平移，Home 复位；退出工具模式后，左键读数，右键设置坐标范围。',flush=True)
        print('三维动画：左键拖动旋转，滚轮缩放；Play/Pause 播放暂停，Time 滑块定位时刻。',flush=True)
        show_results()


if __name__=='__main__':main()
