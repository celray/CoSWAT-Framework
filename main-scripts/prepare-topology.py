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
from collections import deque

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


def flattenReservoirElevations(demSourcePath: str, reservoirsPath: str):
    with rasterio.open(demSourcePath) as demDataset:
        # rasterio.features.shapes supports only: int16, int32, uint8, uint16, float32
        # keep DEM in a supported dtype (float32) since we modify values and then pass to shapes()
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
        if maskedValues.size == 0:
            continue
        minimumValue = float(maskedValues.min())
        print(f"minimum value for reservoir index {reservoirIndex} is {minimumValue}")
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
    counter = 0
    totalPoints = len(intersectionPoints)
    for point in intersectionPoints:
        counter += 1
        showProgress(counter, totalPoints, message="Filtering unique intersection points...", barLength=40)
        isUnique = True
        for existingPoint in uniqueIntersectionPoints:
            if point.distance(existingPoint) < 1e-10:
                isUnique = False
                break
        if isUnique:
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

    primaryCounter = 0
    primaryTotal = len(terminalPointsGdf)
    for terminalIndex, terminalRow in terminalPointsGdf.iterrows():
        primaryCounter += 1
        dualProgress(primaryCounter, primaryTotal, 0, 0, message="orienting river segments...", barLength=40)
        riverSegment = river[river.intersects(terminalRow.geometry)]
        if riverSegment.empty:
            print(f"no river segment found for terminal point index {terminalIndex}")
            continue
        startingSegmentIndex = int(riverSegment.index[0])
        print(f"starting at terminal point index {terminalIndex}")
        print(f"current terminal point geometry {terminalRow.geometry}")
        print(f"initial river segment indices {list(riverSegment.index)}")
        processedIndices = set()
        queuedIndices = {startingSegmentIndex}
        todoSegments = deque([(startingSegmentIndex, terminalRow.geometry)])
        while todoSegments:
            showProgress(len(processedIndices), len(river), message=f"remaining segments to process: {len(todoSegments)}     ", barLength=40)
            segmentIndex, targetPoint = todoSegments.popleft()
            queuedIndices.discard(segmentIndex)
            if segmentIndex in processedIndices:
                continue
            showProgress(len(processedIndices), len(river), message=f"processing segment index: {segmentIndex}    ", barLength=40)
            segmentGeometry = river.at[segmentIndex, 'geometry']
            targetCoordinates = targetPoint.coords[0]
            segmentStart = segmentGeometry.coords[0]
            if segmentStart == targetCoordinates:
                showProgress(len(processedIndices), len(river), message=f"segment index: {segmentIndex} is correctly oriented    ", barLength=40)
            else:
                showProgress(len(processedIndices), len(river), message=f"flipping segment index: {segmentIndex}    ", barLength=40)
                river.at[segmentIndex, 'geometry'] = segmentGeometry.reverse()
                segmentGeometry = river.at[segmentIndex, 'geometry']
            segmentCoordinates = list(segmentGeometry.coords)
            for coordinate in segmentCoordinates[1:]:
                matchingSegments = river[
                    (river.index != segmentIndex) &
                    (river.geometry.apply(lambda geom: geom.coords[0] == coordinate or geom.coords[-1] == coordinate))
                ]
                if matchingSegments.empty:
                    showProgress(len(processedIndices), len(river), message=f"! no matching segments found at coord: {coordinate}    ", barLength=40)
                    continue
                sharedPoint = shapely.geometry.Point(coordinate)
                for matchIndex, matchRow in matchingSegments.iterrows():
                    matchGeometry = matchRow.geometry
                    matchStart = matchGeometry.coords[0]
                    matchEnd = matchGeometry.coords[-1]
                    if matchStart == coordinate:
                        pass
                    elif matchEnd == coordinate:
                        showProgress(len(processedIndices), len(river), message=f"flipping matching segment index: {matchIndex}    ", barLength=40)
                        river.at[matchIndex, 'geometry'] = matchGeometry.reverse()
                    else:
                        showProgress(len(processedIndices), len(river), message=f"! error: Matching segment index {matchIndex} does not connect at coord: {coordinate}    ", barLength=40)
                        continue
                    if matchIndex not in processedIndices and matchIndex not in queuedIndices:
                        todoSegments.append((matchIndex, sharedPoint))
                        queuedIndices.add(matchIndex)
            processedIndices.add(segmentIndex)

    counter = 0
    totalSegments = len(river.index)
    for index, segment in river.iterrows():
        counter += 1
        showProgress(counter, totalSegments, message="Finalizing segment directions...")
        river.at[index, 'geometry'] = segment.geometry.reverse()

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

    # get regions
    if len(args.r) > 0: regions = args.r
    else: regions = list_folders(f"../model-data/")

    for region in regions:
        if not exists(f"../model-data/{region}"):
            print(f'\t! the version, {region}, does not exist, the following are available:')
            for v in list_folders('../model-data/'):
                print(f'\t\t- {v}')
            print(f'\t> please specify a valid version using the --v argument')
            sys.exit(1)


        riverNetworkPath    = f'../model-data/{region}/shapes/burn-shape-ESRI-54003.shp'
        grandReservoirPath  = f'../model-data/{region}/shapes/lakes-grand-ESRI-54003.gpkg'
        demPath             = f'../model-data/{region}/raster/dem-aster-ESRI-54003.tif'

        demArray, demMeta, lakesGdf = flattenReservoirElevations(demPath, grandReservoirPath)
        riverGdf = geopandas.read_file(riverNetworkPath)
        riverGdf = riverGdf.explode(index_parts=False).reset_index(drop=True)
        terminalPointsGdf = identifyTerminalPoints(riverGdf, demArray, demMeta['transform'])
        if terminalPointsGdf.empty:
            print(f"no terminal points identified; aborting pipeline")
            quit()
        flippedRiverGdf = orientRiverNetwork(riverGdf, terminalPointsGdf)
        reconciledRiverGdf, reconciliationSummary = reconcileRiverTopology(flippedRiverGdf, lakesGdf)
        tracedDemArray, tracedMeta, traceSummary = traceRiverDrops(demArray, demMeta, reconciledRiverGdf)

        lakesOutputPath         = f'../model-data/{region}/shapes/lakes-grand-ESRI-54003.shp'
        terminalOutputPath      = f"../model-data/{region}/shapes/terminalPoints.gpkg"
        flippedOutputPath       = f"../model-data/{region}/shapes/flippedRiverNetwork.gpkg"
        reconciledOutputPath    = f"{riverNetworkPath}"
        tracedOutputPath        = f"{demPath}"

        if not exists(f"{lakesOutputPath[:-4]}.bak.gpkg"):
            geopandas.read_file(lakesOutputPath).to_file(f"{lakesOutputPath[:-4]}.bak.gpkg", driver='GPKG')
        lakesGdf.to_file(lakesOutputPath, driver='GPKG')

        terminalPointsGdf.to_file(terminalOutputPath, driver='GPKG')
        flippedRiverGdf.to_file(flippedOutputPath, driver='GPKG')

        if not exists(f"{reconciledOutputPath[:-4]}.bak.gpkg"):
            geopandas.read_file(reconciledOutputPath).to_file(f"{reconciledOutputPath[:-4]}.bak.gpkg", driver='GPKG')
        reconciledRiverGdf.to_file(reconciledOutputPath, driver='GPKG')

        if not exists(f"{tracedOutputPath}.bak.tif"):
            with rasterio.open(tracedOutputPath) as src:
                rasterio.shutil.copy(src, f"{tracedOutputPath}.bak.tif", copy_src_overviews=True)

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
