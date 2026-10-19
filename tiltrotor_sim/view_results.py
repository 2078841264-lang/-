"""重新打开已有 flight.csv：不重新计算动力学、不覆盖保存的结果。"""
import argparse
from pathlib import Path
from model import load_config
from reporting import load_results,plot_results,show_flight,show_results


def main():
    parser=argparse.ArgumentParser(description='重开已有仿真曲线或可旋转的三维动画')
    parser.add_argument('path',type=Path,help='输出文件夹或 flight.csv 的路径')
    parser.add_argument('--3d',dest='three_d',action='store_true',help='仅打开可旋转的三维动画')
    args=parser.parse_args()
    try:
        log=load_results(args.path)
        if args.three_d:
            folder=args.path if args.path.is_dir() else args.path.parent
            # 必须使用这一次运行的真实参数，不能误用当前配置重新解释历史推力。
            parameter_file=folder/'parameters_used.json'
            if not parameter_file.exists():
                raise ValueError('三维动画需要 CSV 同目录的 parameters_used.json。')
            show_flight(log,load_config(parameter_file))
        else:plot_results(log,show=True)
    except (OSError,ValueError,RuntimeError) as exc:
        parser.exit(1,f'无法打开曲线：{exc}\n')
    if args.three_d:
        print('左键拖动旋转；中键拖动平移；滚轮或右键拖动缩放；Play/Pause 播放暂停；Time 滑块定位时刻。',flush=True)
    else:
        print('Zoom：框选放大；Pan：拖动平移；Home：复位；退出工具模式后，左键读数，右键设置坐标范围。',flush=True)
    show_results()


if __name__=='__main__':main()
