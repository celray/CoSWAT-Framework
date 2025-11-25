#!/bin/env python3

'''
this script will dodge vertices of reservoirs touching a stream by
adding one more pixel based on underlying dem to the reservoir and
keeping only corner vertices (not those on a straight line)

Author  : Celray James CHAWANDA
Email   : celray.chawanda@outlook.com
Licence : All rights Reserved
Repo    : https://github.com/celray

Date    : 2025-11-10 - 16:51
'''

# imports
from ccfx import createPath
import rasterio
from shapely.geometry import Point, Polygon, MultiPolygon, LineString
from shapely.ops import unary_union, nearest_points
from collections import defaultdict
import math
import os, geopandas, sys, time, random, itertools

# functions
# helper to extract point coords from various intersection geometries
def extractPointsFromGeom(geom, lake_id, stream_id, distance_val=0.0, seen=set()):
    pts = []
    if geom is None or geom.is_empty:
        return pts
    gtype = geom.geom_type
    if gtype == 'Point':
        coords = [(geom.x, geom.y)]
    elif gtype == 'MultiPoint':
        coords = [(p.x, p.y) for p in geom.geoms]
    elif gtype == 'LineString':
        coords = list(geom.coords)
    elif gtype == 'MultiLineString':
        coords = []
        for ls in geom.geoms:
            coords.extend(list(ls.coords))
    elif gtype == 'GeometryCollection':
        coords = []
        for g in geom.geoms:
            # recursive extraction
            pts.extend(extractPointsFromGeom(g, lake_id, stream_id, distance_val, seen))
            # continue to next
        return pts
    else:
        # fallback: try to get a representative point
        rp = geom.representative_point()
        coords = [(rp.x, rp.y)]

    for xy in coords:
        key = (round(float(xy[0]), 6), round(float(xy[1]), 6))
        if key in seen:
            continue
        seen.add(key)
        pts.append({'geometry': Point(xy), 'lake_id': lake_id, 'stream_id': stream_id, 'distance': float(distance_val)})
    return pts



def determineRelationship(riverRow, reservoirGDF):
    '''
    Determine the relationship of a river segment to reservoir segments.
    Returns:
    0 - touching
    1 - entering
    2 - exiting
    -1 - no relationship
    '''
    riverGeom = riverRow.geometry
    if riverGeom is None or riverGeom.is_empty:
        return -1  # undefined

    startPoint = Point(riverGeom.coords[0])
    endPoint = Point(riverGeom.coords[-1])

    touchingReservoirs = reservoirGDF[reservoirGDF['geometry'].apply(lambda g: g.intersects(riverGeom))]
    for _, resRow in touchingReservoirs.iterrows():
        resGeom = resRow.geometry
        if resGeom is None or resGeom.is_empty:
            continue

        startInside = resGeom.contains(startPoint)
        endInside = resGeom.contains(endPoint)

        if startInside and endInside:
            return 0  # touching
        elif startInside and not endInside:
            return 1  # entering
        elif not startInside and endInside:
            return 2  # exiting
        elif not startInside and not endInside:
            return 3  # touches outside

    return -1  # no relationship found


# then remove coords that are collinear (on straight lines)
def removeCollinearPoints(polygon, tol=1e-6):
    if polygon.geom_type != 'Polygon':
        return polygon

    def is_collinear(p1, p2, p3, tol):
        area = abs((p1[0]*(p2[1]-p3[1]) + p2[0]*(p3[1]-p1[1]) + p3[0]*(p1[1]-p2[1])) / 2.0)
        return area < tol

    new_exterior = []
    coords = list(polygon.exterior.coords)
    n = len(coords)
    for i in range(n):
        p_prev = coords[i - 1]
        p_curr = coords[i]
        p_next = coords[(i + 1) % n]
        if not is_collinear(p_prev, p_curr, p_next, tol):
            new_exterior.append(p_curr)

    return Polygon(new_exterior)



# set default working directory to the script location
os.chdir(os.path.dirname(__file__))

