# PCBForgeX
```
usage: generateMold.py [-h] [-fa FA] [-fs FS] [--slop SLOP] [--cut-depth CUT_DEPTH] [--thickness THICKNESS] [--spacing SPACING] [--output OUTPUT] [--flip] [--drill-btm] [--drill-top]

Returns an OpenSCAD document to 3D print your active KiCAD PCB

options:
  -h, --help            show this help message and exit
  -fa FA                Angle step for rendering curves
  -fs FS                Minimum size for rendering curves
  --slop SLOP           Your 3D printer tolerance -- parts printed this distance apart should fit together snugly
  --cut-depth CUT_DEPTH
                        The distance to press traces down. Ensure that this shears the copper
  --thickness THICKNESS
                        Dielectric thickness, between copper layers (plus cut-depth)
  --spacing SPACING     Space between board layers in export
  --output OUTPUT       Output filename with desired extension for export. Supports everything OpenSCAD does plus scad itself and - for stdout
  --flip                Turn mold inside out -- punch on top and die on bottom
  --drill-btm           Extend bottom layer drills out of the board
  --drill-top           Extend top layer drills out of the board
```
To use the generated models, place copper tape over the die half of the layer, press the punch half into it to shear the copper, remove the copper from the top that didn't get punched inside, then put the layers back together.  This method can generate as many layers as you want, and THT assembly is solderless (punch the leads through the copper tape).  The script works on your active PCB document, because for some reason KiCAD decided to remove API support for their files, and only support IPC.  It can generate an OpenSCAD file for your editing, or skip straight to compiling it to a 3D printable model.  The generated SCAD files depend on BOSL2, which is provided with this repository via submodule.
