import kipy
import math
import argparse
import enum
import subprocess

parser = argparse.ArgumentParser(description="Returns an OpenSCAD document to 3D print your active KiCAD PCB")
parser.add_argument("-fa", type=float, default=5, help="Angle step for rendering curves")
parser.add_argument("-fs", type=float, default=0.1, help="Minimum size for rendering curves")
parser.add_argument("--slop", type=float, default=0.05, help="Your 3D printer tolerance -- parts printed this distance apart should fit together snugly")
parser.add_argument("--cut-depth", type=float, default=0.6,help="The distance to press traces down.  Ensure that this shears the copper")
parser.add_argument("--thickness", type=float, default=0.6, help="Dielectric thickness, between copper layers (plus cut-depth)")
parser.add_argument("--spacing", type=float, default=1, help="Space between board layers in export")
parser.add_argument("--output", type=str,default="output.stl", help="Output filename with desired extension for export.  Supports everything OpenSCAD does plus scad itself and - for stdout")
parser.add_argument("--flip", action="store_true", help="Turn mold inside out -- punch on top and die on bottom")
parser.add_argument("--drill-btm", action="store_true", help="Extend bottom layer drills out of the board")
parser.add_argument("--drill-top", action="store_true", help="Extend top layer drills out of the board")
args = parser.parse_args()

scad = "include <BOSL2/std.scad>\n\n" + "$fa=" + str(args.fa) + ";\n$fs=" + str(args.fs) + ";\n$slop=" + str(args.slop) + ";\n\ndepth=" + str(args.cut_depth) + ";\nthickness=" + str(args.thickness) + ";\n\n"
origin = kipy.geometry.Vector2()

Shape = enum.Enum('Shape', [('Circle', 1), ('Rectangle', 2), ('Oval', 3), ('Trapezoid', 4), ('RoundedRectangle', 5), ('ChamferedRectangle', 6), ('Custom', 7)])

def radius(center, rad_point):
    x = rad_point.x-center.x
    y = rad_point.y-center.y
    return kipy.util.units.to_mm(math.sqrt(x*x+y*y))

def outSize(x,y):
    return "["+str(kipy.util.units.to_mm(x))+","+str(kipy.util.units.to_mm(y))+"]"

def outVecSize(vec2):
    return outSize(vec2.x,vec2.y)

def outPoint(x,y):
    return outSize(x-origin.x, y-origin.y)

def outVecPoint(vec2):
    return outPoint(vec2.x,vec2.y)

def min(vec2):
    return str(min(vec2.x, vec2.y))

def outSegment(start, end):
    return "["+outVecPoint(start)+","+outVecPoint(end)+"]"

def outRectangle(top_left, bottom_right):
    return "["+outVecPoint(top_left)+","+outPoint(bottom_right.x, top_left.y)+","+outVecPoint(bottom_right)+","+outPoint(top_left.x, bottom_right.y)+"]"

def outArc(start, mid, end):
    return "arc(points=["+outVecPoint(start)+","+outVecPoint(mid)+","+outVecPoint(end)+"])"

def outBezier(start, control1, control2, end):
    return "bezier_curve(["+outVecPoint(start)+","+outVecPoint(control1)+","+outVecPoint(control2)+","+outVecPoint(end)+"])"

def outCircle(center, rad):
    return "move("+outVecPoint(center)+",circle("+str(radius(center, rad))+"))"

def outPath(polyline):
    output = "concat("
    for node in polyline.nodes:
        if node.has_arc:
            output += outArc(node.arc)
        elif node.has_point:
            output += "["+outVecPoint(node.point)+"]"
        output += ","
    return output[:-1]+")" 

