import kipy
import math
import argparse
import enum

parser = argparse.ArgumentParser(description="Returns an OpenSCAD document to 3D print your active KiCAD PCB")
parser.add_argument("-fa", type=float, default=5, help="Angle step for rendering curves")
parser.add_argument("-fs", type=float, default=0.1, help="Minimum size for rendering curves")
parser.add_argument("--slop", type=float, default=0.05, help="Your 3D printer tolerance -- parts printed this distance apart should fit together snugly")
parser.add_argument("--cut-depth", type=float, default=0.6,help="The distance to press traces down.  Ensure that this shears the copper")
parser.add_argument("--thickness", type=float, default=0.6, help="Dielectric thickness, between copper layers (plus cut-depth)")
parser.add_argument("--spacing", type=float, default=1, help="Space between board layers in export")
args = parser.parse_args()

scad = "include <BOSL2/std.scad>\n\n" + "$fa=" + str(args.fa) + ";\n$fs=" + str(args.fs) + ";\n$slop=" + str(args.slop) + ";\n\ndepth=" + str(args.cut_depth) + ";\nthickness=" + str(args.thickness) + ";\n\n"
origin = kipy.geometry.Vector2()

Shape = enum.Enum('Shape', [('Circle', 1), ('Rectangle', 2), ('Oval', 3), ('Trapezoid', 4), ('RoundedRectangle', 5), ('ChamferedRectangle', 6), ('Custom', 7)])

def radius(center, rad_point):
    x = rad_point.x-center.x
    y = rad_point.y-center.y
    return kipy.util.units.to_mm(math.sqrt(x*x+y*y))

def normalizeX(x):
    return kipy.util.units.to_mm(x-origin.x)

def normalizeY(y):
    return kipy.util.units.to_mm(y-origin.y)

def vToBOSL2Point(vec2):
    return toBOSL2Point(vec2.x,vec2.y)
    
def toBOSL2Point(x,y):
    return "["+str(normalizeX(x))+","+str(normalizeY(y))+"]"
    
def toBOSL2Segment(start, end):
    return "["+vToBOSL2Point(start)+","+vToBOSL2Point(end)+"]"

def toBOSL2Rectangle(top_left, bottom_right):
    return "["+vToBOSL2Point(top_left)+","+toBOSL2Point(bottom_right.x, top_left.y)+","+vToBOSL2Point(bottom_right)+","+toBOSL2Point(top_left.x, bottom_right.y)+"]"

def toBOSL2Arc(start, mid, end):
    return "arc(points=["+vToBOSL2Point(start)+","+vToBOSL2Point(mid)+","+vToBOSL2Point(end)+"])"

def toBOSL2Bezier(start, control1, control2, end):
    return "bezier_curve(["+vToBOSL2Point(start)+","+vToBOSL2Point(control1)+","+vToBOSL2Point(control2)+","+vToBOSL2Point(end)+"])"

def toBOSL2Circle(center, rad):
    return "move("+vToBOSL2Point(center)+",circle("+str(radius(center, rad))+"))"

def toBOSL2Cylinder(center, h, rad, anchor):
    return "move("+vToBOSL2Point(center)+") cylinder(h="+h+",r="+str(rad)+",anchor="+anchor+")"

def toBOSL2RoundedCuboid(pos, angle, size, depth, fillet, anchor):
    return "move("+vToBOSL2Point(pos)+") zrot("+str(angle)+") cuboid(["+str(kipy.util.units.to_mm(size.x))+","+str(kipy.util.units.to_mm(size.y))+","+depth+"],rounding="+str(fillet)+",edges=[FRONT+RIGHT,RIGHT+BACK,BACK+LEFT,LEFT+FRONT],anchor="+anchor+")"
    
def toBOSL2ChamferedCuboid(pos, angle, size, depth, chamfer, corners, fillet, anchor):
    chamcorn = "["
    roundcorn = "["
    for i in range(4):
        if corners[i]:
            chamcorn += str(chamfer)
            roundcorn += "0"
        else:
            chamcorn += "0"
            roundcorn += str(fillet)
        chamcorn += ","
        roundcorn += ","
    chamcorn = chamcorn[:-1] + "]"
    roundcorn = roundcorn[:-1] + "]"
    size = "["+str(kipy.util.units.to_mm(size.x))+","+str(kipy.util.units.to_mm(size.y))+"]"
    return "move("+vToBOSL2Point(pos)+") zrot("+str(angle)+") prismoid(size1="+size+",size2="+size+",h="+depth+",chamfer="+chamcorn+",rounding="+roundcorn+",anchor="+anchor+")"

