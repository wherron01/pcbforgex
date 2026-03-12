# PCBForgeX
```
usage: pcbforgex.py [-h] [-fa FA] [-fs FS] [--slop SLOP]
                    [--cut-depth CUT_DEPTH] [--thickness THICKNESS]
                    [--spacing SPACING] [--output OUTPUT] [--flip]
                    [--no-drill-ends] [--separate] [--no-mirror]

Outputs a 3D printable die for your active KiCAD PCB, rendered with OpenSCAD

options:
  -h, --help            show this help message and exit
  -fa FA                Angle step for rendering curves (default: 5)
  -fs FS                Minimum size for rendering curves (default: 0.1)
  --slop SLOP           Your 3D printer tolerance -- parts printed this
                        distance apart should fit together snugly (default:
                        0.1)
  --cut-depth CUT_DEPTH
                        The distance to press traces down. Ensure that this
                        shears the copper (default: 1)
  --thickness THICKNESS
                        Dielectric thickness, between copper layers (plus cut-
                        depth) (default: 1)
  --spacing SPACING     Space between board layers in export (default: 2)
  --output OUTPUT       Output filename with desired extension for export.
                        Supports everything OpenSCAD does plus scad itself and
                        - for stdout (default: output.stl)
  --flip                Turn mold inside out -- punch on top and die on
                        bottom. Useful for SMT components on the top layer
                        (default: False)
  --no-drill-ends       Don't extend top and bottom layer drills to the layer
                        caps (default: False)
  --separate            Export each layer as its own file (default: False)
  --no-mirror           Don't mirror the board to match KiCAD. You usually
                        never want this (default: False)
```
To use the generated models:
1. Place copper tape over one half of the first layer,
2. Press the other half of the same layer into it to shear the copper,
3. Separate the two halves,
4. Remove the copper from the negative parts of the layer,
5. Repeat steps 1-4 for each layer,
6. Put the layers back together,
7. Assemble components onto the completed board.  
This method has several advantages over traditional solutions:
1. It can generate as many layers as you want. 50 layer PCB at home? Easy.
2. THT assembly can be solderless, by using the leads to punch through the copper tape.
3. It only uses inexpensive consumables and tools that most hobbyists already have.
The script works on your active PCB document, so you must have it open in KiCAD.
This is because for some reason KiCAD decided to remove API support for their files. 
They now only support IPC with a running KiCAD process. 
You may also need to enable the KiCAD API in the software. 
This script generates a single 3D printable STL by default.
It will need to be split into parts in a slicer.
You can also generate individual files, or files of any standard 3D format.
This script also can skip compilation and give you the generated SCAD file directly.
This is intended for tinkerers who wish to tweak the output beyond these parameters.
This script relies on an external OpenSCAD installation.
If you do not have OpenSCAD, you can still generate scads, but not compile them.
The output, whether internally rendered or not, must have access to pcbforgex.scad.
In turn, pcbforgex.scad must have access to BOSL2, the Belfry OpenSCAD Library.
This is included as a submodule of this repository, which you can clone recursively.
As long as you maintain the directory structure, things should Just Work.
Alternatively, if you already have the library installed, a shallow clone will find it.
This script also has a single python dependency.
Of course, this is the KiCAD API itself.
It should be installable with pip from requirements.txt.
If your system is externally managed, you can install this in a virtual environment.
Using a venv is probably best practice anyways.
