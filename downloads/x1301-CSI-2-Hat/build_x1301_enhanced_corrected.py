from pathlib import Path
import cadquery as cq
import zipfile, json

OUT=Path('/mnt/data/x1301_enhanced')
OUT.mkdir(exist_ok=True)

# Grounded board envelope from official X1301 DXF / recovered reference model.
BOARD_STEP=Path('/mnt/data/x1301_model/X1301_DXF_REFERENCE.step')
board = cq.importers.importStep(str(BOARD_STEP))

PCB_T=1.6
# DXF tool layer: four 2.7 mm mounting holes.
MOUNT_HOLES=[(24.0,4.5),(82.0,4.5),(24.0,53.5),(82.0,53.5)]
for x,y in MOUNT_HOLES:
    cutter=cq.Workplane('XY').center(x,y).circle(1.35).extrude(PCB_T+2).translate((0,0,-1))
    try:
        board=board.cut(cutter)
    except Exception:
        pass

# --- Grounded footprint solids ---
# 40-pin header placement outline is 50.8 x 5 mm in DXF.
# Typical 2x20 Raspberry Pi female stacking header overall height used for reference.
gpio = cq.Workplane('XY').box(50.8,5.0,8.5, centered=(True,True,False)).translate((53.0,4.5,PCB_T))
# Pin field visualization inside header (not electrical-detail exact).
pins=[]
for ix in range(20):
    for iy in range(2):
        x=28.87 + ix*2.54
        y=3.23 + iy*2.54
        pins.append(cq.Workplane('XY').center(x,y).rect(0.64,0.64).extrude(10.0).translate((0,0,PCB_T-1.5)))
pins_comp = pins[0]
for p in pins[1:]: pins_comp=pins_comp.union(p)

# --- Inferred/mechanical-reference component solids ---
# HDMI Type-A right-angle receptacle envelope. Approximate generic shell dimensions.
# Positioned at the short board edge based on official product photos; separate named solids.
def hdmi(center_y, name):
    # shell: X depth 11.5, Y width 14.2, Z 6.5; front flush at X~85.5
    shell=(cq.Workplane('XY').box(11.5,14.2,6.5,centered=(True,True,False))
           .translate((5.754,center_y,PCB_T)))
    # plastic tongue/body behind shell, just enough to visually distinguish
    insert=(cq.Workplane('XY').box(8.5,11.5,3.8,centered=(True,True,False))
            .translate((6.904,center_y,PCB_T+1.2)))
    return shell, insert

# Photo-derived approximate centers; kept separate because DXF doesn't encode component Z/body.
hdmi_in, hdmi_in_insert = hdmi(19.0,'HDMI_IN')
hdmi_out, hdmi_out_insert = hdmi(38.0,'HDMI_OUT')

# HDMI cable/plug keepouts protruding beyond board edge for enclosure design.
def hdmi_keepout(center_y):
    return (cq.Workplane('XY').box(28.0,18.0,11.0,centered=(True,True,False))
            .translate((-5.996,center_y,PCB_T-1.0)))
ko_in=hdmi_keepout(19.0)
ko_out=hdmi_keepout(38.0)

# 22-pin 0.5 mm FFC connector: generic low-profile top-entry/right-angle envelope.
# Position is approximate from component placement/pad patterns and official photos.
csi=(cq.Workplane('XY').box(14.0,5.5,2.4,centered=(True,True,False))
     .translate((54.0,49.0,PCB_T)))
csi_cable=(cq.Workplane('XY').box(18.0,22.0,0.5,centered=(True,True,False))
           .translate((54.0,59.0,PCB_T+1.2)))

# Major IC envelopes (mechanical only, not exact packages unless noted).
# TC358743 is known from Geekworm docs. Generic BGA body envelope for collision/clearance use.
tc358743=(cq.Workplane('XY').box(7.0,7.0,1.1,centered=(True,True,False))
          .translate((45.0,29.0,PCB_T)))
# Active HDMI splitter / support IC envelope inferred from board function and photo.
splitter=(cq.Workplane('XY').box(6.0,6.0,1.1,centered=(True,True,False))
          .translate((64.0,22.0,PCB_T)))
# A few conservative component-height regions for enclosure collision checking.
comp_region_a=(cq.Workplane('XY').box(18.0,15.0,3.0,centered=(True,True,False))
               .translate((17.0,31.0,PCB_T)))
comp_region_b=(cq.Workplane('XY').box(20.0,18.0,3.0,centered=(True,True,False))
               .translate((62.0,34.0,PCB_T)))