def toBOSL2Path(polyline):
    output = "concat("
    for node in polyline.nodes:
        if node.has_arc:
            output += toBOSL2Arc(node.arc)
        elif node.has_point:
            output += "["+vToBOSL2Point(node.point)+"]"
        output += ","
    return output[:-1]+")" 

def getOutline(board_shapes):
    if len(board_shapes) == 0:
        return None    
    current_point = None
    outline = "["
    loop = True
    while loop:
        if len(board_shapes) == 0:
            loop = False
        contiguous = False
        for shape in board_shapes:
            if isinstance(shape, kipy.board_types.BoardSegment):
                if current_point == None:
                    outline += "concat("
                    outline += toBOSL2Segment(shape.start, shape.end)
                    current_point = shape.end
                    contiguous = True
                    board_shapes.remove(shape)
                    break
                elif current_point == shape.start:
                    outline += toBOSL2Segment(shape.start, shape.end)
                    current_point = shape.end
                    contiguous = True
                    board_shapes.remove(shape)
                    break
                elif current_point == shape.end:
                    outline += toBOSL2Segment(shape.end, shape.start)
                    current_point = shape.start
                    contiguous = True
                    board_shapes.remove(shape)
                    break
            elif isinstance(shape, kipy.board_types.BoardArc):
                if current_point == None: 
                    outline += "concat("
                    outline += toBOSL2Arc(shape.start, shape.mid, shape.end)
                    current_point = shape.end
                    contiguous = True
                    board_shapes.remove(shape)
                    break
                elif current_point == shape.start:
                    outline += toBOSL2Arc(shape.start, shape.mid, shape.end)
                    current_point = shape.end
                    contiguous = True
                    board_shapes.remove(shape)
                    break
                elif current_point == shape.end:
                    outline +=  toBOSL2Arc(shape.end, shape.mid, shape.start)
                    current_point = shape.start
                    contiguous = True
                    board_shapes.remove(shape)
                    break
            elif isinstance(shape, kipy.board_types.BoardBezier):
                if current_point == None:
                    outline += "concat("
                    outline += toBOSL2Bezier(shape.start, shape.control1, shape.control2, shape.end)
                    current_point = shape.end
                    contiguous = True
                    board_shapes.remove(shape)
                    break                    
                elif current_point == shape.start:
                    outline += toBOSL2Bezier(shape.start, shape.control1, shape.control2, shape.end)
                    current_point = shape.end
                    contiguous = True
                    board_shapes.remove(shape)
                    break
                elif current_point == shape.end:
                    outline += toBOSL2Bezier(shape.end, shape.control2, shape.control1, shape.start)
                    current_point = shape.start
                    contiguous = True
                    board_shapes.remove(shape)
                    break
            elif isinstance(shape, kipy.board_types.BoardRectangle):
                if current_point == None:
                    outline += toBOSL2Rectangle(shape.top_left, shape.bottom_right)
                    contiguous = True
                    board_shapes.remove(shape)
                    break
            elif isinstance(shape, kipy.board_types.BoardPolygon):
                if current_point == None:
                    outline += toBOSL2Path(shape.polygons[0].outline)
                    contiguous = True
                    board_shapes.remove(shape)
                    break    
            elif isinstance(shape, kipy.board_types.BoardCircle):
                if current_point == None:
                    outline += toBOSL2Circle(shape.center, radius(shape.center, shape.radius_point))
                    contiguous = True
                    board_shapes.remove(shape)        
        if contiguous == False:
            current_point = None
            outline = outline[:-1]+")"
        outline += ","
        
    return outline[:-1]+"]"

