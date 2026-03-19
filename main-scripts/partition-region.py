#!/bin/python3

'''
This script partitions a region into N subregions by traversing the river
network topology and grouping subbasins. It produces a subregions.gpkg
file with mask polygons and routing points.

Requires an existing delineation (rivs1.shp, subs1.shp, channel.shp).

Usage:
    partition-region.py <region> --n <num_subregions> [--v <version>]

Author  : Celray James CHAWANDA
Contact : celray@chawanda.com
Licence : MIT
'''

import sys, os, argparse
import geopandas
import pandas
import numpy as np
from shapely.geometry import Point, Polygon, MultiPolygon
from shapely.ops import unary_union
from collections import defaultdict, deque

# change working directory
me = os.path.realpath(__file__)
os.chdir(os.path.dirname(me))

import datavariables as variables

def buildTree(channelsGdf):
    '''build adjacency from channel shapefile. returns:
        - children: dict of LINKNO -> list of upstream LINKNOs
        - parent: dict of LINKNO -> downstream LINKNO
        - roots: list of outlet LINKNOs (DSLINKNO == -1)
    '''
    children    = defaultdict(list)
    parent      = {}
    roots       = []

    for _, row in channelsGdf.iterrows():
        linkno  = int(row['LINKNO'])
        dslink  = int(row['DSLINKNO'])
        parent[linkno] = dslink

        if dslink == -1:
            roots.append(linkno)
        else:
            children[dslink].append(linkno)

    return children, parent, roots


def calcUpstreamArea(linkno, children, areaMap, cache):
    '''recursively calculate total upstream area for a channel'''
    if linkno in cache:
        return cache[linkno]

    total = areaMap.get(linkno, 0)
    for child in children.get(linkno, []):
        total += calcUpstreamArea(child, children, areaMap, cache)

    cache[linkno] = total
    return total


def findMainStem(root, children, upstreamArea):
    '''find the main stem by always following the child with the largest upstream area'''
    stem = [root]
    current = root
    while children.get(current):
        kids = children[current]
        biggest = max(kids, key=lambda k: upstreamArea.get(k, 0))
        stem.append(biggest)
        current = biggest
    return stem


def assignSubbasins(linkno, children, assignment, groupId, excludeLinks):
    '''BFS assign all upstream channels to a group, stopping at excludeLinks'''
    queue = deque([linkno])
    while queue:
        current = queue.popleft()
        if current in assignment:
            continue
        assignment[current] = groupId
        for child in children.get(current, []):
            if child not in excludeLinks and child not in assignment:
                queue.append(child)