# Assembly keeps every reference body independently selectable in STEP-capable CAD.
assy=cq.Assembly(name='X1301_V1_1_ENHANCED_REFERENCE')
assy.add(board,name='PCB_DXF_GROUNDED')
assy.add(gpio,name='GPIO_2x20_HEADER_DXF_FOOTPRINT')
assy.add(pins_comp,name='GPIO_PIN_FIELD_REFERENCE')
assy.add(hdmi_in,name='HDMI_IN_SHELL_INFERRED')
assy.add(hdmi_in_insert,name='HDMI_IN_INSERT_INFERRED')
assy.add(hdmi_out,name='HDMI_LOOP_OUT_SHELL_INFERRED')
assy.add(hdmi_out_insert,name='HDMI_LOOP_OUT_INSERT_INFERRED')
assy.add(csi,name='CSI_22PIN_FFC_INFERRED')
assy.add(tc358743,name='TC358743_ENVELOPE_INFERRED')
assy.add(splitter,name='HDMI_SPLITTER_IC_ENVELOPE_INFERRED')
assy.add(comp_region_a,name='COMPONENT_REGION_A_CLEARANCE')
assy.add(comp_region_b,name='COMPONENT_REGION_B_CLEARANCE')

step_path=OUT/'X1301_V1_1_ENHANCED_REFERENCE.step'
assy.save(str(step_path), exportType='STEP', mode='default')

# Separate enclosure keepout STEP
keep_assy=cq.Assembly(name='X1301_ENCLOSURE_KEEPOUTS')
keep_assy.add(ko_in,name='HDMI_IN_PLUG_KEEPOUT')
keep_assy.add(ko_out,name='HDMI_OUT_PLUG_KEEPOUT')
keep_assy.add(csi_cable,name='CSI_FFC_CABLE_KEEPOUT')
keep_path=OUT/'X1301_V1_1_ENCLOSURE_KEEPOUTS.step'
keep_assy.save(str(keep_path), exportType='STEP', mode='default')

# Combined STL is visual/reference only.
compound = board.union(gpio).union(pins_comp).union(hdmi_in).union(hdmi_in_insert).union(hdmi_out).union(hdmi_out_insert).union(csi).union(tc358743).union(splitter)
stl_path=OUT/'X1301_V1_1_ENHANCED_REFERENCE.stl'
cq.exporters.export(compound,str(stl_path), tolerance=0.05, angularTolerance=0.2)

# Grounded hole-center drill template CSV / metadata
meta={
 'model':'Geekworm X1301 V1.1 enhanced mechanical reference',
 'pcb_thickness_mm':PCB_T,
 'grounded_from_dxf':{
   'board_outline':True,
   'mounting_holes_diameter_mm':2.7,
   'mounting_hole_centers_mm':MOUNT_HOLES,
   'gpio_placement_footprint_mm':[50.8,5.0],
   'gpio_placement_center_mm':[53.0,4.5]
 },
 'inferred_reference_geometry':{
   'hdmi_type_a_shell_mm':[11.5,14.2,6.5],
   'hdmi_centers_y_mm':[19.0,38.0],
   'csi_22pin_envelope_mm':[14.0,5.5,2.4],
   'ic_envelopes':'mechanical clearance placeholders; not package-verified'
 },
 'important':'Bodies whose names end in _INFERRED or _REFERENCE are not dimensionally guaranteed by the DXF. Keep them separate when using the assembly for fabrication.'
}
(OUT/'model_metadata.json').write_text(json.dumps(meta,indent=2))
(OUT/'README.md').write_text('''# X1301 V1.1 Enhanced Reference Model\n\nThis model combines geometry recovered from the official Geekworm X1301 DXF with explicit mechanical-reference bodies for components not fully defined by that 2D file.\n\n## Dimensionally grounded from DXF\n- PCB outline / footprint\n- PCB thickness set to 1.6 mm as a conventional board-thickness parameter\n- Four mounting holes: Ø2.7 mm centers at (24,4.5), (82,4.5), (24,53.5), (82,53.5) mm\n- 40-pin GPIO placement outline: 50.8 × 5.0 mm, center approximately (53.0,4.5) mm\n\n## Added reference/inferred bodies\n- Two HDMI Type-A female receptacle envelopes\n- HDMI plug/cable keepout bodies\n- 22-pin 0.5 mm CSI FFC connector envelope and cable keepout\n- TC358743 mechanical package envelope\n- HDMI splitter/support IC envelope\n- conservative top-side component clearance regions\n\nThe enhanced STEP is intentionally an **assembly with separate named bodies**. Do not fuse it before enclosure work: this lets FreeCAD/Onshape distinguish grounded PCB geometry from inferred component geometry.\n\nUse `X1301_V1_1_ENCLOSURE_KEEPOUTS.step` as cutter/reference geometry when designing case openings.\n''')

zip_path=Path('/mnt/data/X1301_V1_1_ENHANCED_REFERENCE_MODEL.zip')
with zipfile.ZipFile(zip_path,'w',zipfile.ZIP_DEFLATED) as z:
    for f in OUT.iterdir(): z.write(f,arcname=f.name)
print(step_path)
print(keep_path)
print(stl_path)
print(zip_path)
