import kipy
import math
import argparse
import enum
import subprocess
import re

parser = argparse.ArgumentParser(description="Returns an OpenSCAD document to 3D print your active KiCAD PCB", formatter_class=argparse.ArgumentDefaultsHelpFormatter)
parser.add_argument("-fa", type=float, default=5, help="Angle step for rendering curves")
parser.add_argument("-fs", type=float, default=0.1, help="Minimum size for rendering curves")
parser.add_argument("--slop", type=float, default=0.1, help="Your 3D printer tolerance -- parts printed this distance apart should fit together snugly")
parser.add_argument("--cut-depth", type=float, default=1,help="The distance to press traces down.  Ensure that this shears the copper")
parser.add_argument("--thickness", type=float, default=1, help="Dielectric thickness, between copper layers (plus cut-depth)")
parser.add_argument("--spacing", type=float, default=2, help="Space between board layers in export")
parser.add_argument("--output", type=str,default="output.stl", help="Output filename with desired extension for export.  Supports everything OpenSCAD does plus scad itself and - for stdout")
parser.add_argument("--flip", action="store_true", help="Turn mold inside out -- punch on top and die on bottom. Useful for SMT components on the top layer")
parser.add_argument("--no-drill-btm", action="store_true", help="Don't extend bottom layer drills out of the board")
parser.add_argument("--no-drill-top", action="store_true", help="Don't xtend top layer drills out of the board")
parser.add_argument("--separate", action="store_true", help="Export each layer as its own file")
parser.add_argument("--no-mirror", action="store_true", help="Don't mirror the board to match KiCAD.  You usually never want this")
args = parser.parse_args()

def outp(o, filename, extension):
    if filename == None:
        print(o)
    elif extension == "scad":
        with open(filename+"."+extension,"w",encoding="UTF-8") as f:
            f.write(o)
    else:
        subprocess.run(["openscad", "-", "-o", filename+"."+extension], input=o.encode('UTF-8'))


header = "include <pcbforgex.scad>\n\n"
mirror = "" if args.no_mirror else "yflip() "
flip = -1 if args.flip else 1

board = kipy.KiCad().get_board()
origin = board.get_origin(2);

def radius(center, rad_point):
    x = rad_point.x-center.x
    y = rad_point.y-center.y
    return kipy.util.units.to_mm(math.sqrt(x*x+y*y))

def shortRound(size, ratio):
    return kipy.util.units.to_mm(min(size.x,size.y)*ratio)

def outSize(x,y):
    return "["+str(kipy.util.units.to_mm(x))+","+str(kipy.util.units.to_mm(y))+"]"

def outVecSize(vec2):
    return outSize(vec2.x,vec2.y)

def outPoint(x,y):
    return outSize(x-origin.x, y-origin.y)

def outVecPoint(vec2):
    return outPoint(vec2.x,vec2.y)

def outCenter(start, end):
    return outPoint((start.x+end.x)/2,(start.y+end.y)/2)

def outSegment(start, end):
    return "["+outVecPoint(start)+","+outVecPoint(end)+"]"

def outRectangle(top_left, bottom_right):
    return "move("+outCenter(top_left, bottom_right)+",rect("+outVecSize(bottom_right-top_left)+"))"

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
    current_point = None
    outline = "[ "
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

def genVias(vias, layer, lookahead):
    output = "[ "
    for via in vias:
        if layer in via.padstack.layers:
            output += "["+("true" if lookahead in via.padstack.layers else "false")+","+outVecPoint(via.position)+","+str(kipy.util.units.to_mm(via.diameter))+","+str(kipy.util.units.to_mm(via.drill_diameter))+"],"
    return output[:-1]+"]"

def genTracks(tracks):
    output = "[ "
    for track in tracks:
        output += "["+str(kipy.util.units.to_mm(track.width))+"," 
        if isinstance(track, kipy.board_types.Track):
            output += outSegment(track.start,track.end)
        if isinstance(track, kipy.board_types.ArcTrack):
            output += outArc(track.start,track.mid,track.end)
        output += "],"
    return output[:-1]+"]"

