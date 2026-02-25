include <BOSL2/std.scad>

module body(t,d,outline) {
	attachable(anchor=CENTER,orient=UP,r=0.01,l=t+d) {
		extrude_from_to([0,0,-(t+d)/2],[0,0,(t+d)/2]) region(outline);
		children();
	};
}

module genTop(flip=1,depth) {
	position(TOP) tag(flip > 0 ? "remove" : "") up(0.01*flip) { 
		down(flip > 0 ? depth : 0) children(); 
	};
}

module genBtm(flip=1,depth) {
	position(BOTTOM) tag(flip > 0 ? "" : "remove") up(0.01*flip) { 
		down(flip > 0 ? depth : 0) children(); 
	};
}

module genThruHole(depth) {
	position(BOTTOM) down(depth+0.01) tag("remove") { children(); };
}

module posCylinder(pos, h, r, add_slop) {
	move(pos) cylinder(h=h,r=r+(add_slop*get_slop()),anchor=BOTTOM);
}

module posPrismoid(pos, angle, size, depth, chamfer, fillet, add_slop) {
	s = add_scalar(size,add_slop*get_slop()*2);
	move(pos) zrot(angle) prismoid(size1=s,size2=s,h=depth,chamfer=chamfer*min(s),rounding=fillet*min(s),anchor=BOTTOM); 
}

module slopRegion(points,slop) {
	if(slop == 0) {
		region(points);
	} else if(slop > 0) {
		minkowski() {
			region(points);
			circle(r=get_slop());
		};
	} else {
		minkowski_difference(planar=true) {
			region(points);
			circle(r=get_slop());
		};
	}
}

module genTracks(depth, tracks, slop) {
	for(track=tracks) {
		up(depth/2) path_sweep(rect([track[0]+(slop*get_slop()*2), depth]), track[1]);
		for(point=track[1]) {
			move(point) cylinder(h=depth,r=track[0]/2+(slop*get_slop()),anchor=BOTTOM);
		}
	}
}

module genVias(depth, vias, slop) {
	for(via=vias) {
		move(via[1]) cylinder(h=depth,r=via[2]/2+(slop*get_slop()), anchor=BOTTOM);
	}
}

module genPads(depth, pads, slop) {
	for(pad=pads) {
		linear_extrude(depth) slopRegion(pad[1], slop);
	}
}

module genZones(depth, zones, slop) {
	for(zone=zones) {
		linear_extrude(depth) slopRegion(zone, slop);
	}
}

module genHalfLayer(depth, tracks, vias, pads, zones, slop) {
	genTracks(depth, tracks, slop);
	genVias(depth, vias, slop);
	genPads(depth, pads, slop);
	genZones(depth, zones, slop);
}

module genDrills(thickness, depth, vias, pads) {
	h = thickness+depth*2+0.02;
	for(via=vias) {
		if(via[0]) move(via[1])  cylinder(h=h,r=via[3]/2, anchor=BOTTOM);
	}
	for(pad=pads) {
		if(pad[0]) move(pad[2]) rot(pad[3]) prismoid(size1=pad[4],size2=pad[4],h=h,rounding=min(pad[4])/2,anchor=BOTTOM);
	}
}

module genLayer(outline, thickness, depth, tracks1, tracks2, vias1, vias2, pads1, pads2, zones1, zones2, flip) {
	diff() body(thickness, depth, outline) {
		genTop(flip, depth) genHalfLayer(depth, tracks1, vias1, pads1, zones1, flip);
		genBtm(flip, depth) genHalfLayer(depth, tracks2, vias2, pads2, zones2, flip*-1);
		genThruHole(depth) genDrills(thickness, depth, vias1, pads1);
	}
}
