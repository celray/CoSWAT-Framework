#!/bin/python3

import warnings, os, sys
import geopandas
import pandas, math
from genericpath import exists
from shapely.wkt import loads
from shapely.geometry import Point, Polygon

import datavariables as variables

def min_distance(point, lines):
    return lines.distance(point).min()


def file_name(path_, extension=True):
    if extension:
        fn = os.path.basename(path_)
    else:
        fn = os.path.basename(path_).split(".")[0]
    return(fn)


def distance(coords_a, coords_b):
    return math.sqrt(((coords_b[0] - coords_a[0]) ** 2) + (coords_b[1] - coords_a[1]) ** 2)


def report(string, printing=False):
    if printing:
        print(f"  > {string}")
    else:
        sys.stdout.write("\r" + string)
        sys.stdout.flush()


def points_to_geodataframe(point_pairs_list, columns = ['latitude', 'longitude'], auth = "EPSG", code = '4326', out_shape = '', format = 'gpkg', v = False, get_geometry_only = False):
    df = pandas.DataFrame(point_pairs_list, columns = columns)
    geometry = [Point(xy) for xy in zip(df['latitude'], df['longitude'])]

    if get_geometry_only:
        return geometry[0]

    gdf = geopandas.GeoDataFrame(point_pairs_list, columns = columns, geometry=geometry)
    drivers = {'gpkg': 'GPKG', 'shp': 'ESRI Shapefile'}

    gdf = gdf.set_crs(f'{auth}:{code}')
    
    if out_shape != '':
        if v: print(f'creating shapefile {out_shape}')
        gdf.to_file(out_shape, driver=drivers[format])
    
    return gdf


def list_all_files(folder, extension="*"):
    list_of_files = []
    # Getting the current work directory (cwd)
    thisdir = folder

    # r=root, d=directories, f = files
    for r, d, f in os.walk(thisdir):
        for file in f:
            if extension == "*":
                list_of_files.append(os.path.join(r, file))
            elif "." in extension:
                if file.endswith(extension[1:]):
                    list_of_files.append(os.path.join(r, file))
                    # print(os.path.join(r, file))
            else:
                if file.endswith(extension):
                    list_of_files.append(os.path.join(r, file))
                    # print(os.path.join(r, file))

    return list_of_files


def list_folders(directory):
    """
    directory: string or pathlike object
    """
    all_dirs = os.listdir(directory)
    dirs = [dir_ for dir_ in all_dirs if os.path.isdir(
        os.path.join(directory, dir_))]
    return dirs


warnings.filterwarnings("ignore") 


# change working directory
me = os.path.realpath(__file__)
os.chdir(os.path.dirname(me))

import argparse

parser = argparse.ArgumentParser(description="create outlet points for a region")
parser.add_argument("version", help="model version")
parser.add_argument("region", help="region name")
parser.add_argument("--sr", help="subregion directory name", nargs='?', default=None)

cliArgs = parser.parse_args()

version     = cliArgs.version
region      = cliArgs.region
subDir      = cliArgs.sr

proj_auth   = variables.final_proj_auth
proj_code   = variables.final_proj_code

# resolve project directory
if subDir is not None:
    projBase = f'../model-setup/CoSWATv{version}/{region}/{subDir}'
else:
    projBase = f'../model-setup/CoSWATv{version}/{region}'

channels_fn = f'{projBase}/Watershed/Shapes/dem-aster-{proj_auth.lower()}-{proj_code}channel/dem-aster-{proj_auth.upper()}-{proj_code}channel.shp'
grdc_shp_fn = f'../model-data/{region}/shapes/grdc_stations-{proj_auth.upper()}-{proj_code}.gpkg'


if not exists(channels_fn):
    channels_fn = f'{projBase}/Watershed/Shapes/dem-aster-{proj_auth.upper()}-{proj_code}channel.shp'
    if not exists(channels_fn):
        print(f"! the channels file ({file_name(channels_fn)}) was not found")
        quit()

points_template_fn = f"../data-preparation/resources/outlet-template-{proj_auth}-{proj_code}.gpkg"

channels_gdf = geopandas.read_file(channels_fn)
points_template_gdf = geopandas.read_file(points_template_fn)


points_template_gdf = points_template_gdf[0:0]


points = []

workit = True
while workit:
    for index, row in channels_gdf.iterrows():
        if not row['DSLINKNO'] == -1: continue

        linestring = loads(str(row['geometry']))
        if len(linestring.coords) < 3:
            report("stepping inner due to short channel shenanigans")
            
            for indx_, rw in channels_gdf.iterrows():
                if rw['DSLINKNO'] == row['LINKNO']:
                    channels_gdf.loc[indx_, "DSLINKNO"] = -1

            channels_gdf.loc[index, "DSLINKNO"] = -99
            workit = True
            break

        point_coords = linestring.coords[1]
        report(f"processing channel {row['LINKNO']}{' ' * 30}")

        list_of_points = [float(x) for x in point_coords]

        if not list_of_points in points:
            points.append(list_of_points)
        workit = False


