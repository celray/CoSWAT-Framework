#!/bin/env  python3

'''

Author  : Celray James CHAWANDA
Email   : celray.chawanda@outlook.com
Licence : All rights Reserved
Repo    : https://github.com/celray

Date    : 2025-11-08 - 13:07
'''

from ccfx import *
import os
import math
import multiprocessing
from collections import deque, defaultdict

import numpy
import pandas
import rasterio
from rasterio.features import geometry_mask, shapes
import geopandas
import shapely
import shapely.geometry
import shapely.ops
import argparse
import datavariables as variables

os.chdir(os.path.dirname(__file__))

dropIncrement = 0.01
geometricTolerance = 1e-8
minimumLength = 1e-6


_parallel_geometry_cache = None
COORD_KEY_PRECISION = 9
COORD_TOLERANCE = 1e-8

try:
    from shapely.validation import make_valid as _shapely_make_valid
except Exception:
    _shapely_make_valid = getattr(shapely, "make_valid", None)


def _coord_key(coord):
    return (round(coord[0], COORD_KEY_PRECISION), round(coord[1], COORD_KEY_PRECISION))


def _coords_match(first, second):
    return abs(first[0] - second[0]) <= COORD_TOLERANCE and abs(first[1] - second[1]) <= COORD_TOLERANCE


def _init_split_pool(geometries):
    global _parallel_geometry_cache
    _parallel_geometry_cache = geometries


def _collect_intersections_for_index(firstIndex: int):
    points = []
    if _parallel_geometry_cache is None:
        return points
    firstGeometry = _parallel_geometry_cache[firstIndex]
    if firstGeometry is None or firstGeometry.is_empty:
        return points
    for secondIndex in range(firstIndex + 1, len(_parallel_geometry_cache)):
        secondGeometry = _parallel_geometry_cache[secondIndex]
        if secondGeometry is None or secondGeometry.is_empty:
            continue
        intersection = firstGeometry.intersection(secondGeometry)
        if intersection.is_empty:
            continue
        if intersection.geom_type == 'Point':
            points.append(intersection)
        elif intersection.geom_type == 'MultiPoint':
            points.extend(list(intersection.geoms))
    return points


def _clean_polygonal_geometry(geometry, *, minimum_area=0.0):
    if geometry is None:
        return geometry
    if _shapely_make_valid is not None:
        try:
            geometry = _shapely_make_valid(geometry)
        except Exception:
            pass
    try:
        if geometry.is_empty:
            return geometry
    except Exception:
        return geometry

    try:
        geometry = geometry.buffer(0)
    except Exception:
        pass

    if geometry.is_empty:
        return geometry

    if isinstance(geometry, shapely.geometry.Polygon):
        return geometry if geometry.area >= minimum_area else shapely.geometry.GeometryCollection()
    if isinstance(geometry, shapely.geometry.MultiPolygon):
        polygons = [poly for poly in geometry.geoms if not poly.is_empty and poly.area >= minimum_area]
        if not polygons:
            return shapely.geometry.GeometryCollection()
        if len(polygons) == 1:
            return polygons[0]
        return shapely.geometry.MultiPolygon(polygons)
    if isinstance(geometry, shapely.geometry.GeometryCollection):
        polygons = []
        for subGeometry in geometry.geoms:
            cleaned = _clean_polygonal_geometry(subGeometry, minimum_area=minimum_area)
            if cleaned is None or cleaned.is_empty:
                continue
            if isinstance(cleaned, shapely.geometry.MultiPolygon):
                polygons.extend(list(cleaned.geoms))
            elif isinstance(cleaned, shapely.geometry.Polygon):
                polygons.append(cleaned)
        if not polygons:
            return shapely.geometry.GeometryCollection()
        if len(polygons) == 1:
            return polygons[0]
        return shapely.geometry.MultiPolygon(polygons)
    return geometry


def enforce_min_gap_between_polygons(geom1, geom2, *, minimum_gap, tolerance=1e-6, minimum_area_ratio=0.1, max_iterations=8):
    if geom1 is None or geom1.is_empty or geom2 is None or geom2.is_empty:
        return geom1, geom2, True, 0

    geom1 = _clean_polygonal_geometry(geom1)
    geom2 = _clean_polygonal_geometry(geom2)
    if geom1 is None or geom2 is None:
        return geom1, geom2, False, 0
    if geom1.is_empty or geom2.is_empty:
        return geom1, geom2, True, 0

    original_area1 = geom1.area
    original_area2 = geom2.area
    if original_area1 == 0 or original_area2 == 0:
        return geom1, geom2, True, 0

    iteration = 0
    width_multiplier = max(minimum_gap * 0.05, tolerance * 10.0)
    success = False

    while iteration < max_iterations:
        distance = geom1.distance(geom2)
        if distance >= minimum_gap - tolerance:
            success = True
            break

        shortfall = minimum_gap - distance
        half_shortfall = max(shortfall / 2.0, tolerance * 10.0)
        width = max(width_multiplier, half_shortfall)

        try:
            nearest_start, nearest_end = shapely.ops.nearest_points(geom1, geom2)
        except Exception:
            break

        separation_axis = shapely.geometry.LineString([nearest_start, nearest_end])
        if separation_axis.length == 0:
            width *= 1.5
            iteration += 1
            width_multiplier = width
            continue

        cut_zone = separation_axis.buffer(width, cap_style='flat')
        if cut_zone.is_empty:
            width *= 1.5
            iteration += 1
            width_multiplier = width
            continue

        cut_zone = _clean_polygonal_geometry(cut_zone)
        if cut_zone is None or cut_zone.is_empty:
            width *= 1.5
            iteration += 1
            width_multiplier = width
            continue

        candidate1 = geom1.difference(cut_zone)
        candidate2 = geom2.difference(cut_zone)

        candidate1 = _clean_polygonal_geometry(candidate1, minimum_area=original_area1 * minimum_area_ratio)
        candidate2 = _clean_polygonal_geometry(candidate2, minimum_area=original_area2 * minimum_area_ratio)

        changed = False
        if candidate1 is not None and not candidate1.is_empty:
            geom1 = candidate1
            changed = True
        if candidate2 is not None and not candidate2.is_empty:
            geom2 = candidate2
            changed = True

        if not changed:
            width *= 1.5
        else:
            width_multiplier = width

        iteration += 1

    if not success:
        distance = geom1.distance(geom2)
        if distance < minimum_gap - tolerance:
            remaining = (minimum_gap - distance) / 2.0
            if remaining > 0:
                shrink_amount = max(remaining, tolerance * 10.0)
                shrink_candidate1 = _clean_polygonal_geometry(geom1.buffer(-shrink_amount), minimum_area=original_area1 * minimum_area_ratio)
                shrink_candidate2 = _clean_polygonal_geometry(geom2.buffer(-shrink_amount), minimum_area=original_area2 * minimum_area_ratio)
                if shrink_candidate1 is not None and not shrink_candidate1.is_empty:
                    geom1 = shrink_candidate1
                if shrink_candidate2 is not None and not shrink_candidate2.is_empty:
                    geom2 = shrink_candidate2
                if geom1.distance(geom2) >= minimum_gap - tolerance:
                    success = True

    return geom1, geom2, success, iteration