def getOutline(board_shapes):
    if len(board_shapes) == 0:
        return None    
    current_point = None
    outline = "["
    while True:
        contiguous = False
        for shape in board_shapes:
            if isinstance(shape, kipy.board_types.BoardSegment):
                if current_point == None:
                    outline += "concat("
                    outline += outSegment(shape.start, shape.end)
                    current_point = shape.end
                    contiguous = True
                    board_shapes.remove(shape)
                    break
                elif current_point == shape.start:
                    outline += outSegment(shape.start, shape.end)
                    current_point = shape.end
                    contiguous = True
                    board_shapes.remove(shape)
                    break
                elif current_point == shape.end:
                    outline += outSegment(shape.end, shape.start)
                    current_point = shape.start
                    contiguous = True
                    board_shapes.remove(shape)
                    break
            elif isinstance(shape, kipy.board_types.BoardArc):
                if current_point == None: 
                    outline += "concat("
                    outline += outArc(shape.start, shape.mid, shape.end)
                    current_point = shape.end
                    contiguous = True
                    board_shapes.remove(shape)
                    break
                elif current_point == shape.start:
                    outline += outArc(shape.start, shape.mid, shape.end)
                    current_point = shape.end
                    contiguous = True
                    board_shapes.remove(shape)
                    break
                elif current_point == shape.end:
                    outline +=  outArc(shape.end, shape.mid, shape.start)
                    current_point = shape.start
                    contiguous = True
                    board_shapes.remove(shape)
                    break
            elif isinstance(shape, kipy.board_types.BoardBezier):
                if current_point == None:
                    outline += "concat("
                    outline += outBezier(shape.start, shape.control1, shape.control2, shape.end)
                    current_point = shape.end
                    contiguous = True
                    board_shapes.remove(shape)
                    break                    
                elif current_point == shape.start:
                    outline += outBezier(shape.start, shape.control1, shape.control2, shape.end)
                    current_point = shape.end
                    contiguous = True
                    board_shapes.remove(shape)
                    break
                elif current_point == shape.end:
                    outline += outBezier(shape.end, shape.control2, shape.control1, shape.start)
                    current_point = shape.start
                    contiguous = True
                    board_shapes.remove(shape)
                    break
            elif isinstance(shape, kipy.board_types.BoardRectangle):
                if current_point == None:
                    outline += outRectangle(shape.top_left, shape.bottom_right)
                    contiguous = True
                    board_shapes.remove(shape)
                    break
            elif isinstance(shape, kipy.board_types.BoardPolygon):
                if current_point == None:
                    outline += outPath(shape.polygons[0].outline)
                    contiguous = True
                    board_shapes.remove(shape)
                    break    
            elif isinstance(shape, kipy.board_types.BoardCircle):
                if current_point == None:
                    outline += outCircle(shape.center, radius(shape.center, shape.radius_point))
                    contiguous = True
                    board_shapes.remove(shape)        
        if contiguous == False:
            if current_point != None:
                outline = outline[:-1]+")"
                current_point = None
            else:
                break
        outline += ","
        
    return outline[:-1]+"]"

def genViaDrills(vias, layer1, layer2):
    output = ""
    no_vias = True
    for via in vias:
        if layer1 in via.padstack.layers and layer2 in via.padstack.layers:
            no_vias = False
            output += "posCylinder("+outVecPoint(via.position)+",h=thickness+depth+2+0.02,r="+str(kipy.util.units.to_mm(via.drill_diameter/2))+",add_slop=0); "
    return "//No vias drilled through these layers" if no_vias else output

def genViaPads(vias, layer, add_slop):
    output = ""
    no_vias = True
    for via in vias:
        if layer in via.padstack.layers:
            no_vias = False
            output += "posCylinder("+outVecPoint(via.position)+",h=depth,r="+str(kipy.util.units.to_mm(via.diameter/2))+",add_slop="+str(1 if add_slop else -1)+"); "
    return "//No vias on this layer" if no_vias else output

def genTracks(tracks, add_slop):
    if len(tracks) == 0: 
        return "//No tracks on this layer"
    output = ""
    for track in tracks: 
        if isinstance(track, kipy.board_types.Track):
            output += "cappedSweep("+str(kipy.util.units.to_mm(track.width))+",depth,start="+outVecPoint(track.start)+",end="+outVecPoint(track.end)+",add_slop="+str(1 if add_slop else -1)+"); "
    return output

def genPadHoles(pads, layer1, layer2):
    output = ""
    no_drills = True
    for pad in pads:
        drill = pad.padstack.drill
        if drill.start_layer > layer1 or drill.end_layer < layer2 or drill.diameter.x == 0 or drill.diameter.y == 0:
            continue
        no_drills = False
        output += "posPrismoid("+outVecPoint(pad.position)+",angle="+str(pad.padstack.angle.degrees)+",size="+outVecSize(drill.diameter)+",depth=(depth+thickness)*2,chamfer=0,fillet=0.5,add_slop=0); "
    return "//No pads drilled through these layers" if no_drills else output