# fetch more points using the grdc dataset
grdc_point_gdf      = geopandas.read_file(grdc_shp_fn)

grdc_point_gdf['min_dist_to_lines'] = grdc_point_gdf.geometry.apply(min_distance, args=(channels_gdf,))

re_evaluate = True

print(f'\n  > dropping points [{region}]')
checked_indices = []
while re_evaluate:
    re_evaluate = False
    for index, row in grdc_point_gdf.iterrows():
        if index in checked_indices:
            continue

        checked_indices.append(index)
        if row.min_dist_to_lines > variables.channel_snap_thres:
            grdc_point_gdf = grdc_point_gdf.drop(index)
            report(f"dropping {row.grdc_no}      ")
            re_evaluate = True
            break

grdc_point_gdf['X'] = grdc_point_gdf.geometry.x
grdc_point_gdf['Y'] = grdc_point_gdf.geometry.y

print(f'\n  > removing points that are too close to another [{region}]')
# use spatial index for proximity dedup
from scipy.spatial import cKDTree
import numpy as np

grdc_point_gdf['X'] = grdc_point_gdf.geometry.x
grdc_point_gdf['Y'] = grdc_point_gdf.geometry.y
coords          = np.column_stack([grdc_point_gdf['X'].values, grdc_point_gdf['Y'].values])
tree            = cKDTree(coords)
pairs           = tree.query_pairs(variables.proximity_thres)

skippedIndices  = set()
grdcIndices     = grdc_point_gdf.index.tolist()

for i, j in pairs:
    idxI = grdcIndices[i]
    idxJ = grdcIndices[j]
    if idxI in skippedIndices or idxJ in skippedIndices: continue

    distI = grdc_point_gdf.loc[idxI, 'min_dist_to_lines']
    distJ = grdc_point_gdf.loc[idxJ, 'min_dist_to_lines']

    if distI <= distJ: skippedIndices.add(idxJ)
    else: skippedIndices.add(idxI)

grdc_point_gdf = grdc_point_gdf.drop(index=list(skippedIndices)).reset_index(drop=True)
channels_gdf   = channels_gdf.reset_index(drop=True)

print(f'  > attaching points to channels [{region}]')
# use spatial index for nearest channel lookup
channelSindex   = channels_gdf.sindex
close_features  = {}

for index, row in grdc_point_gdf.iterrows():
    nearest = channelSindex.nearest(row.geometry, return_all=False)
    nearestIdx = list(nearest)[0] if hasattr(nearest, '__iter__') else nearest
    # refine: check a few candidates from spatial index
    candidates  = list(channelSindex.query(row.geometry.buffer(variables.channel_snap_thres)))
    if candidates:
        bestIdx     = min(candidates, key=lambda ci: channels_gdf.iloc[ci].geometry.distance(row.geometry))
        close_features[row.name] = bestIdx
    else:
        close_features[row.name] = nearestIdx


outlet_snap_data = []

print(f'  > snapping points to channels safely [{region}]')
for index in close_features:
    ref_x, ref_y = grdc_point_gdf.loc[index,:].geometry.coords.xy

    point_coords = [ref_x[0], ref_y[0]]

    x_array, y_array = channels_gdf.loc[close_features[index],:].geometry.coords.xy
        
    # print(channels_gdf.loc[close_features[index],:].LINKNO)

    # print(ref_x,ref_y)
    x_array = [coord_ for coord_ in x_array]
    y_array = [coord_ for coord_ in y_array]

    start_coords = [x_array[0], y_array[0]]
    end_coords = [x_array[-1], y_array[-1]]

    if len(x_array) < variables.minimum_channel_segments:
        continue

    current_snap = [x_array[variables.start_index_value], y_array[variables.start_index_value]]
    current_distance = distance(point_coords, current_snap)

    for i in range(variables.start_index_value, len(x_array) - variables.end_index_value):
        if distance(point_coords, [x_array[i], y_array[i]]) < current_distance:
            current_snap = [x_array[i], y_array[i]]
            current_distance = distance(point_coords, current_snap)


    outlet_snap_data.append(current_snap)


# print()
point_data = points_to_geodataframe(outlet_snap_data + points, auth = proj_auth, code = proj_code, out_shape = f'{projBase}/Watershed/Shapes/outlets_tmp.gpkg')

# print()
points_template_gdf["canDrop"] = "Yes"
counter = 1
for index, row in point_data.iterrows():

    report(f"processing point {index}       ")
    
    new_row = {'PTSOURCE':0, 'RES': 0, 'INLET': 0, 'ID': counter, 'PointId': counter, 'geometry': row['geometry'], 'canDrop': 'Yes'}
    if counter >= len(points_template_gdf):
        new_row['canDrop'] = "No"
    new_row_df = pandas.DataFrame([new_row])

    points_template_gdf = geopandas.GeoDataFrame(pandas.concat([points_template_gdf, new_row_df], ignore_index=True), crs = points_template_gdf.crs, geometry='geometry')

    # points_template_gdf = points_template_gdf.append(
    #     {'PTSOURCE':0, 'RES': 0, 'INLET': 0, 'ID': counter, 'PointId': counter, 'geometry': row['geometry']},
    #     ignore_index = True
    # )

    counter += 1

