"""Coordinate-driven CUMCM mechanism examples; synthetic geometry, not contest results."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Arc, Rectangle, Polygon

def build(out, tilt=28, altitude=38):
    if not 5 <= tilt <= 65 or not 10 <= altitude <= 75:
        raise ValueError('demo layout supports tilt [5,65], altitude [10,75] degrees')
    out.mkdir(parents=True, exist_ok=False)
    plt.rcParams.update({'font.sans-serif':['Microsoft YaHei','SimHei','DejaVu Sans'], 'axes.unicode_minus':False,'svg.fonttype':'none','pdf.fonttype':42})
    fig,axs=plt.subplots(2,2,figsize=(12,8),layout='constrained')
    ink='#263238'; teal='#168A88'; coral='#D9664B'
    def segment(ax,a,b,**kw): ax.plot(*np.array([a,b]).T,**kw)
    def arrow(ax,a,b,label=None,color=ink):
        ax.annotate('',xy=b,xytext=a,arrowprops={'arrowstyle':'->','color':color,'lw':1.3})
        if label: ax.text(*b,label,fontsize=10,va='bottom')
    for ax in axs.flat:
        ax.set_aspect('equal'); ax.axis('off')
    # Oblique linear projection: every 3D point and angle arc shares this matrix.
    ax=axs[0,0]; P=np.array([[1,-.45,0],[.12,.32,1.]])
    def project(v): return np.asarray(v)@P.T
    az=math.radians(35); el=math.radians(altitude)
    sun=np.array([math.cos(el)*math.cos(az),math.cos(el)*math.sin(az),math.sin(el)])
    foot=sun*np.array([1,1,0]); origin=np.zeros(3)
    t=np.linspace(0,2*np.pi,241); ring=project(np.c_[np.cos(t),np.sin(t),np.zeros_like(t)])
    ax.plot(*ring.T,color=ink,lw=1)
    for v,txt in [(np.array([1.3,0,0]),'东 x'),(np.array([0,1.3,0]),'北 y'),(np.array([0,0,1.15]),'天顶 z')]: arrow(ax,project(origin),project(v),txt)
    arrow(ax,project(origin),project(sun),'太阳方向',coral)
    segment(ax,project(sun),project(foot),color='#829498',ls='--',lw=1)
    segment(ax,project(origin),project(foot),color=teal,lw=1)
    t=np.linspace(0,el,70); arc=project(.34*np.c_[np.cos(t)*math.cos(az),np.cos(t)*math.sin(az),np.sin(t)])
    ax.plot(*arc.T,color=teal); ax.text(*(arc[len(arc)//2]+[.09,0]),'α',fontsize=13)
    ax.text(-.08,-.12,'O'); ax.set_xlim(-1.3,1.7);ax.set_ylim(-.65,1.55)
    ax.set_title('（a）空间方向 → 地平投影 → 高度角',fontsize=12,pad=12)
    # True orthogonality of mirror tangent and normal.
    ax=axs[0,1]; th=math.radians(tilt); tangent=np.array([math.cos(th),math.sin(th)]); normal=np.array([-math.sin(th),math.cos(th)])
    corners=np.array([-tangent-.035*normal,tangent-.035*normal,tangent+.035*normal,-tangent+.035*normal])
    ax.add_patch(Polygon(corners,fc='#CFE7E4',ec=teal,lw=1.5))
    segment(ax,[-1.35,0],[1.4,0],color='#8A999C',ls='--',lw=1)
    arrow(ax,[0,0],normal*1.1,'法向量 n'); ax.add_patch(Arc((0,0),.8,.8,theta1=0,theta2=tilt,color=teal))
    ax.text(.5,.1,'θ',fontsize=13); ax.text(.8,.7,'镜面');ax.text(.85,-.17,'水平参考线')
    p=.15*tangent; q=.15*normal
    ax.plot(*np.array([p,p+q,q]).T,color=ink,lw=.8)
    ax.set_xlim(-1.4,1.5);ax.set_ylim(min(-.65,float(corners[:,1].min())-.18),1.5);ax.set_title('（b）镜面倾角与法向垂直关系',fontsize=12,pad=12)
    # Side section of tower; ray slope and shadow bound derive from same elevation.
    ax=axs[1,0]; H=2.; R=.16; L=H/math.tan(el)
    ax.add_patch(Polygon([[-R,0],[-R-L,0],[-R,H]],fc='#E8ECEC',ec='none'))
    ax.add_patch(Rectangle((-R,0),2*R,H,fc='#DAE4E6',ec=ink,lw=1.2))
    segment(ax,[-L-.6,0],[1.,0],color=ink,lw=1)
    m=np.array([-min(L*.5,1.25),.35]); hit=np.array([R,m[1]+(R-m[0])*math.tan(el)])
    far=hit+np.array([.8,.8*math.tan(el)])
    arrow(ax,far,hit,color=coral);segment(ax,hit,m,color=coral,ls='--',lw=1.2)
    segment(ax,m+[-.18,-.1],m+[.18,.1],color=teal,lw=3)
    ax.text(m[0]-.35,.1,'镜面');ax.text(.25,1.3,'塔身截面');ax.text(-L*.8,-.25,'阴影边界由太阳高度角确定',fontsize=9)
    ax.text(hit[0]-.95,hit[1]+.15,'遮挡段',fontsize=10)
    ax.set_xlim(-L-.6,1.3);ax.set_ylim(-.4,max(2.6,float(far[1])+.3));ax.set_title('（c）光路相交与地面阴影',fontsize=12,pad=12)
    # Domain and boundary conditions, not a simulated temperature solution.
    ax=axs[1,1];ax.add_patch(Rectangle((-.9,-.25),1.8,.5,fc='#F4E2CB',ec=ink))
    for x in [-.6,0,.6]:
        arrow(ax,[x,.95],[x,.28],color=coral);arrow(ax,[x,-.95],[x,-.28],color=coral)
    arrow(ax,[1.12,-.6],[1.12,.75],'x');ax.text(-1.25,1.02,'环境温度 T∞ > T',fontsize=10)
    ax.text(-.42,.02,'导热区域',fontsize=10);ax.text(-.4,.55,'对流加热',fontsize=10)
    ax.text(1.2,-.28,'−d/2',fontsize=9);ax.text(1.2,.23,'d/2',fontsize=9)
    ax.set_xlim(-1.6,1.7);ax.set_ylim(-1.1,1.2);ax.set_title('（d）计算区域与传热边界条件',fontsize=12,pad=12)
    outputs=[]
    for ext in ['svg','pdf','png']:
        p=out/f'mechanism-examples.{ext}';fig.savefig(p,dpi=190,metadata={'Creator':'Coordinate-driven mechanism demo'} if ext=='pdf' else None)
        outputs.append({'file':p.name,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
    plt.close(fig)
    checks={'mirror_dot_normal':float(tangent@normal),'sun_unit_norm':float(np.linalg.norm(sun)), 'projection_z':float(foot[2]),'recomputed_altitude_deg':math.degrees(math.atan2(sun[2],np.linalg.norm(sun[:2]))),'shadow_length':L,'ray_hit_inside_tower':bool(0<hit[1]<H)}
    assert abs(checks['mirror_dot_normal'])<1e-12 and checks['ray_hit_inside_tower']
    assert abs(checks['sun_unit_norm']-1)<1e-12 and checks['projection_z']==0
    assert abs(checks['recomputed_altitude_deg']-altitude)<1e-10
    report={'kind':'illustrative_geometry_not_contest_results','actual_backend':'matplotlib_coordinate_drawing','parameters':{'tilt_deg':tilt,'altitude_deg':altitude},'projection_matrix':P.tolist(),'checks':checks,'outputs':outputs,'generator_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'visual_review':'pending','scope':'Four reusable construction examples; no complete model or award-paper numerical reproduction.'}
    report['projection_type']='oblique_linear'
    (out/'geometry-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    (out/'latex_include.tex').write_text('\\begin{figure}[htbp]\n\\centering\n\\includegraphics[width=\\linewidth]{mechanism-examples.pdf}\n\\caption{空间投影、镜面姿态、遮挡与边界条件的几何示意。}\n\\end{figure}\n',encoding='utf-8')
    return report

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output-dir',type=Path,required=True);p.add_argument('--tilt',type=float,default=28);p.add_argument('--altitude',type=float,default=38)
    a=p.parse_args();print(json.dumps(build(a.output_dir,a.tilt,a.altitude),ensure_ascii=False,indent=2))