def flattenReservoirElevations(demSourcePath: str, reservoirsPath: str):
    with rasterio.open(demSourcePath) as demDataset:
        demArray = demDataset.read(1).astype('float32')
        demMeta = demDataset.meta.copy()

    reservoirsGdf = geopandas.read_file(reservoirsPath)
    combinedLakeGdfs = []

    for reservoirIndex, reservoirRow in reservoirsGdf.iterrows():
        reservoirGeometry = reservoirRow['geometry']
        if reservoirGeometry is None or reservoirGeometry.is_empty:
            continue
        reservoirMask = geometry_mask(
            [reservoirGeometry],
            out_shape=(demMeta['height'], demMeta['width']),
            transform=demMeta['transform'],
            invert=True,
            all_touched=True
        )
        if not numpy.any(reservoirMask):
            continue
        maskedValues = demArray[reservoirMask]
        maskedValues = maskedValues[maskedValues != variables.no_data_value]
        if maskedValues.size == 0:
            continue
        # remove all -999 no data values
        minimumValue = float(maskedValues.min())
        # print(f"minimum value for reservoir index {reservoirIndex} is {minimumValue}")
        demArray[reservoirMask] = minimumValue
        reservoirShapes = shapes(
            demArray,
            mask=reservoirMask,
            transform=demMeta['transform']
        )
        collectedGeometries = []
        for geometryMapping, value in reservoirShapes:
            if value == minimumValue:
                collectedGeometries.append(shapely.geometry.shape(geometryMapping))
        if collectedGeometries:
            combinedLakeGdfs.append(
                geopandas.GeoDataFrame({'geometry': collectedGeometries}, crs=demMeta['crs'])
            )

    if combinedLakeGdfs:
        lakesGdf = geopandas.GeoDataFrame(
            pandas.concat(combinedLakeGdfs, ignore_index=True),
            geometry='geometry',
            crs=demMeta['crs']
        )
    else:
        lakesGdf = geopandas.GeoDataFrame(columns=['geometry'], geometry='geometry', crs=demMeta['crs'])

    return demArray, demMeta, lakesGdf


def identifyTerminalPoints(riverGdf: geopandas.GeoDataFrame, demArray: numpy.ndarray, demTransform):
    rivers = riverGdf.copy()
    rivers = rivers.explode(index_parts=False).reset_index(drop=True)

    unvisited = set(rivers.index)
    structures = []
    
    while unvisited:
        showProgress(len(rivers) - len(unvisited), len(rivers), message="Identifying connected structures...", barLength=40)
        currentStructure = set()
        toVisit = {unvisited.pop()}
        while toVisit:
            currentIndex = toVisit.pop()
            currentStructure.add(currentIndex)
            currentGeometry = rivers.loc[currentIndex].geometry
            connectedIndices = rivers[rivers.geometry.touches(currentGeometry)].index
            for connectedIndex in connectedIndices:
                if connectedIndex in unvisited:
                    unvisited.remove(connectedIndex)
                    toVisit.add(connectedIndex)
        structures.append(currentStructure)

    print(f" -> total structures found: {len(structures)}\n\n")

    points = []
    structureCounter = 0
    structureTotal = len(structures)
    for structure in structures:
        structureCounter += 1
        showProgress(structureCounter, structureTotal, message="Identifying terminal points...", barLength=40)
        structureLines = rivers.loc[list(structure)]
        endpointCounts = {}
        endpointGeometries = {}
        for _, row in structureLines.iterrows():
            lineGeometry = row.geometry
            if lineGeometry is None or lineGeometry.is_empty:
                continue
            startPoint = shapely.geometry.Point(lineGeometry.coords[0])
            endPoint = shapely.geometry.Point(lineGeometry.coords[-1])
            for candidatePoint in [startPoint, endPoint]:
                key = (candidatePoint.x, candidatePoint.y)
                endpointCounts[key] = endpointCounts.get(key, 0) + 1
                endpointGeometries[key] = candidatePoint
        terminalCandidates = [endpointGeometries[key] for key, count in endpointCounts.items() if count == 1]
        if not terminalCandidates:
            continue
        lowestElevation = float('inf')
        downstreamPoint = None
        for candidate in terminalCandidates:
            rowIndex, colIndex = rasterio.transform.rowcol(demTransform, candidate.x, candidate.y)
            if rowIndex < 0 or rowIndex >= demArray.shape[0] or colIndex < 0 or colIndex >= demArray.shape[1]:
                continue
            candidateElevation = demArray[rowIndex, colIndex]
            if candidateElevation < lowestElevation:
                lowestElevation = candidateElevation
                downstreamPoint = candidate
        if downstreamPoint is not None:
            points.append(downstreamPoint)

    terminalPointsGdf = geopandas.GeoDataFrame(geometry=points, crs=rivers.crs)
    return terminalPointsGdf


