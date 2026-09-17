$fn=28;
MASTER="Camera_Right_Grip_MASTER_98mm.stl";
cell_0 = [[2.9084,60.2779],[8.5959,61.4452],[13.5970,63.8075],[18.3312,67.6891],[21.6054,72.0873],[21.8090,71.4373],[11.4911,56.4326],[8.8316,55.4652]];
cell_1 = [[17.1711,54.7469],[24.1386,64.9382],[31.4220,44.3844]];
cell_2 = [[-28.8272,51.7132],[-18.9537,53.5645],[-17.7486,52.5603],[-16.9384,44.0537],[-23.2126,41.3088]];
cell_3 = [[-12.0765,52.1041],[-1.0201,56.2504],[5.0953,51.2815],[3.1346,44.4196],[-7.0344,40.4647],[-11.2826,43.7693]];
cell_4 = [[8.5543,42.9917],[10.5981,50.1456],[12.8488,50.9639],[27.5374,40.2813],[16.2516,34.0114]];
cell_5 = [[-20.5343,36.3645],[-14.3342,39.0460],[-10.3017,35.9075],[-10.3016,29.1457],[-14.3687,25.6596]];
cell_6 = [[-4.6983,35.3612],[4.6114,38.9819],[12.5440,29.7271],[10.0832,19.8843],[-4.6983,29.3867]];
cell_7 = [[14.9784,16.3626],[18.0362,28.5928],[33.9532,37.2402],[35.9542,31.1924],[36.5456,27.7691],[32.4676,18.1699],[30.9334,15.9823],[28.4659,13.7248],[24.7140,11.3016],[18.5217,11.3000],[16.8759,14.1563]];
cell_8 = [[-11.5230,20.7189],[-7.2604,24.3725],[-0.6272,20.1085],[-4.8064,18.1178],[-8.2314,15.0036]];
module yz_prism(poly, x0, depth, scale2=1.0) {
    // local extrusion Z -> global X; local X->Y, local Y->Z
    translate([x0,0,0]) rotate([0,90,0])
        linear_extrude(height=depth, center=false, convexity=10, scale=scale2)
            polygon(points=poly);
}
module through_cut(poly) {
    translate([-30,0,0]) rotate([0,90,0])
        linear_extrude(height=60, convexity=10)
            polygon(points=poly);
}
module pocket_plus(poly, depth) {
    // starts beyond +X outer face and tapers inward
    translate([27.0,0,0]) rotate([0,-90,0]) linear_extrude(height=depth, convexity=10, scale=0.72) polygon(points=poly);
}
module pocket_minus(poly, depth) {
    // mirrored construction from -X side
    mirror([1,0,0]) translate([27.0,0,0]) rotate([0,-90,0]) linear_extrude(height=depth, convexity=10, scale=0.72) polygon(points=poly);
}

module raw_cutters(){ union(){
  pocket_plus(cell_0, 17.0);
  through_cut(cell_1);
  pocket_plus(cell_2, 17.0);
  pocket_minus(cell_3, 17.0);
  pocket_plus(cell_4, 17.0);
  through_cut(cell_5);
  pocket_plus(cell_6, 8.5);
  through_cut(cell_7);
  pocket_plus(cell_8, 17.0);
} }

// Remove the protected electronics keepout from every cutter.
module keepout(){
  ellipsoid([-5.5000,10.0000,2.0000], [9.6000,13.2000,7.2000]);
  ellipsoid([-5.0000,10.5000,18.0000], [9.6000,13.2000,7.2000]);
  ellipsoid([-3.5000,7.0000,36.0000], [9.6000,13.2000,7.2000]);
  ellipsoid([-1.0000,1.5000,52.0000], [9.6000,13.2000,7.2000]);
  ellipsoid([1.5000,-7.0000,68.0000], [9.6000,13.2000,7.2000]);
  ellipsoid([1.0000,-9.0000,75.0000], [9.6000,13.2000,7.2000]);
  hull() { ellipsoid([-5.5000,10.0000,2.0000], [9.6000,13.2000,7.2000]); ellipsoid([-5.0000,10.5000,18.0000], [9.6000,13.2000,7.2000]); }
  hull() { ellipsoid([-5.0000,10.5000,18.0000], [9.6000,13.2000,7.2000]); ellipsoid([-3.5000,7.0000,36.0000], [9.6000,13.2000,7.2000]); }
  hull() { ellipsoid([-3.5000,7.0000,36.0000], [9.6000,13.2000,7.2000]); ellipsoid([-1.0000,1.5000,52.0000], [9.6000,13.2000,7.2000]); }
  hull() { ellipsoid([-1.0000,1.5000,52.0000], [9.6000,13.2000,7.2000]); ellipsoid([1.5000,-7.0000,68.0000], [9.6000,13.2000,7.2000]); }
  hull() { ellipsoid([1.5000,-7.0000,68.0000], [9.6000,13.2000,7.2000]); ellipsoid([1.0000,-9.0000,75.0000], [9.6000,13.2000,7.2000]); }
}
module ellipsoid(c,r){translate(c) scale(r) sphere(1);}
difference(){ raw_cutters(); keepout(); }