if __name__ == '__main__':

    parser = argparse.ArgumentParser(description="partition a region into subregions based on river network topology")
    parser.add_argument("region", help="region name")
    parser.add_argument("--n", help="number of subregions", type=int, required=True)
    parser.add_argument("--v", help="model version", nargs='?', default=None)

    args    = parser.parse_args()
    region  = args.region
    nSubs   = args.n
    version = args.v if args.v else variables.version

    projBase    = f'../model-setup/CoSWATv{version}/{region}'
    auth        = variables.final_proj_auth
    code        = variables.final_proj_code

    channelsFn  = f'{projBase}/Watershed/Shapes/dem-aster-{auth}-{code}channel.shp'
    rivsFn      = f'{projBase}/Watershed/Shapes/rivs1.shp'
    subsFn      = f'{projBase}/Watershed/Shapes/subs1.shp'

    # if region-level files don't exist, try .bak directory or first subregion
    if not os.path.exists(channelsFn):
        bakBase = f'{projBase}.bak'
        if os.path.exists(f'{bakBase}/Watershed/Shapes/dem-aster-{auth}-{code}channel.shp'):
            projBase    = bakBase
            channelsFn  = f'{bakBase}/Watershed/Shapes/dem-aster-{auth}-{code}channel.shp'
            rivsFn      = f'{bakBase}/Watershed/Shapes/rivs1.shp'
            subsFn      = f'{bakBase}/Watershed/Shapes/subs1.shp'
            print(f'\t> using delineation files from backup {bakBase}')
        else:
            import json as jsonmod
            schemaFn = f'{projBase}/schema.json'
            if os.path.exists(schemaFn):
                with open(schemaFn, 'r') as f:
                    schemaData = jsonmod.load(f)
                firstSub    = schemaData['subregions'][0]
                subProjBase = f'{projBase}/{firstSub}'
                channelsFn  = f'{subProjBase}/Watershed/Shapes/dem-aster-{auth}-{code}channel.shp'
                rivsFn      = f'{subProjBase}/Watershed/Shapes/rivs1.shp'
                subsFn      = f'{subProjBase}/Watershed/Shapes/subs1.shp'
                print(f'\t> using delineation files from subregion {firstSub}')

    for fn in [channelsFn, rivsFn, subsFn]:
        if not os.path.exists(fn):
            print(f'! file not found: {fn}')
            sys.exit(1)

    print(f'\n# partitioning {region} into {nSubs} subregions')

    # read data
    channelsGdf = geopandas.read_file(channelsFn)
    rivsGdf     = geopandas.read_file(rivsFn)
    subsGdf     = geopandas.read_file(subsFn)

    # build topology
    print(f'\t> building river network topology ({len(channelsGdf)} channels)')
    children, parent, roots = buildTree(channelsGdf)

    # map LINKNO -> upstream contributing area (from channel shapefile)
    areaMap = {}
    for _, row in channelsGdf.iterrows():
        areaMap[int(row['LINKNO'])] = float(row['DSContArea']) - float(row['USContArea'])

    # calculate total upstream area for each channel
    upstreamArea = {}
    for root in roots:
        calcUpstreamArea(root, children, areaMap, upstreamArea)

    primaryRoot = max(roots, key=lambda r: upstreamArea.get(r, 0))
    print(f'\t> primary outlet: LINKNO {primaryRoot}, total upstream area: {upstreamArea[primaryRoot]:.0f}')

    # TREE BISECTION WITH VIRTUAL EDGES
    # 1. weight each channel by its subbasin polygon area (not AreaC)
    # 2. connect disconnected roots to nearest primary-network channel via virtual edges
    # 3. recursively bisect the unified tree for balanced polygon-area groups
    # 4. virtual edge cuts = spatial boundaries (no routing), real edge cuts = routing points

    linkToSubbasin  = {int(r['LINKNO']): int(r['Subbasin']) for _, r in rivsGdf.iterrows()}
    subArea         = {int(s['Subbasin']): s.geometry.area for _, s in subsGdf.iterrows()}
    channelWeight   = {linkno: subArea.get(linkToSubbasin.get(linkno, -1), 0) for linkno in set(int(c['LINKNO']) for _, c in channelsGdf.iterrows())}

    # channel centroids for proximity
    chCentroids = {int(r['LINKNO']): (r.geometry.centroid.x, r.geometry.centroid.y) for _, r in rivsGdf.iterrows()}

    # find primary root and its connected set
    primaryRoot = max(roots, key=lambda r: channelWeight.get(r, 0))
    primarySet  = set()
    queue       = deque([primaryRoot])
    while queue:
        n = queue.popleft()
        if n in primarySet: continue
        primarySet.add(n)
        for c in children.get(n, []): queue.append(c)

    # connect disconnected roots to nearest primary channel via virtual edges
    virtualRoots = set()
    for r in roots:
        if r == primaryRoot: continue
        if r not in chCentroids: continue
        virtualRoots.add(r)
        rx, ry  = chCentroids[r]
        bestDist = float('inf')
        bestTarget = None
        for pLink in primarySet:
            if pLink not in chCentroids: continue
            px, py = chCentroids[pLink]
            dist = (rx - px)**2 + (ry - py)**2
            if dist < bestDist:
                bestDist    = dist
                bestTarget  = pLink
        if bestTarget is not None:
            children[bestTarget].append(r)
            parent[r] = bestTarget

    print(f'\t> connected {len(virtualRoots)} disconnected basins to primary network')

    # compute subtree weight using polygon areas
    stw = {}
    def calcSTW(n):
        if n in stw: return stw[n]
        total = channelWeight.get(n, 0)
        for c in children.get(n, []):
            total += calcSTW(c)
        stw[n] = total
        return total

    calcSTW(primaryRoot)

    # recursive bisection
    allChannels = set(channelWeight.keys())

    def bisectTree(channelSet):
        total   = sum(channelWeight.get(c, 0) for c in channelSet)
        target  = total / 2.0
        localSTW = {}
        def calcLocal(n):
            if n in localSTW: return localSTW[n]
            t = channelWeight.get(n, 0)
            for c in children.get(n, []):
                if c in channelSet: t += calcLocal(c)
            localSTW[n] = t
            return t
        for n in channelSet:
            par = parent.get(n, -1)
            if par == -1 or par not in channelSet:
                calcLocal(n)
        bestNode    = None
        bestDiff    = float('inf')
        for n in channelSet:
            par = parent.get(n, -1)
            if par == -1 or par not in channelSet: continue
            diff = abs(localSTW.get(n, 0) - target)
            if diff < bestDiff:
                bestDiff    = diff
                bestNode    = n
        if bestNode is None: return None
        upSet = set()
        q = deque([bestNode])
        while q:
            cur = q.popleft()
            if cur not in channelSet or cur in upSet: continue
            upSet.add(cur)
            for c in children.get(cur, []):
                if c in channelSet: q.append(c)
        return bestNode, parent[bestNode], upSet, channelSet - upSet

    groups      = [allChannels]
    cutPoints   = []

    while len(groups) < nSubs:
        largest = max(range(len(groups)), key=lambda i: sum(channelWeight.get(c, 0) for c in groups[i]))
        result  = bisectTree(groups[largest])
        if result is None: break
        upNode, downNode, upSet, downSet = result
        # only add routing point if this is a real river edge (not virtual)
        isVirtual = upNode in virtualRoots
        if not isVirtual:
            cutPoints.append((upNode, downNode))
        groups[largest] = downSet
        groups.append(upSet)

    # assign channels to groups (1-based)
    channelToGroup = {}
    for grpIdx, grp in enumerate(groups):
        for linkno in grp:
            channelToGroup[linkno] = grpIdx + 1

    # map to subbasins
    subToGroup = {}
    for linkno, grp in channelToGroup.items():
        sub = linkToSubbasin.get(linkno)
        if sub is not None:
            subToGroup[sub] = grp

    subsGdf['group'] = subsGdf['Subbasin'].map(subToGroup)

    # fill unassigned subbasins
    unassigned = subsGdf[subsGdf['group'].isna()]
    if len(unassigned) > 0:
        print(f'\t> {len(unassigned)} subbasins unassigned, assigning by adjacency')
        assigned        = subsGdf[subsGdf['group'].notna()]
        dissolvedGroups = assigned.dissolve(by='group').reset_index()
        for idx in unassigned.index:
            geom        = subsGdf.loc[idx, 'geometry']
            bestGrp     = None
            bestDist    = float('inf')
            for _, grpRow in dissolvedGroups.iterrows():
                dist = geom.distance(grpRow['geometry'])
                if dist < bestDist:
                    bestDist = dist
                    bestGrp  = grpRow['group']
            subsGdf.loc[idx, 'group'] = bestGrp

    subsGdf['group'] = subsGdf['group'].astype(int)

    # build assignment dict for routing point placement
    assignment = channelToGroup

    for grp in sorted(subsGdf['group'].unique()):
        mask = subsGdf['group'] == grp
        area = subsGdf[mask].geometry.area.sum() / 1e6
        print(f'\t  - group {grp}: {mask.sum()} subbasins, {area:.0f} km²')

    print(f'\t> {len(cutPoints)} routing connections for {len(groups)} subregions')

    # map LINKNO -> subbasin number (from rivs1.shp)
    linkToSubbasin = {}
    for _, row in rivsGdf.iterrows():
        linkToSubbasin[int(row['LINKNO'])] = int(row['Subbasin'])

    # map subbasin number -> group
    subbasinToGroup = {}
    for linkno, group in assignment.items():
        if linkno in linkToSubbasin:
            subbasinToGroup[linkToSubbasin[linkno]] = group

    # assign subbasins in subs1.shp to groups
    subsGdf['group'] = subsGdf['Subbasin'].map(subbasinToGroup)

    # unassigned subbasins: assign to the group they physically touch
    unassigned = subsGdf[subsGdf['group'].isna()]
    if len(unassigned) > 0:
        print(f'\t> {len(unassigned)} subbasins unassigned, assigning by adjacency')
        assigned = subsGdf[subsGdf['group'].notna()]

        # build dissolved group polygons for spatial lookup
        dissolvedGroups = assigned.dissolve(by='group').reset_index()

        for idx in unassigned.index:
            geom = subsGdf.loc[idx, 'geometry']
            bestGrp     = None
            bestDist    = float('inf')

            for _, grpRow in dissolvedGroups.iterrows():
                dist = geom.distance(grpRow['geometry'])
                if dist < bestDist:
                    bestDist = dist
                    bestGrp  = grpRow['group']

            subsGdf.loc[idx, 'group'] = bestGrp

    subsGdf['group'] = subsGdf['group'].astype(int)

    # dissolve subbasins by group to create mask polygons
    print(f'\t> dissolving subbasins into {nSubs} subregion masks')
    masksGdf = subsGdf.dissolve(by='group').reset_index()
    masksGdf['subregion'] = [f'{i:02d}' for i in range(1, len(masksGdf) + 1)]
    masksGdf['name']      = None
    masksGdf = masksGdf[['subregion', 'name', 'geometry']]

    def removeHoles(geom):
        if geom.geom_type == 'Polygon':
            return Polygon(geom.exterior)
        elif geom.geom_type == 'MultiPolygon':
            return MultiPolygon([Polygon(p.exterior) for p in geom.geoms])
        return geom

    # build group -> subregion ID lookup
    groupToSubId = {}
    for i, grp in enumerate(sorted(subsGdf['group'].unique())):
        groupToSubId[grp] = f'{i + 1:02d}'

    # create routing points on channels at subbasin boundaries
    # QSWAT+ only recognizes inlets where BasinNo changes between channel and its downstream
    print(f'\t> creating routing points at {len(cutPoints)} cut locations')
    routingPoints   = []
    bufferRadius    = variables.data_resolution * 3

    # build BasinNo lookup for boundary detection
    basinNoMap  = {}
    dsLinkMap   = {}
    for _, ch in channelsGdf.iterrows():
        basinNoMap[int(ch['LINKNO'])]  = int(ch['BasinNo'])
        dsLinkMap[int(ch['LINKNO'])]   = int(ch['DSLINKNO'])

    def isOnSubbasinBoundary(linkno):
        '''check if channel and its downstream are in different subbasins'''
        dsLink = dsLinkMap.get(linkno, -1)
        if dsLink < 0: return True
        return basinNoMap.get(linkno, -1) != basinNoMap.get(dsLink, -2)

    # load lakes for point-in-lake avoidance
    lakesFn     = f'{projBase}/Watershed/Shapes/lakes-grand-{auth}-{code}.shp'
    lakesUnion  = None
    if os.path.exists(lakesFn):
        lakesGdf    = geopandas.read_file(lakesFn)
        if len(lakesGdf) > 0:
            lakesBuf    = lakesGdf.geometry.buffer(variables.data_resolution * 2)
            lakesUnion  = lakesBuf.unary_union

    for upLink, downLink in cutPoints:
        upGroup     = assignment.get(upLink, 1)
        downGroup   = assignment.get(downLink, 1)
        upSubId     = groupToSubId.get(upGroup, '01')
        downSubId   = groupToSubId.get(downGroup, '01')

        # search for a channel near the cut that is on a subbasin boundary
        # start with upLink/downLink, then walk upstream/downstream to find one
        bestChannel = None
        bestPoint   = None

        # try channels near the cut point, preferring ones on subbasin boundaries
        candidates  = [upLink, downLink]

        # walk upstream from upLink to find boundary channels
        current = upLink
        for _ in range(20):
            kids = [k for k in children.get(current, [])]
            if not kids: break
            current = max(kids, key=lambda k: upstreamArea.get(k, 0))
            candidates.append(current)

        # walk downstream from downLink
        current = downLink
        for _ in range(20):
            ds = dsLinkMap.get(current, -1)
            if ds < 0: break
            candidates.append(ds)
            current = ds

        for linkno in candidates:
            if not isOnSubbasinBoundary(linkno): continue

            chRow = channelsGdf[channelsGdf['LINKNO'] == linkno]
            if chRow.empty: continue

            lineGeom    = chRow.iloc[0].geometry
            midPt       = lineGeom.interpolate(0.5, normalized=True)

            # avoid endpoints (confluences)
            coords = list(lineGeom.coords)
            if len(coords) >= 2:
                startPt = Point(coords[0])
                endPt   = Point(coords[-1])
                if midPt.distance(startPt) < 1 or midPt.distance(endPt) < 1:
                    continue

            # avoid placing point inside or near a lake
            if lakesUnion is not None and lakesUnion.contains(midPt):
                continue

            bestChannel = linkno
            bestPoint   = midPt
            break

        if bestPoint is None:
            # fallback: use upLink midpoint even if not on boundary
            chRow = channelsGdf[channelsGdf['LINKNO'] == upLink]
            if not chRow.empty:
                bestPoint = chRow.iloc[0].geometry.interpolate(0.5, normalized=True)
            else:
                continue

        routingPoints.append({
            'geometry':     bestPoint,
            'INLET':        1,
            'OUTLET':       1,
            'INLET_MASK':   downSubId,
            'OUTLET_MASK':  upSubId,
            '_upSubId':     upSubId,
            '_downSubId':   downSubId,
        })

    if routingPoints:
        pointsGdf = geopandas.GeoDataFrame(routingPoints, crs=subsGdf.crs, geometry='geometry')
    else:
        pointsGdf = geopandas.GeoDataFrame(
            columns=['INLET', 'OUTLET', 'INLET_MASK', 'OUTLET_MASK', 'geometry'],
            geometry='geometry', crs=subsGdf.crs
        )

    # expand both adjacent masks so each routing point is contained by both masks
    for _, pt in pointsGdf.iterrows():
        # check if both masks already contain the point
        upMask      = masksGdf[masksGdf['subregion'] == pt['_upSubId']]
        downMask    = masksGdf[masksGdf['subregion'] == pt['_downSubId']]

        inUp    = not upMask.empty and upMask.iloc[0].geometry.contains(pt.geometry)
        inDown  = not downMask.empty and downMask.iloc[0].geometry.contains(pt.geometry)

        # use larger buffer if point is far from one of the masks (e.g. moved away from lake)
        if inUp and inDown:
            radius = bufferRadius
        else:
            # calculate distance to the farther mask and use that + buffer
            distUp      = upMask.iloc[0].geometry.distance(pt.geometry) if not upMask.empty else 0
            distDown    = downMask.iloc[0].geometry.distance(pt.geometry) if not downMask.empty else 0
            radius      = max(distUp, distDown) + bufferRadius

        ptBuffer = pt.geometry.buffer(radius)
        for maskIdx, maskRow in masksGdf.iterrows():
            if maskRow['subregion'] in (pt['_upSubId'], pt['_downSubId']):
                masksGdf.loc[maskIdx, 'geometry'] = masksGdf.loc[maskIdx, 'geometry'].union(ptBuffer)

    if '_upSubId' in pointsGdf.columns:
        pointsGdf = pointsGdf.drop(columns=['_upSubId', '_downSubId'])

    # remove interior rings (holes from lakes and geometry operations)
    masksGdf['geometry'] = masksGdf['geometry'].apply(removeHoles)

    # write output (remove existing file to avoid appending stale layers)
    outFn = f'../data-preparation/resources/regions/{region}/subregions.gpkg'
    os.makedirs(os.path.dirname(outFn), exist_ok=True)
    if os.path.exists(outFn):
        # backup existing file
        import shutil
        backupFn = outFn.replace('.gpkg', '_backup.gpkg')
        shutil.copy2(outFn, backupFn)
        print(f'\t> backed up existing file to {backupFn}')
        os.remove(outFn)

    masksGdf.to_file(outFn, layer='masks', driver='GPKG')
    pointsGdf.to_file(outFn, layer='points', driver='GPKG', mode='a')

    print(f'\n\t> wrote {outFn}')
    print(f'\t  masks:  {len(masksGdf)} subregions')
    print(f'\t  points: {len(pointsGdf)} routing points')

    # summary
    print(f'\n\t> subregion summary:')
    for _, row in masksGdf.iterrows():
        subId   = row['subregion']
        area    = row['geometry'].area
        nSb     = len(subsGdf[subsGdf['group'] == int(subId)])
        print(f'\t  {subId}: {nSb} subbasins, area {area / 1e6:.0f} km²')

    # show connections
    if len(pointsGdf) > 0:
        print(f'\n\t> connections:')
        for _, pt in pointsGdf.iterrows():
            print(f'\t  {pt["OUTLET_MASK"]} -> {pt["INLET_MASK"]} at ({pt.geometry.x:.0f}, {pt.geometry.y:.0f})')

    print()
