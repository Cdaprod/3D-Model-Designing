$fn=28;
MASTER="Camera_Right_Grip_MASTER_98mm.stl";

difference(){ import(MASTER, convexity=10); import("Electronics_Cavity_V2.stl", convexity=10); }