def genPads(pads, layer, add_slop):
    output = ""
    no_pads = True
    for pad in pads:
        if layer in pad.padstack.layers:
            no_pads = False
            shape = pad.padstack.copper_layer(layer)
            if shape == None:
                shape = pad.padstack.copper_layers[0]
            shapet = Shape(shape.shape)

            if shapet == Shape.Custom:
                shapet = Shape(shape.custom_anchor_shape)
                extras = getOutline(shape.custom_shapes)
                output += "" if extras == None else "slopRegion("+extras+",start="+("0" if args.flip else "-depth")+",end="+("depth" if args.flip else "0")+",add_slop="+str(1 if add_slop else -1)+"); "
                
            if shapet == Shape.Circle:
                output += "posCylinder("+outVecPoint(pad.position)+", h=depth, r="+str(kipy.util.units.to_mm(shape.size.x/2))+", add_slop="+str(1 if add_slop else -1)+"); "
            elif shapet == Shape.Oval:
                output += "posPrismoid("+outVecPoint(pad.position)+",angle="+str(pad.padstack.angle.degrees)+",size="+outVecSize(shape.size)+",depth=depth,chamfer=0,fillet=0.5,add_slop="+str(1 if add_slop else -1)+"); "
            elif shapet == Shape.Rectangle:
                output +=  "posPrismoid("+outVecPoint(pad.position)+",angle="+str(pad.padstack.angle.degrees)+",size="+outVecSize(shape.size)+",depth=depth,chamfer=0,fillet=0,add_slop="+str(1 if add_slop else -1)+"); "
            elif shapet == Shape.RoundedRectangle:
                output += "posPrismoid("+outVecPoint(pad.position)+",angle="+str(pad.padstack.angle.degrees)+",size="+outVecSize(shape.size)+",depth=depth,chamfer=0,fillet="+str(shape.corner_rounding_ratio)+",add_slop="+str(1 if add_slop else -1)+"); "
            elif shapet == Shape.ChamferedRectangle:
                corners = [shape.chamfered_corners.top_right, shape.chamfered_corners.top_left, shape.chamfered_corners.bottom_left, shape.chamfered_corners.bottom_right]
                fillet = kipy.util.units.to_mm(min(shape.size.x, shape.size.y)*shape.corner_rounding_ratio)
                chamfer = kipy.util.units.to_mm(min(shape.size.x, shape.size.y)*shape.chamfer_ratio)
                chamcorn = "["
                roundcorn = "["
                for i in range(4):
                    if corners[i]:
                        chamcorn += str(shape.chamfer_ratio)
                        roundcorn += "0"
                    else:
                        chamcorn += "0"
                        roundcorn += str(shape.corner_rounding_ratio)
                    chamcorn += ","
                    roundcorn += ","
                chamcorn = chamcorn[:-1] + "]"
                roundcorn = roundcorn[:-1] + "]"
                output += "posPrismoid("+outVecPoint(pad.position)+",angle="+str(pad.padstack.angle.degrees)+",size="+outVecSize(shape.size)+",depth=(depth+thickness)*2,chamfer="+chamcorn+",fillet="+roundcorn+",add_slop="+str(1 if add_slop else -1)+"); "
    return "//No pads on this layer" if no_pads else output

def genZones(zones, layer, add_slop):
    output = ""
    no_zones = True
    for zone in zones: 
        if layer in zone.layers:
            no_zones = False
            output += "slopRegion("+outPath(zone.filled_polygons[layer][0].outline)+",start=0,end=depth,add_slop="+str(1 if add_slop else -1)+"); "
    return "//No zones on this layer" if no_zones else output

board = kipy.KiCad().get_board()
origin = board.get_origin(2);

outline = board.get_shapes();

scad += "outline=" + getOutline([shape for shape in outline if shape.layer == kipy.board_types.BoardLayer.BL_Edge_Cuts]) + ";\n\n"

scad += "module body(t,d) {\n\tattachable(anchor=CENTER,orient=UP,r=0.01,l=t+d) {\n\t\textrude_from_to([0,0,-(t+d)/2],[0,0,(t+d)/2]) region(outline);\n\t\tchildren();\n\t};\n};\n"