def genPads(pads, layer, lookahead):
    output = "[ "
    for pad in pads:
        if layer in pad.padstack.layers:
            output += "["+("true" if lookahead in pad.padstack.layers else "false")+", "+outPath(board.get_pad_shapes_as_polygons(pad).outline)+", "+outVecPoint(pad.position)+","+str(pad.padstack.angle.degrees)+","+outVecSize(pad.padstack.drill.diameter)+"],"
    return output[:-1]+"]"

def genZones(zones, layer):
    output = "[ "
    for zone in zones: 
        if layer in zone.layers:
            output += outPath(zone.filled_polygons[layer][0].outline)+","
    return output[:-1]+"]"

shapes = board.get_shapes();

outline = getOutline([shape for shape in shapes if shape.layer == kipy.board_types.BoardLayer.BL_Edge_Cuts])

layers = [layer for layer in board.get_stackup().layers if layer.material_name == "copper"]

tracks = []
vias = []
pads = []
zones = []

outpat = re.match(r'^(.*)\.([a-zA-Z]+?$)', args.output)

filename = None
extension = None

if outpat != None:
    filename = outpat.group(1)
    extension = outpat.group(2)

for i in range(0, len(layers)):
    tracks.append(genTracks([track for track in board.get_tracks() if track.layer == layers[i].layer]))
    vias.append(genVias(board.get_vias(), layers[i].layer, layers[i+1].layer if i < len(layers)-1 else -1))
    pads.append(genPads(board.get_pads(), layers[i].layer, layers[i+1].layer if i < len(layers)-1 else -1))
    zones.append(genZones(board.get_zones(), layers[i].layer))

if args.separate:
    for i in range(0,len(layers)+1):
        top = -1
        btm = math.inf

        topstr = "Structural"
        btmstr = "Structural"

        t1 = "[]"
        v1 = "[]"
        p1 = "[]"
        z1 = "[]"

        t2 = "[]"
        v2 = "[]"
        p2 = "[]"
        z2 = "[]"

        if i > 0:
            t1 = tracks[i-1]
            v1 = vias[i-1]
            p1 = pads[i-1]
            z1 = zones[i-1]
            topstr = layers[i-1].user_name
        if i < len(layers):
            t2 = tracks[i]
            v2 = vias[i]
            p2 = pads[i]
            z2 = zones[i]
            btmstr = layers[i].user_name
        layerstr = None
        if filename != None:
            layerstr = filename + "/" + topstr + "-" + btmstr 
        outp(header+mirror+"genLayer("+outline+","+str(args.thickness)+","+str(args.cut_depth)+","+t1+","+t2+","+v1+","+v2+","+p1+","+p2+","+z1+","+z2+","+str(flip)+",$fa="+str(args.fa)+",$fs="+str(args.fs)+",$slop="+str(args.slop)+");", layerstr, extension)
else:
    outp(header+ "$fa="+str(args.fa)+";\n$fs="+str(args.fs)+";\n$slop="+str(args.slop)+";\n\n""\ndepth="+str(args.cut_depth)+";\nthickness="+str(args.thickness)+";\noutline="+outline+";\ntracks=[[],"+",".join(tracks)+",[]];\nvias=[[],"+",".join(vias)+",[]];\npads=[[],"+",".join(pads)+",[]];\nzones=[[],"+",".join(zones)+",[]];\n\nline_copies(spacing=[0,0,-("+str(args.spacing)+"+thickness+2*depth)], n="+str(len(layers)+1)+") "+mirror+"genLayer(outline, thickness, depth, tracks[$idx], tracks[$idx+1], vias[$idx], vias[$idx+1], pads[$idx], pads[$idx+1], zones[$idx], zones[$idx+1], "+str(flip)+");", filename, extension)
