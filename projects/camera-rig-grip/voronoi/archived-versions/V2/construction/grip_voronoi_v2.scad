$fn=28;
MASTER="Camera_Right_Grip_MASTER_98mm.stl";

module cavity(){ import("Electronics_Cavity_V2.stl", convexity=10); }
module cutters(){ import("Voronoi_Cutters_V2.stl", convexity=10); }
difference(){ import(MASTER, convexity=10); cavity(); cutters(); }
