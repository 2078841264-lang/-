"""PNG、可缩放交互窗口、完整 CSV 和三维 GIF；绘图不修改仿真数据。"""
import csv
import json
import os
import time
from pathlib import Path
import numpy as np
# 将字体缓存置于项目内，避免受限 Windows 用户目录导致权限警告。
os.environ.setdefault('MPLCONFIGDIR',str(Path(__file__).parent/'outputs'/'.matplotlib'))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation,PillowWriter
from matplotlib.widgets import Button,Slider
from model import rotation,directions,module_thrust
from simulation import metrics


def result_columns():
    # 记录单位与分量顺序，便于在 MATLAB/Excel 中复核。
    columns={'time':['time_s'],
             'state':['p_N_m','p_E_m','p_D_m','v_N_m_s','v_E_m_s','v_D_m_s',
                      'qx','qy','qz','qw','omega_x_rad_s','omega_y_rad_s','omega_z_rad_s'],
             'reference_position':['p_ref_N_m','p_ref_E_m','p_ref_D_m'],
             'reference_velocity':['v_ref_N_m_s','v_ref_E_m_s','v_ref_D_m_s'],
             'reference_omega':['omega_ref_x_rad_s','omega_ref_y_rad_s','omega_ref_z_rad_s']}
    for key in ('rpy_deg','reference_rpy_deg'):
        columns[key]=[key+'_'+s for s in ('roll','pitch','yaw')]
    for key in ('desired_wrench','achievable_wrench','actual_wrench','allocation_residual','tracking_residual'):
        columns[key]=[key+'_'+s for s in ('Fx_N','Fy_N','Fz_N','Tx_Nm','Ty_Nm','Tz_Nm')]
    columns['angles_deg']=[f'{angle}_{i}_deg' for i in range(1,5) for angle in ('alpha','beta')]
    for key in ('throttle_command','throttle_actual','saturated'):
        columns[key]=[f'{key}_{i}' for i in range(1,5)]
    columns['position_error']=['ep_N_m','ep_E_m','ep_D_m']
    columns['attitude_error_deg']=['attitude_geodesic_error_deg']
    columns['integral']=['integral_N_m_s','integral_E_m_s','integral_D_m_s']
    return columns


def save_results(log,c,out,show=False):
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    columns=result_columns()
    header=sum(columns.values(),[])+['height_m','reference_height_m']
    data=np.column_stack([log[key].reshape(len(log['time']),-1) for key in columns]+
                         [-log['state'][:,2],-log['reference_position'][:,2]])
    with open(out/'flight.csv','w',newline='',encoding='utf-8-sig') as f:
        writer=csv.writer(f);writer.writerow(header);writer.writerows(data)
    (out/'metrics.json').write_text(json.dumps(metrics(log),indent=2),encoding='utf-8')
    (out/'parameters_used.json').write_text(json.dumps(c,indent=2,default=lambda x:x.tolist()),encoding='utf-8')
    return plot_results(log,out,show)


def load_results(path):
    """从本程序导出的 CSV 恢复曲线，避免为了观察细节重新仿真。"""
    path=Path(path)
    if path.is_dir():path=path/'flight.csv'
    with path.open(newline='',encoding='utf-8-sig') as f:
        header=next(csv.reader(f))
        data=np.loadtxt(f,delimiter=',',ndmin=2)
    index={name:i for i,name in enumerate(header)}
    columns=result_columns()
    missing=[name for names in columns.values() for name in names if name not in index]
    if missing:raise ValueError('CSV 缺少仿真字段：'+', '.join(missing))
    log={key:data[:,[index[name] for name in names]] for key,names in columns.items()}
    log['time']=log['time'][:,0]
    log['attitude_error_deg']=log['attitude_error_deg'][:,0]
    log['angles_deg']=log['angles_deg'].reshape(-1,4,2)
    log['saturated']=log['saturated'].astype(bool)
    return log