print(f'\n  > removing points that are too close to each other (within {variables.data_resolution / 1000}m) [{region}]')
ptCoords        = np.column_stack([points_template_gdf.geometry.x.values, points_template_gdf.geometry.y.values])
ptTree          = cKDTree(ptCoords)
ptPairs         = ptTree.query_pairs(variables.data_resolution / 1000)

points_to_remove = set()
for i, j in ptPairs:
    if i in points_to_remove or j in points_to_remove: continue
    canDropI = points_template_gdf.iloc[i].get('canDrop', 'No')
    canDropJ = points_template_gdf.iloc[j].get('canDrop', 'No')
    if canDropI == "Yes" and canDropJ == "Yes":
        points_to_remove.add(j)
        report(f"removing point {j} (too close to point {i})       ")

points_template_gdf = points_template_gdf.drop(index=list(points_to_remove)).reset_index(drop=True)



points_template_gdf.crs = f"{proj_auth}:{proj_code}".lower()

lakesFN                 = geopandas.read_file(f'{projBase}/Watershed/Shapes/lakes-grand-{proj_auth}-{proj_code}.shp')
buffered_polygons       = lakesFN.geometry.buffer(variables.data_resolution * 10)     # Create a buffer around the polygons
union_buffer            = buffered_polygons.unary_union    # Combine all buffered polygons into a single geometry

# Select points that are not within the buffered area
points_template_gdf = points_template_gdf[~points_template_gdf.geometry.within(union_buffer)]

# remove points that are within 1m distance of each other
coords1m        = np.column_stack([points_template_gdf.geometry.x.values, points_template_gdf.geometry.y.values])
tree1m          = cKDTree(coords1m)
pairs1m         = tree1m.query_pairs(1.0)
remove1m        = set()
for i, j in pairs1m:
    if i not in remove1m and j not in remove1m:
        remove1m.add(j)

points_template_gdf = points_template_gdf.drop(index=list(remove1m)).reset_index(drop=True)



# if running for a subregion, clip by subregion mask and add routing points
subregionsFn = f'../model-data/{region}/shapes/subregions.gpkg'
if subDir is not None and exists(subregionsFn):
    subId       = subDir.split('-')[0]
    masksGdf    = geopandas.read_file(subregionsFn, layer='masks')
    pointsGdf   = geopandas.read_file(subregionsFn, layer='points')

    # clip by subregion mask
    maskRow = masksGdf[masksGdf['subregion'] == subId]
    if not maskRow.empty:
        points_template_gdf = geopandas.clip(points_template_gdf, maskRow)

    # add routing points
    for _, pt in pointsGdf.iterrows():
        if pt['OUTLET_MASK'] == subId:
            newRow = {'PTSOURCE': 0, 'RES': 0, 'INLET': 0, 'ID': 0, 'PointId': 0, 'geometry': pt.geometry}
            points_template_gdf = geopandas.GeoDataFrame(pandas.concat([points_template_gdf, pandas.DataFrame([newRow])], ignore_index=True), crs=points_template_gdf.crs, geometry='geometry')

        if pt['INLET_MASK'] == subId:
            newRow = {'PTSOURCE': 0, 'RES': 0, 'INLET': 1, 'ID': 0, 'PointId': 0, 'geometry': pt.geometry}
            points_template_gdf = geopandas.GeoDataFrame(pandas.concat([points_template_gdf, pandas.DataFrame([newRow])], ignore_index=True), crs=points_template_gdf.crs, geometry='geometry')

    # deduplicate points within 1m after adding routing points
    dedupCoords = np.column_stack([points_template_gdf.geometry.x.values, points_template_gdf.geometry.y.values])
    dedupTree   = cKDTree(dedupCoords)
    dedupPairs  = dedupTree.query_pairs(1.0)

    dedupRemove = set()
    for i, j in dedupPairs:
        if i not in dedupRemove and j not in dedupRemove:
            dedupRemove.add(j)

    points_template_gdf = points_template_gdf.drop(index=list(dedupRemove)).reset_index(drop=True)

    # renumber IDs
    points_template_gdf['ID']       = range(1, len(points_template_gdf) + 1)
    points_template_gdf['PointId']  = points_template_gdf['ID']

    print(f'  > added routing points for subregion {subDir} ({len(points_template_gdf)} total points)')

points_template_gdf.to_file(f'{projBase}/Watershed/Shapes/outlets.shp', driver = 'ESRI Shapefile')
print()