def splitToSegments(gdf: geopandas.GeoDataFrame) -> geopandas.GeoDataFrame:
    global _parallel_geometry_cache
    intersectionPoints = []
    print()
    geometryList = list(gdf.geometry)
    totalGeometries = len(geometryList)
    processCount = getattr(variables, 'processes', 1) or 1
    processCount = max(1, min(totalGeometries, int(processCount)))

    if processCount > 1 and totalGeometries > 0:
        with multiprocessing.Pool(processCount, initializer=_init_split_pool, initargs=(geometryList,)) as pool:
            for completed, points in enumerate(pool.imap_unordered(_collect_intersections_for_index, range(totalGeometries)), start=1):
                showProgress(completed, totalGeometries, message="Identifying intersection points...", barLength=40)
                if points:
                    intersectionPoints.extend(points)
        _parallel_geometry_cache = None
    else:
        counter = 0
        for firstIndex, firstGeometry in enumerate(geometryList):
            counter += 1
            showProgress(counter, totalGeometries, message="Identifying intersection points...", barLength=40)
            if firstGeometry is None or firstGeometry.is_empty:
                continue
            for secondIndex in range(firstIndex + 1, totalGeometries):
                secondGeometry = geometryList[secondIndex]
                if secondGeometry is None or secondGeometry.is_empty:
                    continue
                intersection = firstGeometry.intersection(secondGeometry)
                if intersection.is_empty:
                    continue
                if intersection.geom_type == 'Point':
                    intersectionPoints.append(intersection)
                elif intersection.geom_type == 'MultiPoint':
                    intersectionPoints.extend(list(intersection.geoms))

    uniqueIntersectionPoints = []
    seenPointKeys = set()
    for point in intersectionPoints:
        try:
            key = _coord_key((point.x, point.y))
        except Exception:
            continue
        if key in seenPointKeys:
            continue
        seenPointKeys.add(key)
        uniqueIntersectionPoints.append(point)

    splitGeometries = []
    attributeRecords = []

    counter = 0
    totalRows = len(gdf)
    for _, row in gdf.iterrows():
        counter += 1
        showProgress(counter, totalRows, message="Splitting geometries at intersection points...", barLength=40)
        line = row.geometry
        segmentsToProcess = [line]
        for intersectionPoint in uniqueIntersectionPoints:
            updatedSegments = []
            for segment in segmentsToProcess:
                if segment.intersects(intersectionPoint) and not segment.touches(intersectionPoint):
                    splitResult = shapely.ops.split(segment, intersectionPoint)
                    if hasattr(splitResult, 'geoms'):
                        updatedSegments.extend(list(splitResult.geoms))
                    else:
                        updatedSegments.append(splitResult)
                else:
                    updatedSegments.append(segment)
            segmentsToProcess = updatedSegments
        for segment in segmentsToProcess:
            if segment.geom_type == 'LineString' and len(segment.coords) > 1:
                splitGeometries.append(segment)
                attributeRecords.append(row.drop('geometry').to_dict())

    if attributeRecords:
        return geopandas.GeoDataFrame(attributeRecords, geometry=splitGeometries, crs=gdf.crs)
    return geopandas.GeoDataFrame({'geometry': splitGeometries}, crs=gdf.crs)


def orientRiverNetwork(riverGdf: geopandas.GeoDataFrame, terminalPointsGdf: geopandas.GeoDataFrame):
    river = splitToSegments(riverGdf)
    river = river.reset_index(drop=True)

    segmentCount = len(river)
    if segmentCount == 0:
        return river

    coordsCache = []
    adjacency = defaultdict(list)
    for index in range(segmentCount):
        geometry = river.at[index, 'geometry']
        if geometry is None or geometry.is_empty:
            coordsCache.append([])
            continue
        coords = list(geometry.coords)
        coordsCache.append(coords)
        if len(coords) < 2:
            continue
        startKey = _coord_key(coords[0])
        endKey = _coord_key(coords[-1])
        adjacency[startKey].append((index, True))
        adjacency[endKey].append((index, False))

    visited = [False] * segmentCount
    queue = deque()
    enqueued = set()
    processedCount = 0

    def process_queue():
        nonlocal processedCount
        while queue:
            segmentIndex, targetCoord = queue.popleft()
            if visited[segmentIndex]:
                continue
            coords = coordsCache[segmentIndex]
            if len(coords) < 2:
                visited[segmentIndex] = True
                continue
            if not _coords_match(coords[0], targetCoord):
                if _coords_match(coords[-1], targetCoord):
                    coords = list(reversed(coords))
                    coordsCache[segmentIndex] = coords
                else:
                    startDistance = math.hypot(coords[0][0] - targetCoord[0], coords[0][1] - targetCoord[1])
                    endDistance = math.hypot(coords[-1][0] - targetCoord[0], coords[-1][1] - targetCoord[1])
                    if endDistance < startDistance:
                        coords = list(reversed(coords))
                        coordsCache[segmentIndex] = coords
            visited[segmentIndex] = True
            processedCount += 1
            showProgress(processedCount, segmentCount, message="orienting river segments...", barLength=40)
            for coordinate in coords[1:]:
                neighborKey = _coord_key(coordinate)
                for neighborIndex, _ in adjacency.get(neighborKey, []):
                    if neighborIndex == segmentIndex or visited[neighborIndex]:
                        continue
                    pairKey = (neighborIndex, neighborKey)
                    if pairKey in enqueued:
                        continue
                    queue.append((neighborIndex, coordinate))
                    enqueued.add(pairKey)

    for _, terminalRow in terminalPointsGdf.iterrows():
        point = terminalRow.geometry
        if point is None or point.is_empty:
            continue
        targetCoord = (point.x, point.y)
        targetKey = _coord_key(targetCoord)
        for segmentIndex, _ in adjacency.get(targetKey, []):
            if visited[segmentIndex]:
                continue
            pairKey = (segmentIndex, targetKey)
            if pairKey in enqueued:
                continue
            queue.append((segmentIndex, targetCoord))
            enqueued.add(pairKey)

    process_queue()

    for segmentIndex in range(segmentCount):
        if visited[segmentIndex]:
            continue
        coords = coordsCache[segmentIndex]
        if len(coords) < 2:
            visited[segmentIndex] = True
            continue
        targetCoord = coords[0]
        targetKey = _coord_key(targetCoord)
        pairKey = (segmentIndex, targetKey)
        if pairKey not in enqueued:
            queue.append((segmentIndex, targetCoord))
            enqueued.add(pairKey)
        process_queue()

    finalGeometries = []
    for index in range(segmentCount):
        coords = coordsCache[index]
        if len(coords) >= 2:
            finalGeometries.append(shapely.geometry.LineString(list(reversed(coords))))
        else:
            finalGeometries.append(river.at[index, 'geometry'])

    river = river.set_geometry(geopandas.GeoSeries(finalGeometries, crs=river.crs))
    return river


def collectLineStrings(geom):
    if geom is None or geom.is_empty:
        return []
    if isinstance(geom, shapely.geometry.LineString):
        return [geom] if len(geom.coords) > 1 else []
    if isinstance(geom, shapely.geometry.MultiLineString):
        return [segment for segment in geom.geoms if len(segment.coords) > 1]
    if isinstance(geom, shapely.geometry.GeometryCollection):
        segments = []
        for subGeometry in geom.geoms:
            segments.extend(collectLineStrings(subGeometry))
        return segments
    return []


def getReservoirIds(point, reservoirRecords):
    matchingIds = []
    for reservoirId, reservoirGeometry in reservoirRecords:
        if reservoirGeometry is None or reservoirGeometry.is_empty:
            continue
        try:
            if reservoirGeometry.covers(point) or reservoirGeometry.distance(point) <= geometricTolerance:
                matchingIds.append(reservoirId)
        except Exception:
            bufferedGeometry = reservoirGeometry.buffer(0)
            if bufferedGeometry.covers(point) or bufferedGeometry.distance(point) <= geometricTolerance:
                matchingIds.append(reservoirId)
    return matchingIds


