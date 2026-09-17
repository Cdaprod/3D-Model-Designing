#!/usr/bin/env python3
from pathlib import Path
import json, numpy as np, trimesh
from OCP.gp import gp_Pnt
from OCP.TColgp import TColgp_HArray1OfPnt
from OCP.GeomAPI import GeomAPI_Interpolate
from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeEdge, BRepBuilderAPI_MakeWire
from OCP.BRepOffsetAPI import BRepOffsetAPI_ThruSections
from OCP.BRepCheck import BRepCheck_Analyzer
from OCP.BRepTools import BRepTools
from OCP.TopAbs import TopAbs_SOLID
from OCP.TopExp import TopExp_Explorer
from OCP.STEPControl import STEPControl_Writer, STEPControl_AsIs
from OCP.IFSelect import IFSelect_RetDone

ROOT=Path(__file__).resolve().parents[1]
CFG=json.loads((ROOT/"config"/"surface_fit.json").read_text())
MASTER=ROOT/"assets"/"Camera_Right_Grip_MASTER_98mm.stl"
OUT=ROOT/"assets"/"smooth"

def area(p):
    xy=p[:,:2]
    return float(0.5*np.sum(xy[:,0]*np.roll(xy[:,1],-1)-np.roll(xy[:,0],-1)*xy[:,1]))

def sample(loop,n):
    p=np.asarray(loop,float)
    if np.linalg.norm(p[0]-p[-1])<1e-7:p=p[:-1]
    if area(p)<0:p=p[::-1]
    idx=np.lexsort((p[:,1],p[:,0]))[-1]
    p=np.roll(p,-int(idx),axis=0)
    c=np.vstack([p,p[0]])
    seg=np.linalg.norm(np.diff(c,axis=0),axis=1); s=np.r_[0,np.cumsum(seg)]
    out=[]
    for t in np.linspace(0,s[-1],n,endpoint=False):
        j=min(np.searchsorted(s,t,side="right")-1,len(seg)-1)
        u=0 if seg[j]<=1e-12 else (t-s[j])/seg[j]
        out.append(c[j]*(1-u)+c[j+1]*u)
    return np.asarray(out)

def wire(points):
    a=TColgp_HArray1OfPnt(1,len(points))
    for i,p in enumerate(points,1):
        a.SetValue(i,gp_Pnt(float(p[0]),float(p[1]),float(p[2])))
    g=GeomAPI_Interpolate(a,True,float(CFG["profile_interpolation_tolerance_mm"])); g.Perform()
    return BRepBuilderAPI_MakeWire(BRepBuilderAPI_MakeEdge(g.Curve()).Edge()).Wire()

def main():
    mesh=trimesh.load(MASTER,force="mesh")
    loft=BRepOffsetAPI_ThruSections(True,False,float(CFG["loft_tolerance_mm"]))
    loft.CheckCompatibility(True)
    for z in CFG["z_sections_mm"]:
        sec=mesh.section(plane_origin=[0,0,float(z)],plane_normal=[0,0,1])
        loop=max(sec.discrete,key=lambda x:float(np.linalg.norm(np.diff(np.asarray(x),axis=0),axis=1).sum()))
        loft.AddWire(wire(sample(loop,int(CFG["profile_points"]))))
    loft.Build()
    if not loft.IsDone():raise RuntimeError("Loft failed")
    shape=loft.Shape()
    if not BRepCheck_Analyzer(shape).IsValid():raise RuntimeError("Invalid BREP")
    e=TopExp_Explorer(shape,TopAbs_SOLID); solids=0
    while e.More():solids+=1;e.Next()
    if solids!=1:raise RuntimeError(f"Expected 1 solid, got {solids}")
    OUT.mkdir(parents=True,exist_ok=True)
    step=OUT/"Camera_Right_Grip_RECONSTRUCTED_SOLID.step"
    brep=OUT/"Camera_Right_Grip_RECONSTRUCTED_SOLID.brep"
    w=STEPControl_Writer();w.Transfer(shape,STEPControl_AsIs)
    if w.Write(str(step))!=IFSelect_RetDone:raise RuntimeError("STEP export failed")
    BRepTools.Write_s(shape,str(brep))
    print(step)

if __name__=="__main__":main()
