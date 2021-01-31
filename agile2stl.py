#!/usr/bin/env python3

''' Script to convert an Agile data file into a 3D image '''

import os
import argparse
import numpy as np
import matplotlib.tri as mtri
from stl import mesh

def do_conversion(infile, outfile):
    ''' Convert the image infile to a STL outfile '''
    # Open data file and read into a numpy array
    in_data = np.loadtxt(infile, delimiter=",")
    in_width = len(in_data)
    in_depth = len(in_data[0])

    # At this point, data array width is 365/366 days and
    # depth of 48 half hour slots per day.
    # In order to be able to map to a 3d column, expand each
    # data point to a 3x2 grid.
    # This will also help to easily create the STL triangles
    # later, without turning each data value into a sharp point.
    scale_depth = 3
    scale_width = 2

    # And also add a border around the data, this improves the
    # appearance and more importantly will also close off the edges
    # and help complete the bottom box
    border_size = 10

    # This is therefore the final size of our data array
    scaled_width = (in_width * scale_width) + (2 * border_size)
    scaled_depth = (in_depth * scale_depth) + (2 * border_size)

    # Create the scaled up integer array, including the border
    scaled = np.zeros((scaled_width, scaled_depth), dtype='uint16')

    # Load Convert to integer with offset for max supported -ve value
    # The maximum -ve offset supported (values below this will be clamped)
    max_neg = -10

    for x in range(in_width):
        for y in range(in_depth):
            # Scale the z component, adding max -ve offset
            if in_data[x][y] >= max_neg:
                z = in_data[x][y] - max_neg
            else:
                z = (-max_neg)
            # Store, scaling and applying the border offset
            for xx in range(scale_width):
                for yy in range(scale_depth):
                    scaled[((scale_width * x) + border_size + xx), ((scale_depth * y) + border_size + yy)] = z

    # To close the bottom of the image and create a box of height box_z, we need
    # to add an extra 5 sides made up of 4 vertices and 10 triangles
    box_z = 5
    num_box_extra_vertices = 4
    num_box_extra_triangles = 10

    # Create an array of the (x,y,z) values of all the vertices in the surface
    num_x = len(scaled[0])
    num_y = len(scaled)
    num_vertices = (num_x * num_y) + num_box_extra_vertices
    print((num_x, num_y), num_vertices)
    vertices = np.zeros((num_vertices, 3), dtype=int)
    # Start by loading the extra 4 base vertices
    vertices[0:4] = [[0, 0, 0], [num_x-1, 0, 0], [0, num_y-1, 0], [num_x-1, num_y-1, 0]]
    # Then the image
    i = num_box_extra_vertices
    for y in range(num_y):
        for x in range(num_x):
            vertices[i] = [x, y, (scaled[y][x] + box_z)]
            i = i + 1

    # Create an array of the triange vertices indexes
    # Each triangle is defined by a vector of 3 indexes into the vertices array
    # We can make some assumptions based on our known grid shape, ie:
    #     (x, y)   * n          n+1 * (x+1, y)
    #
    #     (x, y+1) * n+256    n+257 * (x+1, y+1)
    # We can form 2 triangles from the above (using right hand rule (anti-clockwise)):
    #   [n+1, n, n+256] and [n+1, n+256, n+257]
    def get_vertice_index(x_pos, y_pos):
        ''' Given the image pixel (x,y) position, return its index in the vertices array '''
        return x_pos + (y_pos * num_x) + num_box_extra_vertices

    num_triangles = (((num_x - 1) * (num_y - 1)) * 2) + num_box_extra_triangles
    triangles = np.zeros((num_triangles, 3), dtype=int)
    x = 0
    y = 0
    for i in range(0, len(triangles), 2):
        triangles[i] = [get_vertice_index(x+1, y), get_vertice_index(x, y), get_vertice_index(x, y+1)]
        triangles[i+1] = [get_vertice_index(x+1, y), get_vertice_index(x, y+1), get_vertice_index(x+1, y+1)]
        x = x + 1
        if x == (num_x - 1):
            y = y + 1
            x = 0
    i = num_triangles - num_box_extra_triangles

    # Add the base box triangles
    # [[0, 0, 0], [num_x-1, 0, 0], [0, num_y-1, 0], [num_x-1, num_y-1, 0]]
    # Viewed top down:
    #   bottom vertices: 0     1    next layer up:   above_0   above_1
    #                    2     3                     above_2   above_3
    # Viewed from below, this is how we build the triangles:
    #   bottom vertices: 2     3    next layer up:   above_2   above_3
    #                    0     1                     above_0   above_1
    above_0 = 4
    above_1 = 4 + num_x - 1
    above_2 = 4 + num_x * (num_y - 1)
    above_3 = 4 + num_x * num_y - 1
    triangles[i:num_triangles] = [
        [3, 2, 1], [0, 1, 2],  # base 2_triangles (viewed from below)
        [above_0, 0, 2], [2, above_2, above_0], # side 1
        [above_2, 2, 3], [3, above_3, above_2], # side 2
        [above_3, 3, 1], [1, above_1, above_3], # side 3
        [above_1, 1, 0], [0, above_0, above_1]  # side 4
    ]

    tris = mtri.Triangulation(vertices[:, 0], vertices[:, 1], triangles=triangles)

    #=====STL=======
    data = np.zeros(len(tris.triangles), dtype=mesh.Mesh.dtype)
    image_mesh = mesh.Mesh(data, remove_empty_areas=False)
    image_mesh.x[:] = vertices[:, 1][tris.triangles]
    image_mesh.y[:] = vertices[:, 0][tris.triangles]
    image_mesh.z[:] = vertices[:, 2][tris.triangles]
    image_mesh.save(outfile)

# -------------------------------------------------------------------------
# Main entry point
# -------------------------------------------------------------------------

# Create an options parser
PARSER = argparse.ArgumentParser(description="Convert an image to 3D postcard",
                                 fromfile_prefix_chars='@')

PARSER.add_argument('input_file', nargs=1,
                    help='the input image file')

PARSER.add_argument('-o', '--out', metavar='<output file>',
                    dest="output_file",
                    help="the output STL file")

PARSER.add_argument('-v', '--version', action='version', version='%(prog)s 0.1')

# Run the parser, exiting on error
ARGS = PARSER.parse_args()

# If output filename is not specified, build it from input file with .stl extension
if not ARGS.output_file:
    ARGS.output_file = os.path.splitext(ARGS.input_file[0])[0]+'.stl'

# parsed OK, run the command
do_conversion(ARGS.input_file[0], ARGS.output_file)