def splitLineIntoPieces(line, reservoirUnion, reservoirRecords, reservoirBoundary):
    if line is None or line.is_empty or len(line.coords) < 2:
        return []
    boundaryGeometry = reservoirBoundary
    if boundaryGeometry is not None and not boundaryGeometry.is_empty:
        try:
            splitResult = shapely.ops.split(line, boundaryGeometry)
        except Exception:
            boundaryGeometry = reservoirUnion.buffer(0).boundary
            splitResult = shapely.ops.split(line, boundaryGeometry)
    else:
        splitResult = line
    if isinstance(splitResult, shapely.geometry.LineString):
        candidateSegments = [splitResult]
    else:
        candidateSegments = [segment for segment in getattr(splitResult, 'geoms', []) if isinstance(segment, shapely.geometry.LineString)]
    orderedSegments = []
    for segment in candidateSegments:
        if len(segment.coords) <= 1 or segment.length <= minimumLength:
            continue
        startPoint = shapely.geometry.Point(segment.coords[0])
        orderValue = line.project(startPoint)
        orderedSegments.append((orderValue, segment))
    if not orderedSegments:
        return []
    orderedSegments.sort(key=lambda item: item[0])
    pieces = []
    for _, segment in orderedSegments:
        midpoint = segment.interpolate(0.5, normalized=True)
        insideReservoir = False
        if reservoirUnion is not None and not reservoirUnion.is_empty:
            try:
                insideReservoir = reservoirUnion.contains(midpoint)
                if not insideReservoir and reservoirUnion.distance(midpoint) <= geometricTolerance:
                    insideReservoir = True
            except Exception:
                bufferedUnion = reservoirUnion.buffer(0)
                insideReservoir = bufferedUnion.contains(midpoint)
                if not insideReservoir and bufferedUnion.distance(midpoint) <= geometricTolerance:
                    insideReservoir = True
        segmentStartPoint = shapely.geometry.Point(segment.coords[0])
        segmentEndPoint = shapely.geometry.Point(segment.coords[-1])
        segmentStartReservoirIds = getReservoirIds(segmentStartPoint, reservoirRecords)
        segmentEndReservoirIds = getReservoirIds(segmentEndPoint, reservoirRecords)
        if not insideReservoir and segmentStartReservoirIds and segmentEndReservoirIds and segmentStartReservoirIds == segmentEndReservoirIds:
            insideReservoir = True
        pieces.append({
            'geometry': segment,
            'inside': insideReservoir,
            'startReservoirIds': segmentStartReservoirIds,
            'endReservoirIds': segmentEndReservoirIds
        })
    return pieces


def determineTrimmedSegment(segmentGeometry, reservoirUnion, reservoirRecords, reservoirBoundary):
    if segmentGeometry is None or segmentGeometry.is_empty or len(segmentGeometry.coords) < 2:
        return {
            'trimmedGeometry': None,
            'trimmedStartReservoirIds': [],
            'trimmedEndReservoirIds': [],
            'startInsideOriginal': False,
            'endInsideOriginal': False,
            'originalStartReservoirIds': [],
            'originalEndReservoirIds': [],
            'hadInteriorIntersection': False
        }

    originalStartPoint = shapely.geometry.Point(segmentGeometry.coords[0])
    originalEndPoint = shapely.geometry.Point(segmentGeometry.coords[-1])
    originalStartReservoirIds = getReservoirIds(originalStartPoint, reservoirRecords)
    originalEndReservoirIds = getReservoirIds(originalEndPoint, reservoirRecords)
    startInsideOriginal = bool(originalStartReservoirIds)
    endInsideOriginal = bool(originalEndReservoirIds)

    pieces = splitLineIntoPieces(segmentGeometry, reservoirUnion, reservoirRecords, reservoirBoundary)
    if not pieces:
        return {
            'trimmedGeometry': segmentGeometry,
            'trimmedStartReservoirIds': originalStartReservoirIds,
            'trimmedEndReservoirIds': originalEndReservoirIds,
            'startInsideOriginal': startInsideOriginal,
            'endInsideOriginal': endInsideOriginal,
            'originalStartReservoirIds': originalStartReservoirIds,
            'originalEndReservoirIds': originalEndReservoirIds,
            'hadInteriorIntersection': False
        }

    insidePiecesExist = any(piece['inside'] for piece in pieces)

    if not insidePiecesExist:
        return {
            'trimmedGeometry': segmentGeometry,
            'trimmedStartReservoirIds': originalStartReservoirIds,
            'trimmedEndReservoirIds': originalEndReservoirIds,
            'startInsideOriginal': startInsideOriginal,
            'endInsideOriginal': endInsideOriginal,
            'originalStartReservoirIds': originalStartReservoirIds,
            'originalEndReservoirIds': originalEndReservoirIds,
            'hadInteriorIntersection': insidePiecesExist
        }

    firstOutsidePiece = next((piece for piece in pieces if not piece['inside']), None)
    lastOutsidePiece = next((piece for piece in reversed(pieces) if not piece['inside']), None)

    trimmedPiece = None
    if not startInsideOriginal:
        trimmedPiece = firstOutsidePiece
    elif startInsideOriginal and not endInsideOriginal:
        trimmedPiece = lastOutsidePiece
    elif startInsideOriginal and endInsideOriginal:
        if set(originalStartReservoirIds) != set(originalEndReservoirIds):
            trimmedPiece = lastOutsidePiece
        else:
            trimmedPiece = None
    else:
        trimmedPiece = firstOutsidePiece

    if trimmedPiece is None:
        return {
            'trimmedGeometry': None,
            'trimmedStartReservoirIds': [],
            'trimmedEndReservoirIds': [],
            'startInsideOriginal': startInsideOriginal,
            'endInsideOriginal': endInsideOriginal,
            'originalStartReservoirIds': originalStartReservoirIds,
            'originalEndReservoirIds': originalEndReservoirIds,
            'hadInteriorIntersection': insidePiecesExist
        }

    trimmedGeometry = trimmedPiece['geometry']
    trimmedStartReservoirIds = trimmedPiece['startReservoirIds']
    trimmedEndReservoirIds = trimmedPiece['endReservoirIds']

    if trimmedGeometry is None or trimmedGeometry.is_empty or trimmedGeometry.length <= minimumLength:
        return {
            'trimmedGeometry': None,
            'trimmedStartReservoirIds': [],
            'trimmedEndReservoirIds': [],
            'startInsideOriginal': startInsideOriginal,
            'endInsideOriginal': endInsideOriginal,
            'originalStartReservoirIds': originalStartReservoirIds,
            'originalEndReservoirIds': originalEndReservoirIds,
            'hadInteriorIntersection': insidePiecesExist
        }

    if not trimmedStartReservoirIds:
        trimmedStartReservoirIds = getReservoirIds(shapely.geometry.Point(trimmedGeometry.coords[0]), reservoirRecords)
    if not trimmedEndReservoirIds:
        trimmedEndReservoirIds = getReservoirIds(shapely.geometry.Point(trimmedGeometry.coords[-1]), reservoirRecords)

    if insidePiecesExist and reservoirBoundary is not None and not reservoirBoundary.is_empty:
        coordinates = list(trimmedGeometry.coords)
        startPoint = shapely.geometry.Point(coordinates[0])
        endPoint = shapely.geometry.Point(coordinates[-1])
        expectStartTouch = startInsideOriginal
        expectEndTouch = endInsideOriginal or (insidePiecesExist and not startInsideOriginal)
        geometryUpdated = False

        if expectStartTouch and not trimmedStartReservoirIds:
            projectedStart = reservoirBoundary.interpolate(reservoirBoundary.project(startPoint))
            trimmedStartReservoirIds = getReservoirIds(projectedStart, reservoirRecords)
            if trimmedStartReservoirIds and startPoint.distance(projectedStart) > geometricTolerance:
                coordinates[0] = (projectedStart.x, projectedStart.y)
                geometryUpdated = True

        if expectEndTouch and not trimmedEndReservoirIds:
            projectedEnd = reservoirBoundary.interpolate(reservoirBoundary.project(endPoint))
            trimmedEndReservoirIds = getReservoirIds(projectedEnd, reservoirRecords)
            if trimmedEndReservoirIds and endPoint.distance(projectedEnd) > geometricTolerance:
                coordinates[-1] = (projectedEnd.x, projectedEnd.y)
                geometryUpdated = True

        if geometryUpdated:
            trimmedGeometry = shapely.geometry.LineString(coordinates)
            if not trimmedStartReservoirIds and expectStartTouch:
                trimmedStartReservoirIds = getReservoirIds(shapely.geometry.Point(coordinates[0]), reservoirRecords)
            if not trimmedEndReservoirIds and expectEndTouch:
                trimmedEndReservoirIds = getReservoirIds(shapely.geometry.Point(coordinates[-1]), reservoirRecords)

    return {
        'trimmedGeometry': trimmedGeometry,
        'trimmedStartReservoirIds': trimmedStartReservoirIds,
        'trimmedEndReservoirIds': trimmedEndReservoirIds,
        'startInsideOriginal': startInsideOriginal,
        'endInsideOriginal': endInsideOriginal,
        'originalStartReservoirIds': originalStartReservoirIds,
        'originalEndReservoirIds': originalEndReservoirIds,
        'hadInteriorIntersection': insidePiecesExist
    }


