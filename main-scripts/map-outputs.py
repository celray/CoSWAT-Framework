#!/bin/python3

'''
this script coordinates the mapping of the COmmunity SWAT+ Model
(CoSWAT-Global) results. A project aimed at providing a community
contributed global SWAT+ model initiated and led by Celray James
CHAWANDA.

Author  : Celray James CHAWANDA
Date    : 23/02/2023

Contact : celray@chawanda.com
          celray.chawanda.com

Licence : MIT 2023
GitHub  : github.com/celray
'''

import os
import sys
from cjfx import *
import argparse

ignore_warnings()

# change working directory
me = os.path.realpath(__file__)
os.chdir(os.path.dirname(me))

import datavariables as variables


def make_gpkg(region, version, map_columns, map_log):

    print(f'\t> mapping {region}')

    hrus2shapefile_fn   = f'../model-setup/CoSWATv{version}/{region}/Watershed/Shapes/hrus2.shp'
    hrus_wb_aa_fn       = f'../model-setup/CoSWATv{version}/{region}/Scenarios/Default/TxtInOut/hru_wb_aa.txt'

    # check if necessay files exist
    if not (exists(hrus2shapefile_fn) and exists(hrus_wb_aa_fn)):
        write_to(map_log, f'{datetime.datetime.now()} - ! cannot map results from {region}', mode='a')
        print(f'\t! cannot map results from {region}')
        print(f'\t  - check that {hrus2shapefile_fn} exists')
        print(f'\t  - check that {hrus_wb_aa_fn} exists')
        return None
    
    hrus_gpd    = geopandas.read_file(hrus2shapefile_fn)
    
    hrus_gpd['region'] = \
                f'{region}'

    wb_pd       = pandas.read_csv(hrus_wb_aa_fn, skiprows=1, delim_whitespace=True, low_memory=False)
    wb_pd       = wb_pd[wb_pd['jday'] != 'mm']


    wb_pd['gis_id']     = pandas.to_numeric(wb_pd['gis_id'], errors='coerce')
    hrus_gpd['HRUS']    = pandas.to_numeric(hrus_gpd['HRUS'], errors='coerce')

    for map_col in map_columns:
        wb_pd[map_col] = pandas.to_numeric(wb_pd[map_col], errors='coerce')

    merged_pd   = pandas.merge(hrus_gpd, wb_pd, how = 'inner', left_on='HRUS', right_on='gis_id')

    maps_gpd    = geopandas.GeoDataFrame(merged_pd, geometry='geometry', crs = hrus_gpd.crs)
    
    if len(maps_gpd.index) == 0:
        print(f'\t! cannot map results from {region}')
        print(f'\t  - check that the model was fully run')
        return None

    fn = f'../model-setup/CoSWATv{version}/{region}/Evaluation/Shape/wb_map_vars.gpkg'
    create_path(fn)
    delete_file(fn, v = False)
    maps_gpd.to_file(fn)

    return maps_gpd


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="a terminal script for mapping the coswat models.")

    parser.add_argument("r", help="the name of the region to run the model for. If not specified, all regions will be processed.", nargs='*', default=[])
    parser.add_argument("--v", help="the version of the model setup to use. If not specified, the datavariables value will be used.", nargs='?', default=None)

    args = parser.parse_args()

    # get model setup version
    if args.v is None: version_ = variables.version
    else: version_ = args.v  

    # get regions
    if len(args.r) > 0:
        regions = args.r
        if len(regions) == 1 and regions[0] == 'all':
            regions = list_folders(f"../model-setup/CoSWATv{version_}/")
    else: regions = list_folders(f"../model-setup/CoSWATv{version_}/")

    if not exists(f"../model-setup/CoSWATv{version_}"):
        print(f'\t! the version, CoSWATv{version_}, does not exist, the following versions are available:')
        for v in list_folders('../model-setup/'):
            if v.startswith('CoSWATv'):
                print(f'\t\t- {v}')
        print(f'\t> please specify a valid version using the --v argument')
        sys.exit(1)

    map_columns_         = ["precip", "snofall", "snomlt", "surq_gen", "latq", "wateryld", "perc", "et", "ecanopy", "eplant", "esoil", "surq_cont", "cn", "sw_init", "sw_final", "sw_ave", "sw_300", "sno_init", "sno_final", "snopack", "pet", "qtile", "irr", "surq_runon", "latq_runon", "overbank", "surq_cha", "surq_res", "surq_ls", "latq_cha", "latq_res", "latq_ls", "satex", "satex_chan", "sw_change", "lagsurf", "laglatq", "lagsatex"]
    out_shape_map_fn     = f'../model-outputs/version-{version_}/maps/shapefiles/map-data.gpkg'

    cumulative = None

    if variables.individual_maps:
        delete_file(out_shape_map_fn, v = False)

    map_log_ = write_to(f'../model-outputs/version-{version_}/maps/map.log', '', mode='o')

    jobs = []
    if variables.individual_maps:
        for region_ in regions:
            jobs.append([region_, version_, map_columns_, map_log_])
            
        # Create a multiprocessing Pool
        with multiprocessing.Pool(variables.processes) as pool:
            results = [pool.apply_async(make_gpkg, job) for job in jobs]

            for result in results:
                maps_gpd_ = result.get() 
                if maps_gpd_ is None: continue
                
                if variables.remerge_maps:
                    if cumulative is None:
                        cumulative = maps_gpd_
                    else:
                        cumulative = geopandas.GeoDataFrame(pandas.concat([cumulative, maps_gpd_], ignore_index=True), geometry='geometry', crs = maps_gpd_.crs)


    else:
        if variables.remerge_maps:
            print(f'\t> reading previous cumulative output vector data')
            cumulative = geopandas.read_file(out_shape_map_fn)

    if not cumulative is None:
        if variables.remerge_maps:
            create_path(out_shape_map_fn)
            delete_file(out_shape_map_fn, v = False)
            cumulative.to_file(out_shape_map_fn)