class DataCursor:
    """工具栏空闲时：左键读取采样点，右键输入精确坐标范围。"""
    def __init__(self,fig):
        self.fig=fig
        self.annotation=None
        self.marker=None
        self.connection=fig.canvas.mpl_connect('button_press_event',self.on_click)

    def on_click(self,event):
        toolbar=getattr(event.canvas,'toolbar',None)
        if event.inaxes is None or event.xdata is None:
            return
        if toolbar is not None and toolbar.mode:return
        if event.button==3:
            self.set_limits(event.inaxes)
            return
        if event.button!=1:return
        candidates=[]
        for line in event.inaxes.lines:
            if line is self.marker:continue
            x,y=line.get_data()
            x=np.asarray(x);y=np.asarray(y)
            if not len(x):continue
            # 所有时间曲线按时间排序；只检查鼠标两侧的相邻采样点。
            k=int(np.searchsorted(x,event.xdata))
            for i in {max(0,min(len(x)-1,k)),max(0,min(len(x)-1,k-1))}:
                if not np.isfinite(y[i]):continue
                pixel=event.inaxes.transData.transform((x[i],y[i]))
                distance=np.linalg.norm(pixel-np.array([event.x,event.y]))
                candidates.append((distance,line,float(x[i]),float(y[i])))
        if not candidates:return
        _,line,x,y=min(candidates,key=lambda item:item[0])
        if self.annotation is not None:self.annotation.remove()
        if self.marker is not None:self.marker.remove()
        self.marker,=event.inaxes.plot([x],[y],'o',mfc='none',mec='black',ms=7,
                                      label='_data_cursor',scalex=False,scaley=False)
        label=line.get_label()
        if label.startswith('_'):label='value'
        self.annotation=event.inaxes.annotate(
            f'{label}\nt = {x:.12g} s\ny = {y:.12g}\n{event.inaxes.get_ylabel()}',
            xy=(x,y),xytext=(.02,.98),textcoords='axes fraction',va='top',
            fontsize=9,bbox=dict(boxstyle='round',fc='white',ec='gray',alpha=.95),
            arrowprops=dict(arrowstyle='->',color='gray'))
        event.canvas.draw_idle()

    def set_limits(self,ax):
        # 允许直接检查 1e-14 等微小量级，不依赖像素精度框选。
        from tkinter import simpledialog,messagebox
        parent=self.fig.canvas.manager.window
        limits=(*ax.get_xlim(),*ax.get_ylim())
        value=simpledialog.askstring('Axes limits',
            ax.get_ylabel()+'\nEnter: xmin xmax ymin ymax (scientific notation allowed)',
            initialvalue=' '.join(f'{v:.12g}' for v in limits),parent=parent)
        if value is None:return
        try:
            parsed=[float(s) for s in value.split()]
            if len(parsed)!=4 or not np.all(np.isfinite(parsed)):
                raise ValueError
            xmin,xmax,ymin,ymax=parsed
            if xmin>=xmax or ymin>=ymax:raise ValueError
        except ValueError:
            messagebox.showerror('Invalid limits','Enter four finite numbers; min must be less than max.',parent=parent)
            return
        toolbar=self.fig.canvas.manager.toolbar
        if toolbar is not None:toolbar.push_current()
        ax.set_xlim(xmin,xmax);ax.set_ylim(ymin,ymax)
        if toolbar is not None:toolbar.push_current()
        self.fig.canvas.draw_idle()


def allocation_axis(ax,values,unit):
    """保留原始残差；近零时设置显示范围，并标明峰值，不滤波或截断数据。"""
    peak=float(np.max(np.abs(values)))
    display_floor=1e-9
    if peak<display_floor:
        ax.set_ylim(-display_floor,display_floor)
        ax.set_title(f'Max |residual| = {peak:.3e} {unit} (near zero)',fontsize=10)
    else:
        ax.set_title(f'Max |residual| = {peak:.3e} {unit}',fontsize=10)
    ax.ticklabel_format(axis='y',style='sci',scilimits=(0,0),useOffset=False)