def reconcileRiverTopology(riverGdf: geopandas.GeoDataFrame, reservoirsGdf: geopandas.GeoDataFrame):
    river = riverGdf.explode(index_parts=False).reset_index(drop=True)
    reservoirs = reservoirsGdf.copy()

    if river.empty:
        print(f"no river segments available for reconciliation")
        return river, {'processed': 0, 'trimmed': 0, 'removed': 0, 'exitPruned': 0}

    if reservoirs.empty:
        print(f"no reservoirs available for reconciliation")
        return river, {'processed': len(river), 'trimmed': 0, 'removed': 0, 'exitPruned': 0}

    if river.crs and reservoirs.crs and river.crs != reservoirs.crs:
        reservoirs = reservoirs.to_crs(river.crs)

    reservoirUnion = shapely.ops.unary_union(reservoirs.geometry)
    reservoirBoundary = reservoirUnion.boundary if reservoirUnion is not None and not reservoirUnion.is_empty else None
    reservoirRecords = [(reservoirIndex, reservoirGeometry) for reservoirIndex, reservoirGeometry in zip(reservoirs.index, reservoirs.geometry)]

    processedSegments = []
    for segmentIndex, segmentRow in river.iterrows():
        lineGeometry = segmentRow.geometry
        if lineGeometry is None or lineGeometry.is_empty:
            continue
        geometryParts = [lineGeometry] if isinstance(lineGeometry, shapely.geometry.LineString) else collectLineStrings(lineGeometry)
        if not geometryParts:
            continue
        for partGeometry in geometryParts:
            if partGeometry is None or partGeometry.is_empty or partGeometry.length <= minimumLength:
                continue
            trimmingResult = determineTrimmedSegment(partGeometry, reservoirUnion, reservoirRecords, reservoirBoundary)
            processedSegments.append({
                'index': segmentIndex,
                'attributes': segmentRow.drop(labels='geometry').to_dict(),
                'originalGeometry': partGeometry,
                'trimmedGeometry': trimmingResult['trimmedGeometry'],
                'startInside': trimmingResult['startInsideOriginal'],
                'endInside': trimmingResult['endInsideOriginal'],
                'startReservoirIds': trimmingResult['originalStartReservoirIds'],
                'endReservoirIds': trimmingResult['originalEndReservoirIds'],
                'trimmedStartReservoirIds': trimmingResult['trimmedStartReservoirIds'],
                'trimmedEndReservoirIds': trimmingResult['trimmedEndReservoirIds'],
                'wasExitSegment': trimmingResult['startInsideOriginal'] and not trimmingResult['endInsideOriginal'],
                'hadInteriorIntersection': trimmingResult['hadInteriorIntersection']
            })

    exitSelection = {}
    for segmentData in processedSegments:
        if not segmentData['wasExitSegment']:
            continue
        trimmedGeometry = segmentData['trimmedGeometry']
        if trimmedGeometry is None or trimmedGeometry.is_empty:
            continue
        if not segmentData['startReservoirIds']:
            continue
        reservoirKey = sorted(segmentData['startReservoirIds'])[0]
        currentSelection = exitSelection.get(reservoirKey)
        if currentSelection is None or segmentData['index'] < currentSelection:
            exitSelection[reservoirKey] = segmentData['index']

    finalRecords = []
    removedCount = 0
    trimmedCount = 0
    exitPrunedCount = 0
    for segmentData in processedSegments:
        trimmedGeometry = segmentData['trimmedGeometry']
        originalGeometry = segmentData['originalGeometry']
        if trimmedGeometry is None or trimmedGeometry.is_empty:
            removedCount += 1
            continue
        if trimmedGeometry.length <= minimumLength:
            removedCount += 1
            continue
        if segmentData['hadInteriorIntersection']:
            if not segmentData['trimmedStartReservoirIds'] and not segmentData['trimmedEndReservoirIds']:
                removedCount += 1
                continue
        if segmentData['wasExitSegment'] and segmentData['startReservoirIds']:
            reservoirKey = sorted(segmentData['startReservoirIds'])[0]
            selectedIndex = exitSelection.get(reservoirKey)
            if selectedIndex is not None and selectedIndex != segmentData['index']:
                removedCount += 1
                exitPrunedCount += 1
                continue
        if originalGeometry is not None and not originalGeometry.equals(trimmedGeometry):
            trimmedCount += 1
        recordAttributes = segmentData['attributes'].copy()
        recordAttributes['geometry'] = trimmedGeometry
        finalRecords.append(recordAttributes)

    if not finalRecords:
        print(f"no river segments remained after reconciliation")
        return geopandas.GeoDataFrame(columns=river.columns, crs=river.crs), {'processed': len(processedSegments), 'trimmed': trimmedCount, 'removed': removedCount, 'exitPruned': exitPrunedCount}

    reconciledGdf = geopandas.GeoDataFrame(finalRecords, geometry='geometry', crs=river.crs)
    reconciledGdf = reconciledGdf.explode(index_parts=False).reset_index(drop=True)

    summary = {
        'processed': len(processedSegments),
        'trimmed': trimmedCount,
        'removed': removedCount,
        'exitPruned': exitPrunedCount
    }

    return reconciledGdf, summary