def genViaDrills(vias, layer1, layer2):
    output = "position(BOTTOM) down(depth+0.01) tag(\"remove\") {"
    no_vias = True
    for via in vias:
        if layer1 in via.padstack.layers and layer2 in via.padstack.layers:
            no_vias = False
            output += toBOSL2Cylinder(via.position, "thickness+depth*2+0.02", kipy.util.units.to_mm(via.drill_diameter/2), "BOTTOM") + "; "
    return "//no vias drilled on this layer" if no_vias else output + "} // via drills"

def genViaPads(vias, layer, plusminus):
    output = ""
    no_vias = True
    for via in vias:
        if layer in via.padstack.layers:
            no_vias = False
            output += toBOSL2Cylinder(via.position, "depth", str(kipy.util.units.to_mm(via.diameter/2)) + plusminus + "get_slop()", "TOP") + "; "
    return None if no_vias else output

def genBtmViaPads(vias, layer):
    BOSLViaPads = genViaPads(vias, layer, "-")
    if BOSLViaPads == None:
        return "//no vias on the bottom of this layer"
    return "position(BOTTOM) up(0.01) { " + BOSLViaPads + "} // bottom via pads"

def genTopViaPads(vias, layer):
    BOSLViaPads = genViaPads(vias, layer, "+")
    if BOSLViaPads == None:
        return "//no vias on the top of this layer"
    return "position(TOP) tag(\"remove\") up(0.01) { " + BOSLViaPads + "}; // top via pads"
    
def genTracks(tracks, plusminus):
    if len(tracks) == 0: 
        return None
    output = ""
    for track in tracks: 
        if isinstance(track, kipy.board_types.Track):
            wid = kipy.util.units.to_mm(track.width)
            output += toBOSL2Cylinder(track.start, "depth", str(wid/2)+plusminus+"get_slop()", "TOP") + "; "
            output += "path_sweep(rect([" + str(wid) + plusminus + "get_slop()*2, depth], anchor=TOP)," + toBOSL2Segment(track.start, track.end) + "); "
            output += toBOSL2Cylinder(track.end, "depth", str(wid/2)+plusminus+"get_slop()", "TOP") + "; "
    return output
        
def genBtmTracks(tracks):
    BOSLTracks = genTracks(tracks, "-")
    if BOSLTracks == None:
        return "//no tracks on the bottom of this layer"
    return "position(BOTTOM) up(0.01) { " + BOSLTracks + "} // bottom tracks"

def genTopTracks(tracks):
    BOSLTracks = genTracks(tracks, "+")
    if BOSLTracks == None:
        return "//no tracks on the top of this layer"
    return "position(TOP) tag(\"remove\") up(0.01) { " + BOSLTracks + "}; // top tracks"

def genPadHoles(pads, layer1, layer2):
    output = "position(BOTTOM) down(depth+0.01) tag(\"remove\") { "
    no_drills = True
    for pad in pads:
        drill = pad.padstack.drill
        if drill.start_layer > layer1 or drill.end_layer < layer2 or drill.diameter.x == 0 or drill.diameter.y == 0:
            continue
        no_drills = False
        fillet = kipy.util.units.to_mm(min(drill.diameter.x, drill.diameter.y)/2)
        output +=  toBOSL2RoundedCuboid(pad.position, pad.padstack.angle.degrees, drill.diameter, "(depth+thickness)*2", fillet, "BOTTOM") + "; "
    return "//no pads drilled on this layer" if no_drills else output + "} // pad drills"

