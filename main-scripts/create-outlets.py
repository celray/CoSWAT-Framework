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

args = sys.argv

all_models = list_all_files("../model-setup/", "qgs")

if len(args) < 3:
    versions = {}

    for model in all_models:
        model = model.split("/")[-1].split("\\")
        
        v = model[0].lower().replace('coswatv', '')
        r = model[1]

        if not v in versions:
            versions[v] = []
        
        versions[v].append(r)
            
    print("please select a version and region (...py version region). these are available:")
    
    for k in versions:
        print(f"    {v}")
        for m in versions[k]:
            print(f"\t- {m}")
    
    quit()

version = args[1]
region  = args[2]

proj_auth = variables.final_proj_auth
proj_code = variables.final_proj_code

channels_fn = f'../model-setup/CoSWATv{version}/{region}/Watershed/Shapes/dem-aster-{proj_auth.lower()}-{proj_code}channel/dem-aster-{proj_auth.upper()}-{proj_code}channel.shp'
channels_fn = f'../model-setup/CoSWATv{version}/{region}/Watershed/Shapes/dem-aster-{proj_auth.lower()}-{proj_code}channel/dem-aster-{proj_auth.upper()}-{proj_code}channel.shp'
grdc_shp_fn = f'../model-data/{region}/shapes/grdc_stations-{proj_auth.upper()}-{proj_code}.gpkg'


if not exists(channels_fn):
    channels_fn = f'../model-setup/CoSWATv{version}/{region}/Watershed/Shapes/dem-aster-{proj_auth.upper()}-{proj_code}channel.shp'
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
# get closest points
kept_points    = []
skipped_points  = []

for index, row in grdc_point_gdf.iterrows():
    if row.name in skipped_points:
        continue
    if row.name in kept_points:
        continue

    closest_points = []
    for inner_idx, inner_row in grdc_point_gdf.iterrows():
        if distance([inner_row.X, inner_row.Y], [row.X, row.Y]) <= variables.proximity_thres:
            closest_points.append(inner_row)

    if len(closest_points) >= 2:
        kept_index          = closest_points[0].name
        kept_index_dist     = closest_points[0].min_dist_to_lines

        for close_pt in closest_points:
            if close_pt.min_dist_to_lines < kept_index_dist:
                kept_index      = close_pt.name
                kept_index_dist = close_pt.min_dist_to_lines            

        kept_points.append(kept_index)

        for close_pt in closest_points:
            if (not close_pt.name in skipped_points) and (not close_pt.name in kept_points):
                skipped_points.append(close_pt.name)
    else:
        kept_points.append(index)



for index in skipped_points:
    grdc_point_gdf = grdc_point_gdf.drop(index)


grdc_point_gdf.reset_index(inplace=True)
channels_gdf.reset_index(inplace=True)


print(f'  > attaching points to channels [{region}]')
# find cloest feature

close_features = {}

for index, row in grdc_point_gdf.iterrows():
    
    close_features[row.name]    = None
    current_distance            = None

    for inner_index, inner_row in channels_gdf.iterrows():
        if close_features[row.name] is None:
            close_features[row.name] = inner_index
            current_distance = inner_row.geometry.distance(row.geometry)
        else:
            if inner_row.geometry.distance(row.geometry) < current_distance:
                close_features[row.name] = inner_index
                current_distance = inner_row.geometry.distance(row.geometry)


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
point_data = points_to_geodataframe(outlet_snap_data + points, auth = proj_auth, code = proj_code, out_shape = f'../model-setup/CoSWATv{version}/{region}/Watershed/Shapes/outlets_tmp.gpkg')

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
# Remove points that are within 1 kilometer of each other
points_to_remove = []
for i, row_i in points_template_gdf.iterrows():
    if i in points_to_remove:
        continue
    
    for j, row_j in points_template_gdf.iterrows():
        if i >= j or j in points_to_remove:
            continue
        
        # Calculate distance between points
        dist = row_i.geometry.distance(row_j.geometry)
        if dist < (variables.data_resolution / 1000):  # within the defined resolution
            if (row_j.canDrop == "Yes") and (row_i.canDrop == "Yes"):
                points_to_remove.append(j)
                report(f"removing point {j} (too close to point {i})       ")

# instead of removing randomly like above, use point with higher catchment area




# Remove the identified points
points_template_gdf = points_template_gdf.drop(points_to_remove).reset_index(drop=True)



points_template_gdf.crs = f"{proj_auth}:{proj_code}".lower()

lakesFN                 = geopandas.read_file(f'../model-setup/CoSWATv{version}/{region}/Watershed/Shapes/lakes-grand-{proj_auth}-{proj_code}.shp')
buffered_polygons       = lakesFN.geometry.buffer(variables.data_resolution * 10)     # Create a buffer around the polygons
union_buffer            = buffered_polygons.unary_union    # Combine all buffered polygons into a single geometry

# Select points that are not within the buffered area
points_template_gdf = points_template_gdf[~points_template_gdf.geometry.within(union_buffer)]

# remove points that are within 1m distance of each other.
points_to_remove_1m = []
for i, row_i in points_template_gdf.iterrows():
    if i in points_to_remove_1m:
        continue
    
    for j, row_j in points_template_gdf.iterrows():
        if i >= j or j in points_to_remove_1m:
            continue
        
        # Calculate distance between points
        dist = row_i.geometry.distance(row_j.geometry)
        if dist < 1:  # within 1 meter
            points_to_remove_1m.append(j)
            report(f"removing point {j} (within 1m of point {i})       ")

# Remove the identified points
points_template_gdf = points_template_gdf.drop(points_to_remove_1m).reset_index(drop=True)



points_template_gdf.to_file(f'../model-setup/CoSWATv{version}/{region}/Watershed/Shapes/outlets.shp', driver = 'ESRI Shapefile')
print()