# main code
if __name__ == '__main__':

    import argparse
    import datavariables as variables
    from ccfx import exists, listFolders


    parser = argparse.ArgumentParser(description="a script to dodge reservoir vertices touching streams")
    
    parser.add_argument("r", help="the name of the region to run the model for. If not specified, all regions will be processed.", nargs='*', default=[])
    parser.add_argument("--v", help="the version of the model setup to use. If not specified, the datavariables value will be used.", nargs='?', default=None)

    args = parser.parse_args()

    if len(args.r) > 0:
        regions = args.r
    else: 
        print("please specify at least one region to process")
        sys.exit(1)

    version = variables.version
    if args.v:
        version = args.v

    for region in regions:
        if not exists(f"../model-setup/CoSWATv{version}"):
            print(f'\t! the version, CoSWATv{version}, does not exist, the following versions are available:')
            for v in listFolders('../model-setup/'):
                if v.startswith('CoSWATv'):
                    print(f'\t\t- {v}')
            print(f'\t> please specify a valid version using the --v argument')
            sys.exit(1)
        
        lakesFN         = os.path.abspath(f'../model-setup/CoSWATv{version}/{region}/Watershed/Shapes/lakes-grand-{variables.final_proj_auth}-{variables.final_proj_code}.shp')
        streamsFN       = os.path.abspath(f'../model-setup/CoSWATv{version}/{region}/Watershed/Shapes/dem-aster-{variables.final_proj_auth}-{variables.final_proj_code}channel.shp')
        demFN           = os.path.abspath(f'../model-setup/CoSWATv{version}/{region}/Watershed/Rasters/DEM/dem-aster-{variables.final_proj_auth}-{variables.final_proj_code}.tif')


        # load data    
        dem      = rasterio.open(demFN)
        lakes    = geopandas.read_file(lakesFN)
        streams  = geopandas.read_file(streamsFN)

        # get points at which streams line touches or comes within a small distance of a reservoir edge
        # use a tiny threshold to capture near-misses (in same CRS units, e.g. meters)
        threshold = 0.001
        touchPointsData = []

        seenCoords = set()
        for idx, lake in lakes.iterrows():
            lakeGeom = lake.geometry
            lakeBoundary = lakeGeom.boundary

            for jdx, stream in streams.iterrows():
                streamGeom = stream.geometry

                # compute exact boundary intersection first (can yield multiple points)
                try:
                    inter = lakeBoundary.intersection(streamGeom)
                except Exception:
                    inter = None

                if inter is not None and (not getattr(inter, 'is_empty', False)):
                    pts = extractPointsFromGeom(inter, idx, jdx, 0.0, seenCoords)
                    touchPointsData.extend(pts)
                    continue

                # if no exact intersection, check within threshold (buffered intersection)
                try:
                    dist = lakeBoundary.distance(streamGeom)
                except Exception:
                    dist = float('inf')

                if dist <= threshold:
                    try:
                        inter_buf = lakeBoundary.intersection(streamGeom.buffer(threshold))
                    except Exception:
                        inter_buf = None

                    if inter_buf is not None and (not getattr(inter_buf, 'is_empty', False)):
                        pts = extractPointsFromGeom(inter_buf, idx, jdx, dist, seenCoords)
                        # if buffered intersection returns lines, we may end up with many coords; keep them all deduped
                        touchPointsData.extend(pts)
                    else:
                        # fallback to nearest point on the stream
                        try:
                            p_boundary, p_stream = nearest_points(lakeBoundary, streamGeom)
                            key = (round(float(p_stream.x), 6), round(float(p_stream.y), 6))
                            if key not in seenCoords:
                                seenCoords.add(key)
                                touchPointsData.append({'geometry': p_stream, 'lake_id': idx, 'stream_id': jdx, 'distance': dist})
                        except Exception:
                            rep = streamGeom.representative_point()
                            key = (round(float(rep.x), 6), round(float(rep.y), 6))
                            if key not in seenCoords:
                                seenCoords.add(key)
                                touchPointsData.append({'geometry': rep, 'lake_id': idx, 'stream_id': jdx, 'distance': dist})

        # create GeoDataFrame once, set geometry and CRS to match lakes
        if touchPointsData:
            touchPoints = geopandas.GeoDataFrame(touchPointsData, geometry='geometry', crs=lakes.crs)
        else:
            touchPoints = geopandas.GeoDataFrame(columns=['geometry', 'lake_id', 'stream_id', 'distance'], geometry='geometry', crs=lakes.crs)

        # save touching points to file
        # touchPoints.to_file(outDir + "/touchingPoints.gpkg")

        # for every point in this touchPoints we will extract the riverSegment
        # from the stream we will create three points from the touching point, we will
        # go on either side to the next coods in the stream line and create a linestring
        # then we will save those linestrings to a new geofile

        riverSegmentsData = []
        for idx, tp in touchPoints.iterrows():
            lake_id = tp['lake_id']
            stream_id = tp['stream_id']
            touchPoint = tp['geometry']

            streamGeom = streams.loc[stream_id].geometry
            if streamGeom is None or streamGeom.is_empty:
                print(f"empty stream geometry for stream_id {stream_id}")
                continue

            # find the nearest segment in the stream to the touch point
            nearest_pt_on_stream = streamGeom.interpolate(streamGeom.project(touchPoint))
            # get the coords of the stream line
            stream_coords = list(streamGeom.coords)

            # find the index of the nearest point in the stream coords
            nearest_index = min(range(len(stream_coords)), key=lambda i: Point(stream_coords[i]).distance(nearest_pt_on_stream))

            # get previous and next points if they exist
            if stream_coords[nearest_index] == (touchPoint.x, touchPoint.y):
                prev_index = max(0, nearest_index - 1)
            else:
                prev_index = nearest_index
            next_index = min(len(stream_coords) - 1, nearest_index + 1)

            segment_coords = [stream_coords[prev_index], (touchPoint.x, touchPoint.y), stream_coords[next_index]]
            river_segment = LineString(segment_coords)

            riverSegmentsData.append({'geometry': river_segment, 'lake_id': lake_id, 'stream_id': stream_id})

        # create GeoDataFrame once, set geometry and CRS to match lakes
        if riverSegmentsData:
            riverSegments = geopandas.GeoDataFrame(riverSegmentsData, geometry='geometry', crs=lakes.crs)
            riverSegments = riverSegments.drop_duplicates(subset=['geometry'])
        else:
            riverSegments = geopandas.GeoDataFrame(columns=['geometry', 'lake_id', 'stream_id'], geometry='geometry', crs=lakes.crs)

        # save river segments to file
        # riverSegments.to_file(outDir + "/riverSegments.gpkg")


        # we insert touch points as vertices in the reservoir polygons
        reservoirSegments = []
        for idx, tp in touchPoints.iterrows():
            lake_id = tp['lake_id']
            stream_id = tp['stream_id']
            touchPoint = tp['geometry']

            lakeGeom = lakes.loc[lake_id].geometry
            if lakeGeom is None or lakeGeom.is_empty:
                continue

            # we will now insert the touch point as a vertex in the
            # lake polygon but only if it does not already exist
            if lakeGeom.geom_type == 'Polygon':
                coords = list(lakeGeom.exterior.coords)
                # check if touchPoint already exists as a vertex
                exists = any(abs(c[0] - touchPoint.x) < 1e-6 and abs(c[1] - touchPoint.y) < 1e-6 for c in coords)
                if not exists:
                    # find the segment where the touch point lies
                    insert_index = None
                    for i in range(len(coords)):
                        p1 = coords[i]
                        p2 = coords[(i + 1) % len(coords)]
                        line = LineString([p1, p2])
                        if line.distance(touchPoint) < 1e-6:
                            insert_index = i + 1
                            break
                    if insert_index is not None:
                        new_coords = coords[:insert_index] + [(touchPoint.x, touchPoint.y)] + coords[insert_index:]
                        new_lakeGeom = Polygon(new_coords)
                        lakes.at[lake_id, 'geometry'] = new_lakeGeom
            elif lakeGeom.geom_type == 'MultiPolygon':
                newPolys = []
                for poly in lakeGeom.geoms:
                    coords = list(poly.exterior.coords)
                    # check if touchPoint already exists as a vertex in this poly
                    exists = any(abs(c[0] - touchPoint.x) < 1e-6 and abs(c[1] - touchPoint.y) < 1e-6 for c in coords)
                    if not exists:
                        insert_index = None
                        for i in range(len(coords)):
                            p1 = coords[i]
                            p2 = coords[(i + 1) % len(coords)]
                            line = LineString([p1, p2])
                            if line.distance(touchPoint) < 1e-6:
                                insert_index = i + 1
                                break
                        if insert_index is not None:
                            new_coords = coords[:insert_index] + [(touchPoint.x, touchPoint.y)] + coords[insert_index:]
                            new_poly = Polygon(new_coords)
                            newPolys.append(new_poly)
                        else:
                            newPolys.append(poly)
                    else:
                        newPolys.append(poly)
                lakes.at[lake_id, 'geometry'] = MultiPolygon(newPolys)
        # save updated lakes with touch points inserted as vertices
        # lakes.to_file(outDir + "/updatedLakes.gpkg")


        # we create reservoir segments similarly
        reservoirSegments = []
        for idx, tp in touchPoints.iterrows():
            lake_id = tp['lake_id']
            stream_id = tp['stream_id']
            touchPoint = tp['geometry']

            lakeGeom = lakes.loc[lake_id].geometry
            if lakeGeom is None or lakeGeom.is_empty:
                continue

            # here we will add point before and point after demRes/5m on either side of
            # the touch point but along the lake boundary
            lakeBoundary = lakeGeom.boundary
            lake_boundary_coords = list(lakeBoundary.coords)

            # we find the index of the nearest point in the lake boundary coords
            nearest_index = min(range(len(lake_boundary_coords)), key=lambda i: Point(lake_boundary_coords[i]).distance(touchPoint))
            # sometimes the next index or previous index may be the same as touch point, so we need to check

            if lake_boundary_coords[nearest_index] == (touchPoint.x, touchPoint.y):
                prev_index = max(0, nearest_index - 1)
                next_index = min(len(lake_boundary_coords) - 1, nearest_index + 1)
            else:
                if lake_boundary_coords[nearest_index - 1] == (touchPoint.x, touchPoint.y):
                    prev_index = max(0, nearest_index - 1)
                    next_index = nearest_index
                elif lake_boundary_coords[nearest_index + 1] == (touchPoint.x, touchPoint.y):
                    prev_index = nearest_index
                    next_index = min(len(lake_boundary_coords) - 1, nearest_index + 1)
                else:
                    prev_index = nearest_index
                    next_index = nearest_index + 1

            pointBefore = lake_boundary_coords[prev_index]
            pointAfter = lake_boundary_coords[next_index]

            segment_coords = [pointBefore, (touchPoint.x, touchPoint.y), pointAfter]
            reservoir_segment = LineString(segment_coords)

            reservoirSegments.append({'geometry': reservoir_segment, 'lake_id': lake_id, 'stream_id': stream_id})

        # create GeoDataFrame once, set geometry and CRS to match lakes
        if reservoirSegments:
            reservoirSegments = geopandas.GeoDataFrame(reservoirSegments, geometry='geometry', crs=lakes.crs)
        else:
            reservoirSegments = geopandas.GeoDataFrame(columns=['geometry', 'lake_id', 'stream_id'], geometry='geometry', crs=lakes.crs)

        # save reservoir segments to file
        # reservoirSegments.to_file(outDir + "/reservoirSegments.gpkg")


        # Now that we have river and reservoir segments, further processing can be done as needed
        # we will add a column to the river segments indicating whether it is touching (0) or 
        # is entering (1) the reservoir or is exiting (2) - this can be determined by checking if
        # the segment's endpoints are inside the reservoir polygon (touching) or first point inside
        # second outside (entering) or first point outside second inside (exiting) - this requires
        # spatial joins or point in polygon checks

        # save updated river segments to file
        riverSegments['relationship'] = riverSegments.apply(lambda row: determineRelationship(row, lakes), axis=1)
        # riverSegments.to_file(outDir + "/riverSegments.gpkg")


        # now we will check all touching segments. we will use the touching point as reference and decide which direction
        # (up/down, left/right) the reservoirSegment is located relative to the riverSegment centre.
        # we will save this info in vertical (-1,0,1) and horizontal (-1,0,1) columns in the riverSegments geofile

        for idx, tp in touchPoints.iterrows():
            # find the reservoir segment from reservoirSegments corresponding to this touch point
            # this is not the lake_id but the actual segment touching the point, so need to find intersection

            reservoirSegment = None

            for jdx, resSeg in reservoirSegments.iterrows():
                resGeom = resSeg.geometry
                if resGeom is None or resGeom.is_empty:
                    continue

                if resGeom.distance(tp.geometry) < 1e-6:  # small tolerance
                    reservoirSegment = resGeom
                    break

            # we will compare the average x of all coords in the reservoirSegment to the touch point x
            # and similarly for y to determine left/right and up/down

            if reservoirSegment is None: continue

            res_coords = list(reservoirSegment.coords)
            avg_res_x = sum([c[0] for c in res_coords]) / len(res_coords)
            avg_res_y = sum([c[1] for c in res_coords]) / len(res_coords)

            horiz = 0
            vert = 0
            if avg_res_x < tp.geometry.x:
                horiz = -1  # left
            elif avg_res_x > tp.geometry.x:
                horiz = 1   # right

            if avg_res_y < tp.geometry.y:
                vert = -1  # down
            elif avg_res_y > tp.geometry.y:
                vert = 1   # up

            # save the horizontal and vertical relationship to the river segment
            riverSegments.at[tp.name, 'horizRel'] = horiz
            riverSegments.at[tp.name, 'vertRel'] = vert

        # set horiz and vert to 0 where relationship is entering (1)
        # riverSegments.loc[riverSegments['relationship'].isin([1,]), 'horizRel'] = 0
        # riverSegments.loc[riverSegments['relationship'].isin([1,]), 'vertRel'] = 0

        # save updated river segments to file
        # riverSegments.to_file(outDir + "/riverSegments.gpkg")


        # at this point, we will grow the reservoir polygons by adding pixels in the direction
        # defined by horizRel and vertRel of touching river segments with reference to the touching point
        # if horizRel = -1, we add a pixel to the left of the touch point and if vertRel = 1, we add a
        # pixel above the touch point (first quadrant considering the two directions)... etc.
        # the pixel is determined by the dem resolution (assumed square pixels here for simplicity)
        demResX = dem.res[0]
        demResY = dem.res[1]

        for idx, tp in touchPoints.iterrows():
            # we will add a pixel to the lake polygon in the direction defined by horizRel and vertRel
            # from the touch point, create the pixel from touch point, offset by demResX and demResY
            # for the other three points to make the square pixel

            if (riverSegments.at[tp.name, 'relationship'] == 1) or (riverSegments.at[tp.name, 'relationship'] == 2): continue

            horiz = riverSegments.at[tp.name, 'horizRel']
            vert = riverSegments.at[tp.name, 'vertRel']
            x0, y0 = tp.geometry.x, tp.geometry.y
            x1 = x0 + horiz * demResX
            y1 = y0 + vert * demResY

            # always create a valid square pixel
            pixelCoords = [
                (x0, y0),
                (x1, y0),
                (x1, y1),
                (x0, y1),
                (x0, y0)
            ]
            newPixel = Polygon(pixelCoords)

            lake_id = tp['lake_id']
            lakeGeom = lakes.at[lake_id, 'geometry']
            if lakeGeom is None or lakeGeom.is_empty:
                continue
            lakeGeom = lakeGeom.union(newPixel)
            lakes.at[lake_id, 'geometry'] = lakeGeom

        # at this point, we will shrink the reservoir polygons by moving the touchpoint vertices if the 
        # river segment relationship is 3 (touches outside) we will move it in the direction of the
        # horizRel and vertRel by (demRes/5) m
        for idx, tp in touchPoints.iterrows():

            if riverSegments.at[tp.name, 'relationship'] != 3: continue

            horiz = riverSegments.at[tp.name, 'horizRel']
            vert = riverSegments.at[tp.name, 'vertRel']
            
            # find the coordinates of lake polygon nearest vertice to the touch point
            vertexCoordinates =None
            lake_id = tp['lake_id']
            lakeGeom = lakes.at[lake_id, 'geometry']

            if lakeGeom is None or lakeGeom.is_empty:
                continue
            if lakeGeom.geom_type != 'Polygon':
                continue
            coords = list(lakeGeom.exterior.coords)
            tp_x, tp_y = tp.geometry.x, tp.geometry.y
            nearest_index = min(range(len(coords)), key=lambda i: Point(coords[i]).distance(tp.geometry))
            vertexCoordinates = coords[nearest_index]  

            if vertexCoordinates is None: continue

            vx, vy = vertexCoordinates
            move_x = horiz * (demResX / 5)
            move_y = vert * (demResY / 5)
            new_vx = vx + move_x
            new_vy = vy + move_y

            # update the lake polygon with the moved vertex
            new_coords = coords[:nearest_index] + [(new_vx, new_vy)] + coords[nearest_index+1:]
            new_lakeGeom = Polygon(new_coords)
            original_area = lakeGeom.area
            lakes.at[lake_id, 'geometry'] = new_lakeGeom



        # then remove rings that may have been created by the union operation
        for idx, lake in lakes.iterrows():
            lakeGeom = lake.geometry
            if lakeGeom is None or lakeGeom.is_empty:
                continue

            if lakeGeom.geom_type == 'Polygon':
                # keep only exterior ring
                lakes.at[idx, 'geometry'] = Polygon(lakeGeom.exterior)
            elif lakeGeom.geom_type == 'MultiPolygon':
                # keep only exterior rings of all polygons
                newPolys = [Polygon(p.exterior) for p in lakeGeom.geoms]
                lakes.at[idx, 'geometry'] = MultiPolygon(newPolys)

        # for idx, lake in lakes.iterrows():
        #     lakeGeom = lake.geometry
        #     if lakeGeom is None or lakeGeom.is_empty:
        #         continue

        #     if lakeGeom.geom_type == 'Polygon':
        #         lakes.at[idx, 'geometry'] = removeCollinearPoints(lakeGeom)
        #     elif lakeGeom.geom_type == 'MultiPolygon':
        #         newPolys = [removeCollinearPoints(p) for p in lakeGeom.geoms]
        #         lakes.at[idx, 'geometry'] = MultiPolygon(newPolys)

        # save updated lakes to file
        # lakes.to_file(outDir + "/updatedLakes.gpkg")

        # we will now need to fix entry points (where 'relationship' == 1:)
        # to fix this, we will fist check at what angle the river segment is crossing the
        # reservoir segment. if the angle it 90 degrees (+/- 10 degrees), we will leave it as is
        # if the angle is at 45 degrees (+/- 10 degrees), we will check if the touch point coincides
        # with a vertex of the reservoir segment, if so, we will move the reservoir vertex away from
        # by 100 m perpendicular to the river segment. if there is no coincidence, we will add a
        # vertex and move it 100m away from the reservoir polygon centroid so that the reservoir grows

        for idx, tp in touchPoints.iterrows():
            if (riverSegments.at[tp.name, 'relationship'] != 1) and (riverSegments.at[tp.name, 'relationship'] != 2): continue

            # check if the reservoir segment coords from reservoirSegments corresponding to this touch point
            # form a 90 degree angle

            reservoirSegment = None
            for jdx, resSeg in reservoirSegments.iterrows():
                resGeom = resSeg.geometry
                if resGeom is None or resGeom.is_empty:
                    continue

                if resGeom.distance(tp.geometry) < 1e-6:  # small tolerance
                    reservoirSegment = resGeom
                    break

            if reservoirSegment is None: continue

            # get the angle between the line from centre to one end of the segment and the line from centre to the other end
            segmentCoords = list(reservoirSegment.coords)
            if len(segmentCoords) <= 2:
                # this means the segment is a straight line, so angle is 180 degrees.
                # we will move the vertice in the reservoir polygon at this tp away demRes/5 from centroid for this case
                reservoirCentroid = lakeGeom.centroid
                cx, cy = reservoirCentroid.x, reservoirCentroid.y
                tx, ty = tp.geometry.x, tp.geometry.y
                dx = tx - cx
                dy = ty - cy

                dist = math.sqrt(dx**2 + dy**2)
                if dist > 0:
                    ux = dx / dist
                    uy = dy / dist
                    moveDist = 100  # move 100m away from centroid
                    newTx = tx - ux * moveDist
                    newTy = ty - uy * moveDist
                    coords = list(lakeGeom.exterior.coords)
                    # find if there's a vertex exactly at tp
                    tpIndex = None
                    for i, c in enumerate(coords):
                        if abs(c[0] - tx) < 1e-6 and abs(c[1] - ty) < 1e-6:
                            tpIndex = i
                            break
                    if tpIndex is not None:
                        new_coords = coords[:tpIndex] + [(newTx, newTy)] + coords[tpIndex+1:]
                        new_lakeGeom = Polygon(new_coords)
                        original_area = lakeGeom.area
                        lakeGeom = new_lakeGeom
                        lakes.at[lake_id, 'geometry'] = lakeGeom

                continue
            
            p1 = Point(segmentCoords[0])
            p2 = Point(segmentCoords[1])
            p3 = Point(segmentCoords[2])
            angle = math.degrees(math.atan2(p3.y - p2.y, p3.x - p2.x) - math.atan2(p1.y - p2.y, p1.x - p2.x))
            angle = abs(angle)

            print(f"angle at touch point {tp.name}: {angle}")
            # update river segment angle info
            riverSegments.at[tp.name, 'angle'] = angle

            if (angle != 0) and (angle != 180):
                # we will move that vertex away from the centroid by demRes/5 m
                print(f"non-flat entry at touch point {tp.name}, moving vertex away from centroid")
                lake_id = tp['lake_id']
                lakeGeom = lakes.at[lake_id, 'geometry']
                if not isinstance(lakeGeom, Polygon):
                    continue
                centroid = lakeGeom.centroid
                cx, cy = centroid.x, centroid.y
                tx, ty = tp.geometry.x, tp.geometry.y
                dx = tx - cx
                dy = ty - cy
                dist = math.sqrt(dx**2 + dy**2)
                if dist > 0:
                    ux = dx / dist
                    uy = dy / dist
                    moveDist = demResX/5  # move demResX/5 m away from centroid
                    newTx = tx - ux * moveDist
                    newTy = ty - uy * moveDist
                    coords = list(lakeGeom.exterior.coords)
                    # find if there's a vertex exactly at tp
                    tpIndex = None
                    for i, c in enumerate(coords):
                        if abs(c[0] - tx) < 1e-6 and abs(c[1] - ty) < 1e-6:
                            tpIndex = i
                            break
                    if tpIndex is not None:
                        # move the existing vertex
                        coords[tpIndex] = (newTx, newTy)
                        newLakeGeom = Polygon(coords)
                        originalArea = lakeGeom.area
                        lakes.at[lake_id, 'geometry'] = newLakeGeom
            else:
                # the entry is flat (0 or 180 degrees), move the vertex away from the reservoir centroid by 100m
                print(f"flat entry at touch point {tp.name}, moving vertex away from centroid")
                lake_id = tp['lake_id']
                lakeGeom = lakes.at[lake_id, 'geometry']
                if not isinstance(lakeGeom, Polygon):
                    continue

                centroid = lakeGeom.centroid
                cx, cy = centroid.x, centroid.y
                tx, ty = tp.geometry.x, tp.geometry.y
                dx = tx - cx
                dy = ty - cy
                dist = math.sqrt(dx**2 + dy**2)

                if dist > 0:
                    ux = dx / dist
                    uy = dy / dist
                    moveDist = demResX/5  # move demResX/5 m away from centroid
                    newTx = tx - ux * moveDist
                    newTy = ty - uy * moveDist
                    coords = list(lakeGeom.exterior.coords)
                    # find if there's a vertex exactly at tp
                    tpIndex = None
                    for i, c in enumerate(coords):
                        if abs(c[0] - tx) < 1e-6 and abs(c[1] - ty) < 1e-6:
                            tpIndex = i
                            break
                    if tpIndex is not None:
                        # move the existing vertex
                        coords[tpIndex] = (newTx, newTy)
                        newLakeGeom = Polygon(coords)
                        originalArea = lakeGeom.area
                        lakes.at[lake_id, 'geometry'] = newLakeGeom
                    else:
                        # no vertex at tp, find the segment where tp lies and insert new vertex at tp first, then move it
                        for i in range(len(coords)):
                            p1 = coords[i]
                            p2 = coords[(i + 1) % len(coords)]
                            line = LineString([p1, p2])
                            if line.distance(Point(tx, ty)) < 1e-6:
                                # insert vertex at tp position first, then move it
                                coords.insert(i + 1, (tx, ty))
                                # now move the newly added vertex
                                coords[i + 1] = (newTx, newTy)
                                newLakeGeom = Polygon(coords)
                                originalArea = lakeGeom.area
                                lakes.at[lake_id, 'geometry'] = newLakeGeom
                                break

        # if relationship is 2 (exiting), we will move the vertice if angle is 90 degrees
        for idx, tp in touchPoints.iterrows():
            if riverSegments.at[tp.name, 'relationship'] != 2:
                continue

            angle = riverSegments.at[tp.name, 'angle']
            if angle is None:
                continue

        
            # find the lake polygon and move the vertex away from centroid by demRes/5
            lake_id = tp['lake_id']
            lakeGeom = lakes.at[lake_id, 'geometry']
            if not isinstance(lakeGeom, Polygon):
                continue
            centroid = lakeGeom.centroid
            cx, cy = centroid.x, centroid.y
            tx, ty = tp.geometry.x, tp.geometry.y
            dx = tx - cx
            dy = ty - cy
            dist = math.sqrt(dx**2 + dy**2)
            if dist > 0:
                ux = dx / dist
                uy = dy / dist
                moveDist = demResX / 5  # move by dem resolution / 5
                newTx = tx - ux * moveDist
                newTy = ty - uy * moveDist
                coords = list(lakeGeom.exterior.coords)
                # find if there's a vertex exactly at tp
                tpIndex = None
                for i, c in enumerate(coords):
                    if abs(c[0] - tx) < 1e-6 and abs(c[1] - ty) < 1e-6:
                        tpIndex = i
                        break
                if tpIndex is not None:
                    # move the existing vertex
                    coords[tpIndex] = (newTx, newTy)
                    newLakeGeom = Polygon(coords)
                    originalArea = lakeGeom.area
                    lakes.at[lake_id, 'geometry'] = newLakeGeom


        # remove any polygon that does not intersect with the streams anymore
        for idx, lake in lakes.iterrows():
            lakeGeom = lake.geometry
            if lakeGeom is None or lakeGeom.is_empty:
                continue

            intersects = False
            for jdx, stream in streams.iterrows():
                streamGeom = stream.geometry
                if streamGeom is None or streamGeom.is_empty:
                    continue

                if lakeGeom.intersects(streamGeom):
                    intersects = True
                    break

            if not intersects:
                # remove this lake polygon (by setting to empty geometry)
                lakes.at[idx, 'geometry'] = Polygon()

        # finally find any touchPoints that are still on a polygon vertex, this is unacceptable!
        # we will move those vertices inner by demRes/5 m towards the centroid of the polygon

        for idx, tp in touchPoints.iterrows():
            # we will loop through lake geom to find if that lake geom intersects with the touch point
            # we will do the check literally by intersecting the geometries with tolerance

            lake_id = tp['lake_id']
            lake = lakes.loc[lake_id]
            lakeGeom = lake.geometry
            if lakeGeom is None or lakeGeom.is_empty:
                continue
            if not lakeGeom.intersects(tp.geometry.buffer(1e-6)):
                continue
            if lakeGeom.geom_type != 'Polygon':
                continue

            coords = list(lakeGeom.exterior.coords)
            tp_x, tp_y = tp.geometry.x, tp.geometry.y
            # check if tp coincides with any vertex
            for i, c in enumerate(coords):

                if abs(c[0] - tp_x) < 1e-6 and abs(c[1] - tp_y) < 1e-5:
                    # move this vertex towards centroid by demRes/5 m
                    centroid = lakeGeom.centroid
                    cx, cy = centroid.x, centroid.y
                    dx = cx - tp_x
                    dy = cy - tp_y
                    dist = math.sqrt(dx**2 + dy**2)
                    print(f'found coinciding vertex at {c} for touch point {tp_x}, {tp_y}, moving it inward')
                    if dist > 0:

                        ux = dx / dist
                        uy = dy / dist
                        moveDist = demResX / 5  # move by dem resolution / 5
                        newTx = tp_x + ux * moveDist
                        newTy = tp_y + uy * moveDist
                        coords[i] = (newTx, newTy)
                        newLakeGeom = Polygon(coords)
                        originalArea = lakeGeom.area
                        lakes.at[lake_id, 'geometry'] = newLakeGeom

                
        # remove empty geometries
        lakes = lakes[~lakes['geometry'].is_empty]

        # save updated lakes to file
        lakes.to_file(lakesFN)
        # save updated river segments to file
        riverSegments.to_file(f"{lakesFN.replace('.shp', '_riverSegments.gpkg')}")
        # save reservoir segments to file
        reservoirSegments.to_file(f"{lakesFN.replace('.shp', '_reservoirSegments.gpkg')}")