def traceRiverDrops(demArray: numpy.ndarray, demMeta: dict, riverGdf: geopandas.GeoDataFrame):
    if riverGdf.empty:
        print(f"no river segments found for drop tracing")
        return demArray.astype('float32'), demMeta, {'startingNodes': 0, 'processedSegments': 0}

    demTransform = demMeta['transform']
    nodataValue = demMeta.get('nodata')
    river = riverGdf.explode(index_parts=False).reset_index(drop=True)
    segmentRecords = []
    nodeData = {}

    def isWithinBounds(row, col):
        return 0 <= row < demArray.shape[0] and 0 <= col < demArray.shape[1]

    def getNodeRowCol(point):
        row, col = rasterio.transform.rowcol(demTransform, point.x, point.y)
        if not isWithinBounds(row, col):
            return None
        return row, col

    def createNodeKey(point):
        return (round(point.x, 6), round(point.y, 6))

    def ensureNode(point):
        nodeKey = createNodeKey(point)
        if nodeKey in nodeData:
            return nodeKey
        rowCol = getNodeRowCol(point)
        if rowCol is None:
            return None
        row, col = rowCol
        if nodataValue is not None and demArray[row, col] == nodataValue:
            return None
        nodeData[nodeKey] = {
            'point': point,
            'rowCol': rowCol,
            'incoming': [],
            'outgoing': [],
            'pendingIncoming': 0
        }
        return nodeKey

    def sampleLineCells(lineGeometry, spacing):
        if lineGeometry.length == 0:
            return []
        steps = max(int(math.ceil(lineGeometry.length / spacing)), 1)
        distances = numpy.linspace(0, lineGeometry.length, steps + 1)
        sampledCells = []
        lastCell = None
        for distance in distances:
            samplePoint = lineGeometry.interpolate(distance)
            row, col = rasterio.transform.rowcol(demTransform, samplePoint.x, samplePoint.y)
            if not isWithinBounds(row, col):
                continue
            currentCell = (row, col)
            if currentCell != lastCell:
                sampledCells.append(currentCell)
                lastCell = currentCell
        endPoint = shapely.geometry.Point(lineGeometry.coords[-1])
        endRow, endCol = rasterio.transform.rowcol(demTransform, endPoint.x, endPoint.y)
        if isWithinBounds(endRow, endCol):
            endCell = (endRow, endCol)
            if not sampledCells or sampledCells[-1] != endCell:
                sampledCells.append(endCell)
        return sampledCells

    def getNeighborValues(row, col, previousCell=None, nextCell=None):
        neighborValues = []
        for deltaRow in [-1, 0, 1]:
            for deltaCol in [-1, 0, 1]:
                if deltaRow == 0 and deltaCol == 0:
                    continue
                neighborRow = row + deltaRow
                neighborCol = col + deltaCol
                neighborCell = (neighborRow, neighborCol)
                if previousCell is not None and neighborCell == previousCell:
                    continue
                if nextCell is not None and neighborCell == nextCell:
                    continue
                if not isWithinBounds(neighborRow, neighborCol):
                    continue
                neighborValue = demArray[neighborRow, neighborCol]
                if nodataValue is not None and neighborValue == nodataValue:
                    continue
                neighborValues.append((neighborRow, neighborCol, neighborValue))
        return neighborValues

    def processSegment(segmentRecord, nodeElevations, spacing):
        startNodeKey = segmentRecord['startNode']
        endNodeKey = segmentRecord['endNode']
        segmentGeometry = segmentRecord['geometry']

        startRow, startCol = nodeData[startNodeKey]['rowCol']
        endRow, endCol = nodeData[endNodeKey]['rowCol']

        startElevation = nodeElevations.get(startNodeKey)
        if startElevation is None:
            startElevation = demArray[startRow, startCol]
            nodeElevations[startNodeKey] = startElevation

        sampledCells = sampleLineCells(segmentGeometry, spacing)
        if not sampledCells:
            return None

        if sampledCells[0] != (startRow, startCol):
            sampledCells.insert(0, (startRow, startCol))
        if sampledCells[-1] != (endRow, endCol):
            sampledCells.append((endRow, endCol))

        previousCell = None
        previousElevation = startElevation
        finalElevation = previousElevation
        for index, cell in enumerate(sampledCells):
            row, col = cell
            if not isWithinBounds(row, col):
                continue
            currentValue = demArray[row, col]
            if nodataValue is not None and currentValue == nodataValue:
                continue
            nextCell = sampledCells[index + 1] if index + 1 < len(sampledCells) else None
            targetElevation = min(currentValue, previousElevation)
            neighborValues = getNeighborValues(row, col, previousCell, nextCell)
            if neighborValues:
                sideValues = [value for _, _, value in neighborValues]
                minimumSideValue = min(sideValues)
                if minimumSideValue <= targetElevation:
                    targetElevation = min(targetElevation, previousElevation - dropIncrement)
            if targetElevation > previousElevation:
                targetElevation = previousElevation
            if targetElevation < currentValue:
                demArray[row, col] = targetElevation
            previousElevation = demArray[row, col]
            previousCell = cell
            finalElevation = previousElevation

        existingEndElevation = nodeElevations.get(endNodeKey)
        if existingEndElevation is None:
            nodeElevations[endNodeKey] = finalElevation
        else:
            nodeElevations[endNodeKey] = min(existingEndElevation, finalElevation)

        return finalElevation

    minCellSize = min(abs(demTransform.a), abs(demTransform.e))
    sampleSpacing = max(minCellSize / 3, 0.0001)

    for segmentIndex, segmentRow in river.iterrows():
        lineGeometries = collectLineStrings(segmentRow.geometry)
        for lineGeometry in lineGeometries:
            if lineGeometry.length == 0:
                continue
            startPoint = shapely.geometry.Point(lineGeometry.coords[0])
            endPoint = shapely.geometry.Point(lineGeometry.coords[-1])
            startRowCol = getNodeRowCol(startPoint)
            endRowCol = getNodeRowCol(endPoint)
            if startRowCol is None or endRowCol is None:
                continue
            startElevation = demArray[startRowCol[0], startRowCol[1]]
            endElevation = demArray[endRowCol[0], endRowCol[1]]
            if nodataValue is not None and (startElevation == nodataValue or endElevation == nodataValue):
                continue
            startNodeKey = ensureNode(startPoint)
            endNodeKey = ensureNode(endPoint)
            if startNodeKey is None or endNodeKey is None:
                continue
            record = {
                'geometry': lineGeometry,
                'startNode': startNodeKey,
                'endNode': endNodeKey,
                'index': segmentIndex
            }
            segmentRecords.append(record)
            nodeData[startNodeKey]['outgoing'].append(len(segmentRecords) - 1)
            nodeData[endNodeKey]['incoming'].append(len(segmentRecords) - 1)

    if not segmentRecords:
        print(f"no usable river segments within dem extent")
        return demArray.astype('float32'), demMeta, {'startingNodes': 0, 'processedSegments': 0}

    for nodeKey, nodeInfo in nodeData.items():
        nodeInfo['pendingIncoming'] = len(nodeInfo['incoming'])

    nodeElevations = {}
    startingNodes = [nodeKey for nodeKey, nodeInfo in nodeData.items() if nodeInfo['pendingIncoming'] == 0 and nodeInfo['outgoing']]
    if not startingNodes:
        print(f"no starting points could be identified")
        return demArray.astype('float32'), demMeta, {'startingNodes': 0, 'processedSegments': 0}

    nodeQueue = deque(startingNodes)
    queuedNodes = set(startingNodes)
    processedSegments = set()
    processedCount = 0
    totalSegments = len(segmentRecords)

    while nodeQueue:
        nodeKey = nodeQueue.popleft()
        nodeInfo = nodeData[nodeKey]
        nodeRow, nodeCol = nodeInfo['rowCol']
        nodeElevation = demArray[nodeRow, nodeCol]
        nodeElevations[nodeKey] = min(nodeElevations.get(nodeKey, nodeElevation), nodeElevation)

        for listIndex in nodeInfo['outgoing']:
            if listIndex in processedSegments:
                continue
            segmentRecord = segmentRecords[listIndex]
            processSegment(segmentRecord, nodeElevations, sampleSpacing)
            processedSegments.add(listIndex)
            processedCount += 1
            showProgress(processedCount, totalSegments, message="tracing drops...   ")
            downstreamNodeKey = segmentRecord['endNode']
            nodeData[downstreamNodeKey]['pendingIncoming'] -= 1
            if nodeData[downstreamNodeKey]['pendingIncoming'] == 0 and downstreamNodeKey not in queuedNodes:
                nodeQueue.append(downstreamNodeKey)
                queuedNodes.add(downstreamNodeKey)

    if processedCount < totalSegments:
        for index, segmentRecord in enumerate(segmentRecords):
            if index in processedSegments:
                continue
            processSegment(segmentRecord, nodeElevations, sampleSpacing)
            processedSegments.add(index)
            processedCount += 1
            showProgress(processedCount, totalSegments, message="finalizing drops...   ")

    demMeta.update(dtype='float32')
    tracedDemArray = demArray.astype('float32')
    summary = {
        'startingNodes': len(startingNodes),
        'processedSegments': processedCount
    }

    return tracedDemArray, demMeta, summary


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="a script for preparing dem for model setup, specifically delineation.")

    parser.add_argument("r", help="the name of the region to run the model for. If not specified, all regions will be processed.", nargs='*', default=[])
    parser.add_argument("--v", help="the version of the model setup to use. If not specified, the datavariables value will be used.", nargs='?', default=None)

    args = parser.parse_args()

    if len(args.r) > 0: regions = args.r
    else: regions = listFolders(f"../model-data/")

    for region in regions:
        # print(f"processing region: {region}" )
        if not exists(f"../model-data/{region}"):
            print(f'\t! the version, {region}, does not exist, the following are available:')
            for v in listFolders('../model-data/'):
                print(f'\t\t- {v}')
            print(f'\t> please specify a valid version using the --v argument')
            sys.exit(1)

        riverNetworkPath        = f'../model-data/{region}/shapes/burn-shape-ESRI-54003.shp'
        grandReservoirPath      = f'../model-data/{region}/shapes/lakes-grand-ESRI-54003.gpkg'
        grandGapReservoirPath   = f'../model-data/{region}/shapes/lakes-grand-ESRI-54003-gap.gpkg'
        demPath                 = f'../model-data/{region}/raster/dem-aster-ESRI-54003.tif'

        lakes = geopandas.read_file(grandReservoirPath)
        gappedLakes = lakes.copy()
        totalPairs = 0
        processedPairs = 0


        gapWarnings = []
        enforcementIterations = 0
        consumedLakeIndices = set()


        for i in range(len(gappedLakes)):
            showProgress(i + 1, len(gappedLakes), message="enforcing lake gaps...", barLength=40)
            for j in range(i + 1, len(gappedLakes)):
                totalPairs += 1

                geom1 = gappedLakes.at[i, 'geometry']
                geom2 = gappedLakes.at[j, 'geometry']

                if geom1 is None or geom2 is None:
                    continue
                if geom1.is_empty or geom2.is_empty:
                    continue

                distance = geom1.distance(geom2)
                if distance >= variables.lakeMinGap - geometricTolerance:
                    continue

                processedPairs += 1

                updatedGeom1, updatedGeom2, gapResolved, iterations = enforce_min_gap_between_polygons(
                    geom1,
                    geom2,
                    minimum_gap=variables.lakeMinGap,
                    tolerance=geometricTolerance,
                    minimum_area_ratio=0.1
                )
                enforcementIterations += iterations

                if updatedGeom1 is None or updatedGeom1.is_empty:
                    gappedLakes.at[i, 'geometry'] = shapely.geometry.GeometryCollection()
                    consumedLakeIndices.add(i)
                    geom1 = gappedLakes.at[i, 'geometry']
                else:
                    gappedLakes.at[i, 'geometry'] = updatedGeom1
                    geom1 = updatedGeom1
                if updatedGeom2 is None or updatedGeom2.is_empty:
                    gappedLakes.at[j, 'geometry'] = shapely.geometry.GeometryCollection()
                    consumedLakeIndices.add(j)
                    geom2 = gappedLakes.at[j, 'geometry']
                else:
                    gappedLakes.at[j, 'geometry'] = updatedGeom2
                    geom2 = updatedGeom2

                if geom1.is_empty or geom2.is_empty:
                    continue

                finalDistance = geom1.distance(geom2)
                if not gapResolved and finalDistance < variables.lakeMinGap - geometricTolerance:
                    gapWarnings.append((i, j, finalDistance))

        if processedPairs > 0:
            averageIterations = enforcementIterations / processedPairs
            print(f"\n\t> adjusted gaps for {processedPairs} of {totalPairs} lake pairs (avg {averageIterations:.2f} iterations)")
        else:
            print(f"\n\t> all lake pairs satisfied the {variables.lakeMinGap} m gap requirement")

        if consumedLakeIndices:
            print(f"\n\t> removed {len(consumedLakeIndices)} lakes that were consumed during gap enforcement")
            gappedLakes = gappedLakes.drop(index=sorted(consumedLakeIndices)).reset_index(drop=True)

        if gapWarnings:
            print(f"\t! warning: some lake pairs could not reach the minimum gap")
            for i, j, finalDistance in gapWarnings[:10]:
                print(f"\t  - lakes {i} and {j} remain {finalDistance:.2f} m apart (target {variables.lakeMinGap} m)")
            if len(gapWarnings) > 10:
                print(f"\t   ...and {len(gapWarnings) - 10} more pairs")
        
        # print(f"processed {processedPairs} lake pairs out of {totalPairs} total pairs")
        
        # save the result
        gappedLakes.to_file(grandGapReservoirPath, driver="GPKG")


        demArray, demMeta, lakesGdf = flattenReservoirElevations(demPath, grandGapReservoirPath)
        lakesOutputPath     = f'../model-data/{region}/shapes/lakes-grand-ESRI-54003.shp'
        if not exists(f"{lakesOutputPath[:-4]}.bak.gpkg"):
            geopandas.read_file(lakesOutputPath).to_file(f"{lakesOutputPath[:-4]}.bak.gpkg", driver='GPKG')

        # remove inner rings so we only have outer boundaries
        for index, row in lakesGdf.iterrows():
            geometry = row.geometry
            if isinstance(geometry, shapely.geometry.Polygon):
                lakesGdf.loc[index, 'geometry'] = shapely.geometry.Polygon(geometry.exterior)
            elif isinstance(geometry, shapely.geometry.MultiPolygon):
                newPolygons = []
                for polygon in geometry.geoms:
                    newPolygons.append(shapely.geometry.Polygon(polygon.exterior))
                lakesGdf.loc[index, 'geometry'] = shapely.geometry.MultiPolygon(newPolygons)

        lakesGdf["RES"] = 1
        lakesGdf.to_file(lakesOutputPath, driver='ESRI Shapefile')

        if not exists(f"{demPath}.bak.tif"):
            with rasterio.open(demPath) as src:
                backupPath = f"{demPath}.bak.tif"
                if hasattr(rasterio, "shutil") and hasattr(rasterio.shutil, "copy"):
                    rasterio.shutil.copy(src, backupPath, copy_src_overviews=True)
                else:
                    with rasterio.open(backupPath, 'w', **src.meta) as backupDataset:
                        backupDataset.write(src.read())

        with rasterio.open(demPath, 'w', **demMeta) as outputDataset:
            outputDataset.write(demArray, 1)

        if variables.prepareDemTopo:
            riverGdf = geopandas.read_file(riverNetworkPath)
            riverGdf = riverGdf.explode(index_parts=False).reset_index(drop=True)
            terminalPointsGdf = identifyTerminalPoints(riverGdf, demArray, demMeta['transform'])
            if terminalPointsGdf.empty:
                print(f"no terminal points identified; aborting pipeline")
                quit()
            flippedRiverGdf = orientRiverNetwork(riverGdf, terminalPointsGdf)
            reconciledRiverGdf, reconciliationSummary = reconcileRiverTopology(flippedRiverGdf, lakesGdf)
            tracedDemArray, tracedMeta, traceSummary = traceRiverDrops(demArray, demMeta, reconciledRiverGdf)

            terminalOutputPath      = f"../model-data/{region}/shapes/terminalPoints.gpkg"
            terminalPointsGdf.to_file(terminalOutputPath, driver='GPKG')

            flippedOutputPath       = f"../model-data/{region}/shapes/flippedRiverNetwork.gpkg"
            flippedRiverGdf.to_file(flippedOutputPath, driver='GPKG')
                
            reconciledOutputPath    = f"{riverNetworkPath}"
            tracedOutputPath        = f"{demPath}"


            if not exists(f"{reconciledOutputPath[:-4]}.bak.gpkg"):
                geopandas.read_file(reconciledOutputPath).to_file(f"{reconciledOutputPath[:-4]}.bak.gpkg", driver='GPKG')
            reconciledRiverGdf.to_file(reconciledOutputPath, driver='GPKG')

            if not exists(f"{tracedOutputPath}.bak.tif"):
                with rasterio.open(tracedOutputPath) as src:
                    backupPath = f"{tracedOutputPath}.bak.tif"
                    if hasattr(rasterio, "shutil") and hasattr(rasterio.shutil, "copy"):
                        rasterio.shutil.copy(src, backupPath, copy_src_overviews=True)
                    else:
                        with rasterio.open(backupPath, 'w', **src.meta) as backupDataset:
                            backupDataset.write(src.read())

            with rasterio.open(tracedOutputPath, 'w', **tracedMeta) as outputDataset:
                outputDataset.write(tracedDemArray, 1)

            print(f"processed {reconciliationSummary['processed']} river segments during reconciliation")
            print(f"trimmed {reconciliationSummary['trimmed']} segments crossing reservoirs")
            print(f"removed {reconciliationSummary['removed']} segments inside reservoirs")
            if reconciliationSummary['exitPruned'] > 0:
                print(f"removed {reconciliationSummary['exitPruned']} surplus exit segments")
            print(f"found {traceSummary['startingNodes']} starting points to trace")
            print(f"processed {traceSummary['processedSegments']} river segments during drop tracing")
            print(f"saved traced dem to {tracedOutputPath}")
        print()