scad += "module genTop(flip=1) {\n\tposition(TOP) tag(flip > 0 ? \"remove\" : \"keep\") up(0.01*flip) { down(flip > 0 ? depth : 0) children(); };\n};\n"

scad += "module genBtm(flip=1) {\n\tposition(BOTTOM) tag(flip > 0 ? \"keep\" : \"remove\") up(0.01*flip) { down(flip > 0 ? depth : 0) children(); };\n};\n"

scad += "module genThruHole() {\n\tposition(BOTTOM) down(depth+0.01) tag(\"remove\") { children(); };\n};\n"

scad += "module posCylinder(pos, h, r, add_slop) {\n\tmove(pos) cylinder(h=h,r=r+(add_slop*get_slop()),anchor=BOTTOM);\n};\n"

scad += "module posPrismoid(pos, angle, size, depth, chamfer, fillet, add_slop) {\n\t\ts = add_scalar(size,add_slop*get_slop()*2);\n\t\tmove(pos) zrot(angle) prismoid(size1=s,size2=s,h=depth,chamfer=chamfer*min(s),rounding=fillet*min(s),anchor=BOTTOM); \n};\n"

scad += "module cappedSweep(height,width,start,end,add_slop) {\n\tposCylinder(start,h=depth,r=width/2,add_slop=add_slop);\n\tup(depth/2) path_sweep(rect([width+(add_slop*get_slop()*2), depth]), [start, end]);\n\tposCylinder(end,h=depth,r=width/2,add_slop=add_slop);\n};\n"

scad += "module slopRegion(points,start,end,add_slop) {\n\textrude_from_to([0,0,start],[0,0,end])\n\tif(add_slop > 0) {\n\t\tminkowski(planar=true) {\n\t\t\tregion(points);\n\t\t\tcircle(r=get_slop());\n\t\t};\n\t} else {\n\t\tminkowski_difference(planar=true) {\n\t\t\tregion(points);\n\t\t\tcircle(r=get_slop());\n\t\t};\n\t}\n};\n\n"

layers = [layer.layer for layer in board.get_stackup().layers if layer.material_name == "copper"]
tracks = board.get_tracks()
vias = board.get_vias()
pads = board.get_pads()
zones = board.get_zones()

scad += "distribute("+str(args.spacing)+"+thickness+2*depth, dir=DOWN) {\n"
for i in range(0,len(layers)+1):
    top = 0
    btm = 999999999999
    if i > 0:
        top = layers[i-1]
    if i < len(layers):
        btm = layers[i]

    htop = btm if i == 0 and args.drill_top else top
    hbtm = top if i == len(layers) and args.drill_btm else btm
    
    scad += "\tdiff() body(thickness, depth) {\n"
    scad += "\t\tgenTop("+str(-1 if args.flip else 1)+") {\n"
    scad += "\t\t\t" + genTracks([track for track in tracks if track.layer == top], not args.flip) + "\n"
    scad += "\t\t\t" + genViaPads(vias, top, not args.flip) + "\n"
    scad += "\t\t\t" + genPads(pads, top, not args.flip) + "\n"
    scad += "\t\t\t" + genZones(zones, top, not args.flip) + "\n"
    scad += "\t\t}\n"
    scad += "\t\tgenBtm("+str(-1 if args.flip else 1)+") {\n"
    scad += "\t\t\t" + genTracks([track for track in tracks if track.layer == btm], not args.flip) + "\n"
    scad += "\t\t\t" + genViaPads(vias, btm, args.flip) + "\n"
    scad += "\t\t\t" + genPads(pads, btm, args.flip) + "\n"
    scad += "\t\t\t" + genZones(zones, btm, args.flip) + "\n"
    scad += "\t\t}\n"
    scad += "\t\tgenThruHole() {\n"
    scad += "\t\t\t" + genViaDrills(vias, htop, hbtm) + "\n" 
    scad += "\t\t\t" + genPadHoles(pads, htop, hbtm) + "\n"
    scad += "\t\t};\n\t};\n"
scad += "};"

if args.output == "-":
    print(scad)
elif args.output[-5:] == ".scad":
    with open(args.output,"w",encoding="UTF-8") as f:
        f.write(scad)
else:
    subprocess.run(["openscad", "-", "-o", args.output], input=scad.encode('utf-8'))
