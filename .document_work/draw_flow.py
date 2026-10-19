from PIL import Image, ImageDraw, ImageFont
from pathlib import Path
im=Image.new('RGB',(1500,1600),'white');d=ImageDraw.Draw(im)
font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',29)
small=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',25)
def text(center,lines):
    lines=lines.split('\n');height=len(lines)*42
    for j,line in enumerate(lines):
        box=d.textbbox((0,0),line,font=font)
        d.text((center[0]-(box[2]-box[0])/2,center[1]-height/2+j*42),line,font=font,fill='black')
def node(box,lines):
    d.rectangle(box,outline='black',width=3)
    text(((box[0]+box[2])/2,(box[1]+box[3])/2),lines)
def arrow(points):
    d.line(points,fill='black',width=3)
    x,y=points[-1];a,b=points[-2];dx=x-a;dy=y-b;n=(dx*dx+dy*dy)**.5;ux=dx/n;uy=dy/n
    d.polygon([(x,y),(x-ux*17-uy*7,y-uy*17+ux*7),(x-ux*17+uy*7,y-uy*17-ux*7)],fill='black')
node((455,30,1045,150),'参考发生器  reference.py\n位置 姿态 及其导数')
node((230,290,690,425),'位置 PID  control.py\n位置误差与速度误差反馈')
node((870,290,1330,425),'SO(3) 控制  control.py\n姿态误差与角速度误差反馈')
arrow([(600,150),(600,205),(460,205),(460,290)])
arrow([(900,150),(900,205),(1100,205),(1100,290)])
node((455,560,1045,695),'推力分配器  allocation.py\n伪逆分配  角度反解  油门反查')
arrow([(460,425),(460,480),(650,480),(650,560)])
arrow([(1100,425),(1100,480),(850,480),(850,560)])
text((430,515),'期望力  N');text((1120,515),'期望力矩  N·m')
node((455,835,1045,970),'执行机构  model.py\n电机一阶惯性  推力正向查表')
arrow([(750,695),(750,835)])
text((1050,761),'8 个角度  4 个油门')
node((455,1110,1045,1245),'刚体动力学与积分  model.py\nNewton–Euler 方程  四元数  RK4')
arrow([(750,970),(750,1110)])
text((1100,1037),'实际力与力矩')
node((455,1385,1045,1520),'更新状态  simulation.py\n位置 速度 姿态 角速度')
arrow([(750,1245),(750,1385)])
arrow([(455,1450),(100,1450),(100,356),(230,356)])
arrow([(1045,1450),(1400,1450),(1400,356),(1330,356)])
text((215,1100),'状态\n反馈')
im.save(Path(__file__).with_name('flow.png'))
