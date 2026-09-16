// ============================================
// 20 x 80 mm Perfboard
// ============================================

// ---------- PARAMETERS ----------

board_length = 80;
board_width = 20;
board_thickness = 1.6;

pitch = 2.54;

columns = 28;
rows = 6;

hole_diameter = 1.0;

// Approximate mounting holes
mount_hole_diameter = 2.2;
mount_x_offset = 3.0;
mount_y_offset = 2.5;

// Cylinder smoothness
$fn = 32;


// ---------- CALCULATED VALUES ----------

grid_length = (columns - 1) * pitch;
grid_width = (rows - 1) * pitch;

start_x = (board_length - grid_length) / 2;
start_y = (board_width - grid_width) / 2;


// ---------- PERF HOLES ----------

module perf_holes() {

    for (col = [0 : columns - 1]) {

        for (row = [0 : rows - 1]) {

            x = start_x + col * pitch;
            y = start_y + row * pitch;

            translate([
                x,
                y,
                -0.5
            ])
            cylinder(
                h = board_thickness + 1,
                d = hole_diameter
            );
        }
    }
}


// ---------- MOUNTING HOLES ----------

module mounting_holes() {

    positions = [

        [mount_x_offset,
         mount_y_offset],

        [board_length - mount_x_offset,
         mount_y_offset],

        [mount_x_offset,
         board_width - mount_y_offset],

        [board_length - mount_x_offset,
         board_width - mount_y_offset]
    ];

    for (p = positions) {

        translate([
            p[0],
            p[1],
            -0.5
        ])
        cylinder(
            h = board_thickness + 1,
            d = mount_hole_diameter
        );
    }
}


// ---------- FINAL BOARD ----------

difference() {

    // PCB body
    cube([
        board_length,
        board_width,
        board_thickness
    ]);

    // 2.54 mm perf grid
    perf_holes();

    // Four larger mounting holes
    mounting_holes();
}