#!/bin/python3

'''
This script prepares the lake data for the whole world filtered by areal threshold.
It is part of the data preparation scripts for the  COmmunity SWAT+ Model (CoSWAT-Global)
development. A project aimed at providing a community contributed global SWAT+ model
initiated and led by Celray James CHAWANDA.

Author  : Celray James CHAWANDA
Date    : 19/07/2022
Contact : celray@chawanda.com
Licence : MIT
GitHub  : github.com/celray
'''

# imports
from cjfx import clip_features, geopandas, create_path, list_folders, ignore_warnings
import time, sys, os
from shapely.geometry import Polygon, MultiPolygon

ignore_warnings()


# functions
def remove_holes(geometry):
    if geometry.geom_type == 'Polygon':
        return Polygon(geometry.exterior)
    elif geometry.geom_type == 'MultiPolygon':
        return MultiPolygon([Polygon(part.exterior) for part in geometry])
    else:
        return geometry


# change working directory
me = os.path.realpath(__file__)
os.chdir(os.path.dirname(me))

import datavariables as variables

if len(sys.argv) < 2:
    print(f"! select a region for which to prepare the dataset. options are: {', '.join(list_folders('./resources/regions/'))}\n")
    sys.exit()

print('\n# preparing lakes data...\n')

regions = sys.argv[1:]

details = {
    'auth': variables.final_proj_auth,
    'code': variables.final_proj_code,
}

input_gdf               = geopandas.read_file(f"{variables.grand_and_lakes}")

for region in regions:
    details['region'] = region
    create_path(variables.grand_final_shp.format(**details))

    regionfn                = "./resources/regions/{region}/bounding-box-{auth}-{code}.gpkg".format(**details)
    regionfn                = "./resources/regions/{region}/outlets-buffer.gpkg".format(**details)

    mask_gdf                = geopandas.read_file(regionfn)
    clippedReservoirs       = input_gdf.clip(mask_gdf.to_crs(input_gdf.crs))

    clippedReservoirs               = clippedReservoirs.to_crs("{auth}:{code}".format(**details))
    clippedReservoirs["calcAreas"]  = clippedReservoirs.geometry.area / 1000000
    clippedReservoirs["calcVol"]    = clippedReservoirs.calcAreas * 2.1
    clippedReservoirs["RES"]        = 1

    clippedReservoirs = clippedReservoirs[clippedReservoirs.calcAreas > (variables.grand_lake_thres)]

    # Assuming 'gdf' is your GeoDataFrame with polygons
    clippedReservoirs['geometry'] = clippedReservoirs['geometry'].apply(remove_holes)

    clippedReservoirs.to_file(variables.grand_final_shp.format(**details))
    clippedReservoirs.to_file(variables.grand_final_gpkg.format(**details), driver = 'GPKG')