def interactive_backend():
    """统一启用桌面图窗后端，曲线与三维播放器均使用 Tk。"""
    if matplotlib.get_backend().lower()=='tkagg':return
    try:plt.switch_backend('TkAgg')
    except (ImportError,RuntimeError) as exc:
        raise RuntimeError('交互窗口需要带 tkinter 的桌面 Python。') from exc


def plot_results(log,out=None,show=False):
    """同一份数据用于 PNG 与交互窗口。show=True 保留四个窗口供 plt.show() 使用。"""
    if show:interactive_backend()
    figures=[]
    def finish(fig,name):
        if out is not None:fig.savefig(Path(out)/(name+'.png'),dpi=140)
        if show:
            fig.canvas.manager.set_window_title(name+' | Zoom / Pan / Home | left: value | right: limits')
            fig._data_cursor=DataCursor(fig)  # 保存对象，避免回调被弱引用回收。
            figures.append(fig)
        else:plt.close(fig)
    t=log['time']
    fig,axes=plt.subplots(4,2,figsize=(13,12),sharex=True)
    for j,label in enumerate(('North (m)','East (m)','Down (m)')):
        ax=axes[j,0];ax.plot(t,log['state'][:,j],label='actual')
        ax.plot(t,log['reference_position'][:,j],'--',label='reference');ax.set_ylabel(label)
    for j,label in enumerate(('Roll (deg)','Pitch (deg)','Yaw (deg)')):
        ax=axes[j,1];ax.plot(t,log['rpy_deg'][:,j],label='actual')
        ax.plot(t,log['reference_rpy_deg'][:,j],'--',label='reference');ax.set_ylabel(label)
    axes[3,0].plot(t,-log['state'][:,2],label='actual')
    axes[3,0].plot(t,-log['reference_position'][:,2],'--',label='reference');axes[3,0].set_ylabel('Height = -Down (m)')
    axes[3,1].plot(t,log['attitude_error_deg'],label='geodesic error');axes[3,1].set_ylabel('SO(3) error (deg)')
    for ax in axes.flat:ax.grid(alpha=.3)
    axes[0,0].legend();axes[0,1].legend()
    for ax in axes[-1]:ax.set_xlabel('Time (s)')
    fig.suptitle('FRD body / NED world: closed-loop tracking');fig.tight_layout()
    finish(fig,'tracking')
    fig,axes=plt.subplots(3,2,figsize=(13,9),sharex=True)
    for j in range(6):
        ax=axes[j%3,j//3]
        for key,style in [('desired_wrench','--'),('achievable_wrench',':'),('actual_wrench','-')]:
            ax.plot(t,log[key][:,j],style,label=key.replace('_wrench',''))
        ax.set_ylabel(('F' if j<3 else 'Torque ')+('xyz'[j%3])+(' (N)' if j<3 else ' (Nm)'));ax.grid(alpha=.3)
    axes[0,0].legend();axes[0,1].legend()
    for ax in axes[-1]:ax.set_xlabel('Time (s)')
    fig.suptitle('Body-frame force and torque');fig.tight_layout();finish(fig,'wrench')
    fig,axes=plt.subplots(4,3,figsize=(15,11),sharex=True)
    for i in range(4):
        for j,label in enumerate(('alpha','beta')):
            axes[i,j].plot(t,log['angles_deg'][:,i,j],label=f'{label}{i+1}');axes[i,j].set_ylabel(f'{label}{i+1} (deg)')
        axes[i,2].plot(t,log['throttle_command'][:,i],'--',label='command')
        axes[i,2].plot(t,log['throttle_actual'][:,i],label='actual');axes[i,2].set_ylabel(f'Throttle {i+1}')
    axes[0,2].legend()
    for ax in axes.flat:ax.grid(alpha=.3)
    for ax in axes[-1]:ax.set_xlabel('Time (s)')
    fig.tight_layout();finish(fig,'actuators')
    fig,axes=plt.subplots(3,2,figsize=(13,9),sharex=True)
    axes[0,0].plot(t,log['state'][:,3:6]);axes[0,0].set_ylabel('NED velocity (m/s)')
    axes[0,1].plot(t,log['state'][:,10:13]);axes[0,1].set_ylabel('Body omega (rad/s)')
    axes[1,0].plot(t,log['allocation_residual'][:,:3]);axes[1,0].set_ylabel('Allocation force residual (N)')
    axes[1,1].plot(t,log['allocation_residual'][:,3:]);axes[1,1].set_ylabel('Allocation torque residual (Nm)')
    allocation_axis(axes[1,0],log['allocation_residual'][:,:3],'N')
    allocation_axis(axes[1,1],log['allocation_residual'][:,3:],'Nm')
    axes[2,0].plot(t,log['saturated'].astype(int));axes[2,0].set_ylabel('Module saturation flags')
    axes[2,1].plot(t,log['integral']);axes[2,1].set_ylabel('Position integral (m s)')
    for ax,labels in [(axes[0,0],('N','E','D')),(axes[0,1],('x','y','z')),
                      (axes[1,0],('x','y','z')),(axes[1,1],('x','y','z')),
                      (axes[2,0],('1','2','3','4')),(axes[2,1],('N','E','D'))]:
        for line,label in zip(ax.lines,labels):line.set_label(label)
        ax.legend(loc='upper right',ncol=len(labels),fontsize=8)
    for ax in axes.flat:ax.grid(alpha=.3)
    for ax in axes[-1]:ax.set_xlabel('Time (s)')
    fig.tight_layout();finish(fig,'diagnostics')
    return figures


def show_results():
    """保持窗口事件循环；关闭所有图窗之后，终端命令结束。"""
    plt.show()


def flight_scene(log,c):
    """GIF 与交互播放器共用三维场景；update 只更新物体，不重置观察视角。

    姿态来自实际四元数，推力来自实际油门与倾转角；D->-D 仅用于显示。
    """
    fig=plt.figure(figsize=(8,7));ax=fig.add_subplot(111,projection='3d')
    transform=np.array([1,1,-1])
    path=log['state'][:,:3]*transform;ref=log['reference_position']*transform
    ax.plot(*ref.T,'--',color='gray',label='reference')
    trail,=ax.plot([],[],[],color='steelblue',label='trajectory')
    body,=ax.plot([],[],[],'o-',color='black',lw=2)
    nose,=ax.plot([],[],[],color='red',lw=3,label='front')
    # 标号固定跟随模块，便于辨认四个实际推力箭头的来源。
    module_labels=[ax.text(0,0,0,str(i+1),color='black',fontsize=10,
                           fontweight='bold',
                           bbox=dict(boxstyle='round,pad=.12',fc='white',ec='darkorange',alpha=.9))
                   for i in range(4)]
    readout=fig.text(.02,.02,'',fontsize=9,family='monospace',va='bottom')
    arrows=[]
    # 将实际推力箭头端点也纳入范围，避免大推力时箭头被坐标边界裁掉。
    all_rotations=np.array([rotation(q) for q in log['state'][:,6:10]])
    all_motors=(log['state'][:,:3,None]+np.einsum('nij,kj->nik',all_rotations,c['arms'])).transpose(0,2,1)*transform
    all_thrust=(directions(np.deg2rad(log['angles_deg']).reshape(-1,2))
                .reshape(-1,4,3)*module_thrust(log['throttle_actual'],c)[:,:,None])
    all_vectors=np.einsum('nij,nkj->nki',all_rotations,all_thrust)*transform*.035
    allp=np.vstack((path,ref,all_motors.reshape(-1,3),(all_motors+all_vectors).reshape(-1,3)))
    center=(allp.max(0)+allp.min(0))/2
    span=max(2.5,float(np.ptp(allp,axis=0).max()+2))
    ax.set_xlim(center[0]-span/2,center[0]+span/2);ax.set_ylim(center[1]-span/2,center[1]+span/2)
    ax.set_zlim(center[2]-span/2,center[2]+span/2);ax.set_box_aspect((1,1,1))
    ax.set_xlabel('North (m)');ax.set_ylabel('East (m)');ax.set_zlabel('Height = -Down (m)');ax.legend()
    title=ax.set_title('')
    fig.subplots_adjust(bottom=.18,top=.88)
    def line(artist,points):artist.set_data_3d(*points.T)
    def update(k):
        state=log['state'][k];R=rotation(state[6:10]);p=state[:3]
        motors=(p+(R@c['arms'].T).T)*transform
        for label,point in zip(module_labels,motors):
            label.set_position((point[0],point[1]));label.set_3d_properties(point[2]+.06,zdir=None)
        line(body,motors[[0,1,2,3,0]])
        line(nose,np.array([p,p+R@np.array([.55,0,0])])*transform)
        line(trail,path[:k+1])
        magnitudes=module_thrust(log['throttle_actual'][k],c)
        thrust=directions(np.deg2rad(log['angles_deg'][k]))*magnitudes[:,None]
        for artist in arrows:artist.remove()
        arrows.clear()
        vectors=(R@thrust.T).T*transform*.035
        arrows.append(ax.quiver(*motors.T,*vectors.T,color='darkorange',arrow_length_ratio=.2))
        title.set_text(f'FRD / NED | t={log["time"][k]:.1f} s | orange: thrust (0.035 m/N)')
        rpy=log['rpy_deg'][k]
        readout.set_text(f'Actual R/P/Y (deg): {rpy[0]:7.2f} {rpy[1]:7.2f} {rpy[2]:7.2f}\n'
                         f'Actual thrust 1/2/3/4 (N): '+' '.join(f'{v:6.2f}' for v in magnitudes)+'\n'
                         'Modules: 1 front-right, 2 rear-right, 3 rear-left, 4 front-left')
        return [body,nose,trail,title,readout,*module_labels,*arrows]
    return fig,ax,update


def save_animation(log,c,out):
    """导出固定视角的 GIF；空间旋转请使用三维交互播放器。"""
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    fig,ax,update=flight_scene(log,c)
    frames=np.unique(np.linspace(0,len(log['time'])-1,min(240,len(log['time']))).astype(int))
    ani=FuncAnimation(fig,update,frames=frames,interval=100,blit=False)
    try:ani.save(out/'flight.gif',writer=PillowWriter(fps=10))
    finally:plt.close(fig)


class FlightPlayer:
    """可旋转的三维动画：播放/暂停、时间定位、视角复位及鼠标缩放。

    播放按真实经过时间选取原始日志采样点，不为了动画重新积分动力学。
    操作时间轴或拖动三维场景时自动暂停，便于检查当前姿态与推力。
    """
    def __init__(self,log,c):
        self.times=np.asarray(log['time'])
        if len(self.times)<2 or not np.all(np.isfinite(self.times)) or not np.all(np.diff(self.times)>0):
            raise ValueError('三维播放需要至少两个有限、严格递增的时间采样点。')
        self.fig,self.ax,self.update=flight_scene(log,c)
        self.fig.set_size_inches(10,8.5,forward=True)
        self.fig.subplots_adjust(bottom=.31)
        self.fig.canvas.manager.set_window_title('3D flight | drag: rotate | wheel: zoom | Space: play/pause')
        self.initial_limits=(self.ax.get_xlim3d(),self.ax.get_ylim3d(),self.ax.get_zlim3d())
        self.initial_view=(self.ax.elev,self.ax.azim,self.ax.roll)
        self.ax.mouse_init(rotate_btn=1,pan_btn=2,zoom_btn=3)
        self.sample=0;self.playing=False;self.updating_slider=False
        self.play_button=Button(self.fig.add_axes([.10,.18,.15,.045]),'Play')
        self.reset_button=Button(self.fig.add_axes([.28,.18,.18,.045]),'Reset view')
        self.top_button=Button(self.fig.add_axes([.49,.18,.12,.045]),'Top')
        self.side_button=Button(self.fig.add_axes([.64,.18,.12,.045]),'Side')
        self.slider=Slider(self.fig.add_axes([.14,.12,.69,.025]),'Time',
                           self.times[0],self.times[-1],valinit=self.times[0],
                           valfmt='%1.3f s',valstep=self.times)
        self.fig.text(.05,.255,'Left drag: rotate | Middle drag: pan | Wheel / right drag: zoom | Space: play/pause',fontsize=9)
        self.play_button.on_clicked(self.toggle)
        self.reset_button.on_clicked(self.reset_view)
        self.top_button.on_clicked(lambda event:self.set_view(90,-90))
        self.side_button.on_clicked(lambda event:self.set_view(0,0))
        self.slider.on_changed(self.seek)
        self.timer=self.fig.canvas.new_timer(interval=50)
        self.timer.add_callback(self.tick)
        self.fig.canvas.mpl_connect('button_press_event',self.on_press)
        self.fig.canvas.mpl_connect('scroll_event',self.on_scroll)
        self.fig.canvas.mpl_connect('key_press_event',self.on_key)
        self.fig.canvas.mpl_connect('close_event',self.on_close)
        self.render(0)

    def render(self,k):
        self.sample=int(np.clip(k,0,len(self.times)-1))
        self.update(self.sample)
        self.updating_slider=True
        try:self.slider.set_val(float(self.times[self.sample]))
        finally:self.updating_slider=False
        self.fig.canvas.draw_idle()

    def play(self):
        if self.sample==len(self.times)-1:self.render(0)
        self.base_time=float(self.times[self.sample]);self.started=time.perf_counter()
        self.playing=True;self.play_button.label.set_text('Pause')
        self.timer.start();self.fig.canvas.draw_idle()

    def pause(self):
        self.timer.stop();self.playing=False;self.play_button.label.set_text('Play')
        self.fig.canvas.draw_idle()

    def toggle(self,event=None):
        if self.playing:self.pause()
        else:self.play()

    def tick(self):
        if not self.playing:return
        target=self.base_time+time.perf_counter()-self.started
        k=np.searchsorted(self.times,target,side='right')-1
        self.render(k)
        if target>=self.times[-1]:self.pause()

    def seek(self,value):
        if self.updating_slider:return
        self.pause()
        k=int(np.searchsorted(self.times,value))
        candidates=[max(0,min(len(self.times)-1,k-1)),max(0,min(len(self.times)-1,k))]
        self.render(min(candidates,key=lambda i:abs(self.times[i]-value)))

    def reset_view(self,event=None):
        self.ax.view_init(elev=self.initial_view[0],azim=self.initial_view[1],roll=self.initial_view[2])
        self.ax.set_xlim3d(self.initial_limits[0]);self.ax.set_ylim3d(self.initial_limits[1])
        self.ax.set_zlim3d(self.initial_limits[2]);self.fig.canvas.draw_idle()

    def set_view(self,elev,azim):
        self.ax.view_init(elev=elev,azim=azim,roll=0);self.fig.canvas.draw_idle()

    def on_press(self,event):
        if event.inaxes is self.ax:self.pause()

    def on_scroll(self,event):
        if event.inaxes is not self.ax:return
        self.pause()
        scale=.85**np.clip(event.step,-10,10)
        for limits,setter in ((self.ax.get_xlim3d(),self.ax.set_xlim3d),
                              (self.ax.get_ylim3d(),self.ax.set_ylim3d),
                              (self.ax.get_zlim3d(),self.ax.set_zlim3d)):
            center=(limits[0]+limits[1])/2
            half=np.clip((limits[1]-limits[0])*scale/2,1e-6,1e6)
            setter(center-half,center+half)
        self.fig.canvas.draw_idle()

    def on_key(self,event):
        if event.key==' ':self.toggle()
        elif event.key in ('left','right'):
            self.seek(self.times[self.sample]+(.1 if event.key=='right' else -.1))

    def on_close(self,event):
        self.timer.stop();self.playing=False


def show_flight(log,c):
    """创建并自动播放三维窗口；最终由 show_results() 保持事件循环。"""
    interactive_backend()
    player=FlightPlayer(log,c)
    player.fig._flight_player=player  # 保留控件和定时器对象，避免垃圾回收。
    player.play()
    return player