def genPads(pads, layer, plusminus):
    output = ""
    no_pads = True
    for pad in pads:
        if layer in pad.padstack.layers:
            no_pads = False
            shape = pad.padstack.copper_layers[0]
            shapet = Shape(shape.shape)

            if shapet == Shape.Custom:
                shapet = Shape(shape.custom_anchor_shape)
                extras = getOutline(shape.custom_shapes)
                output += "" if extras == None else "extrude_from_to([0,0,0],[0,0,-depth]) region(" + extras + "); "
                
            if shapet == Shape.Circle:
                output += toBOSL2Cylinder(pad.position, "depth", str(kipy.util.units.to_mm(shape.size.x/2)) + plusminus + "get_slop()", "TOP") + "; "
            elif shapet == Shape.Oval:
                fillet = kipy.util.units.to_mm(min(shape.size.x, shape.size.y)/2)
                output +=  toBOSL2RoundedCuboid(pad.position, pad.padstack.angle.degrees, shape.size, "depth", fillet, "TOP") + "; "
            elif shapet == Shape.Rectangle:
                output +=  toBOSL2RoundedCuboid(pad.position, pad.padstack.angle.degrees, shape.size, "depth", 0, "TOP") + "; "
            elif shapet == Shape.RoundedRectangle:
                fillet = kipy.util.units.to_mm(min(shape.size.x, shape.size.y)*shape.corner_rounding_ratio)
                output +=  toBOSL2RoundedCuboid(pad.position, pad.padstack.angle.degrees, shape.size, "depth", fillet, "TOP") + "; "
            elif shapet == Shape.ChamferedRectangle:
                corners = [shape.chamfered_corners.bottom_right, shape.chamfered_corners.top_right, shape.chamfered_corners.top_left, shape.chamfered_corners.bottom_left]
                fillet = kipy.util.units.to_mm(min(shape.size.x, shape.size.y)*shape.corner_rounding_ratio)
                chamfer = kipy.util.units.to_mm(min(shape.size.x, shape.size.y)*shape.chamfer_ratio)
                output += toBOSL2ChamferedCuboid(pad.position, pad.padstack.angle.degrees, shape.size, "depth", chamfer, corners, fillet, "TOP") + "; "
            
    return None if no_pads else output

def genBtmPads(pads, layer):
    BOSLPads = genPads(pads, layer, "-")
    if BOSLPads == None:
        return "//no pads on the bottom of this layer"
    return "position(BOTTOM) up(0.01) { " + BOSLPads + "} // bottom pads"

def genTopPads(pads, layer):
    BOSLPads = genPads(pads, layer, "+")
    if BOSLPads == None:
        return "//no pads on the top of this layer"
    return "position(TOP) tag(\"remove\") up(0.01) { " + BOSLPads + "}; // top pads"

def genZones(zones, layer):
    output = ""
    no_zones = True
    for zone in zones: 
        if layer in zone.layers:
            no_zones = False
            output += "extrude_from_to([0,0,-depth],[0,0,0]) offset(0.01) region("+toBOSL2Path(zone.filled_polygons[layer][0].outline)+"); "
    return None if no_zones else output

def genBtmZones(zones, layer):
    BOSLZones = genZones(zones, layer)
    if BOSLZones == None:
        return "//no zones on the bottom of this layer"
    return "position(BOTTOM) up(0.01) { " + BOSLZones + "} // bottom zones"

def genTopZones(zones, layer):
    BOSLZones = genZones(zones, layer)
    if BOSLZones == None:
        return "//no zones on the top of this layer"
    return "position(TOP) tag(\"remove\") up(0.01) { " + BOSLZones + "}; // top zones"

board = kipy.KiCad().get_board()
origin = board.get_origin(2);

outline = board.get_shapes();

scad += "outline=" + getOutline([shape for shape in outline if shape.layer == kipy.board_types.BoardLayer.BL_Edge_Cuts]) + ";\n"

scad += "module body(t,d) {\n\tattachable(anchor=CENTER,orient=UP,r=0.01,l=t+d) {\n\t\textrude_from_to([0,0,-(t+d)/2],[0,0,(t+d)/2]) region(outline);\n\t\tchildren();\n\t}\n}\n"

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
    scad += "\tdiff() body(thickness, depth) {\n"
    scad += "\t\t" + genTopTracks([track for track in tracks if track.layer == top]) + "\n"
    scad += "\t\t" + genBtmTracks([track for track in tracks if track.layer == btm]) + "\n"
    scad += "\t\t" + genTopViaPads(vias, top) + "\n"
    scad += "\t\t" + genBtmViaPads(vias, btm) + "\n"
    scad += "\t\t" + genTopPads(pads, top) + "\n"
    scad += "\t\t" + genBtmPads(pads, btm) + "\n"
    scad += "\t\t" + genTopZones(zones, top) + "\n"
    scad += "\t\t" + genBtmZones(zones, btm) + "\n"
    scad += "\t\t" + genViaDrills(vias, top, btm) + "\n" 
    scad += "\t\t" + genPadHoles(pads, top, btm) + "\n"
    scad += "\t"+"};\n"
scad += "};"

print(scad)
