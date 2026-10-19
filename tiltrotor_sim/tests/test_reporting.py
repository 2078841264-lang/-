"""检查重开 CSV 不丢失数值，数据读数不改变坐标范围，近零显示不隐藏真实残差。"""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import numpy as np
from numpy.testing import assert_allclose
from matplotlib.backend_bases import MouseEvent
import reporting
from unittest.mock import patch
from types import SimpleNamespace
from model import load_config
from simulation import simulate


def test_csv_reopen_preserves_all_logged_channels(tmp_path):
    c=load_config();c['duration']=.01
    log=simulate(c,'hover')
    reporting.save_results(log,c,tmp_path)
    reopened=reporting.load_results(tmp_path)
    for key,value in log.items():
        assert reopened[key].shape==value.shape,key
        assert_allclose(reopened[key],value,rtol=0,atol=0)
    assert reopened['saturated'].dtype==bool


def test_data_cursor_after_zoom_reads_raw_value_without_rescaling():
    fig,ax=reporting.plt.subplots()
    ax.plot([0,1,2],[0,1e-14,0],label='z')
    ax.set_xlim(.5,1.5);ax.set_ylim(-2e-14,2e-14)
    fig.canvas.draw()
    limits=(ax.get_xlim(),ax.get_ylim())
    cursor=reporting.DataCursor(fig)
    x,y=ax.transData.transform((1,1e-14))
    event=MouseEvent('button_press_event',fig.canvas,x,y,button=1)
    cursor.on_click(event)
    assert 't = 1 s' in cursor.annotation.get_text()
    assert 'y = 1e-14' in cursor.annotation.get_text()
    assert 'z' in cursor.annotation.get_text()
    assert (ax.get_xlim(),ax.get_ylim())==limits
    reporting.plt.close(fig)


def test_residual_scale_preserves_raw_data_and_real_error():
    fig,axes=reporting.plt.subplots(1,2)
    small=np.array([0,1e-14,-1e-14])
    line,=axes[0].plot(small)
    reporting.allocation_axis(axes[0],small,'N')
    assert_allclose(line.get_ydata(),small,rtol=0,atol=0)
    assert_allclose(axes[0].get_ylim(),[-1e-9,1e-9])
    assert '1.000e-14 N' in axes[0].get_title()
    large=np.array([0,2,-2])
    axes[1].plot(large)
    reporting.allocation_axis(axes[1],large,'N')
    low,high=axes[1].get_ylim()
    assert low<=-2 and high>=2
    assert 'near zero' not in axes[1].get_title()
    reporting.plt.close(fig)


def test_flight_player_seek_clock_and_camera_are_independent():
    c=load_config();c['duration']=.02
    log=simulate(c,'hover')
    player=reporting.FlightPlayer(log,c)
    # 定位帧必须用原始采样点，观察视角不应被帧更新覆盖。
    player.set_view(42,17)
    player.seek(.011)
    assert player.sample==5
    assert_allclose(player.slider.val,.01)
    assert_allclose([player.ax.elev,player.ax.azim],[42,17])
    with patch('reporting.time.perf_counter',return_value=100):player.play()
    with patch('reporting.time.perf_counter',return_value=100.006):player.tick()
    assert player.sample==8
    assert player.playing
    # 时间滑块操作暂停播放；最后一帧之后暂停，再播放回到开头。
    player.seek(.02)
    assert not player.playing and player.sample==len(log['time'])-1
    with patch('reporting.time.perf_counter',return_value=200):player.play()
    assert player.sample==0
    with patch('reporting.time.perf_counter',return_value=201):player.tick()
    assert not player.playing and player.sample==len(log['time'])-1
    player.reset_view()
    assert_allclose([player.ax.elev,player.ax.azim,player.ax.roll],player.initial_view)
    player.on_close(None);reporting.plt.close(player.fig)


def test_flight_player_zoom_pause_and_actual_pose():
    c=load_config();c['duration']=.01
    log=simulate(c,'hover')
    player=reporting.FlightPlayer(log,c)
    player.play()
    original=player.ax.get_xlim3d()
    player.on_scroll(SimpleNamespace(inaxes=player.ax,step=1))
    assert not player.playing
    zoomed=player.ax.get_xlim3d()
    assert_allclose(zoomed[1]-zoomed[0],.85*(original[1]-original[0]))
    player.seek(.006)
    # 水平配平的四个模块位置与当前模型参数完全对应。
    body=player.ax.lines[2]
    actual=np.column_stack(body.get_data_3d())
    expected=(log['state'][3,:3]+c['arms'][[0,1,2,3,0]])*np.array([1,1,-1])
    assert_allclose(actual,expected,atol=1e-14)
    assert '14.70' in player.fig.texts[0].get_text()
    player.on_close(None);reporting.plt.close(player.fig)
