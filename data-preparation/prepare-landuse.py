#!/bin/python3

'''
This script prepares the landuse data for the whole world at a selected resolution.
It is part of the data preparation scripts for the  COmmunity SWAT+ Model (CoSWAT-Global)
development. A project aimed at providing a community contributed global SWAT+ model
initiated and led by Celray James CHAWANDA.

Author  : Celray James CHAWANDA
Date    : 14/07/2022
Contact : celray@chawanda.com
Licence : MIT
GitHub  : github.com/celray
'''

# imports
import multiprocessing as mp

import wget, sys, os
from cjfx import delete_file, file_name, list_files, resample_raster, exists, copy_file, list_folders, ignore_warnings, create_path
from osgeo import gdal

ignore_warnings()

# change working directory
me = os.path.realpath(__file__)
os.chdir(os.path.dirname(me))

import datavariables as variables



if __name__ == "__main__":

    print("# preparing land use data...")
    # variables
    single_year     = True

    year_model      = variables.esa_landuse_year
    years_download  = range(1992, 2016)

    final_raster    = variables.esa_final_raster

    if len(sys.argv) < 2:
        print(f"! select a region for which to prepare the dataset. options are: {', '.join(list_folders('./resources/regions/'))}\n")
        sys.exit()
    
    regions = sys.argv[1:]

    details = {
        'auth': variables.final_proj_auth,
        'code': variables.final_proj_code,
        'year_model': variables.esa_landuse_year,
    }

    # download
    create_path('./landuse-ws/')
    if single_year:
        link = variables.esa_base_path.format(year = year_model)
        # raster_fn = f"./landuse-ws/ESACCI-LC-L4-LCCS-Map-300m-P1Y-{year_model}-v2.0.7.tif"
        raster_fn = "./landuse-ws/ricemap-v1-2025.tif"
        if not exists(raster_fn):
            wget.download(f'ftp://geo10.elie.ucl.ac.be/{link}', f'{raster_fn}')
            print()
    else:
        pool = mp.Pool(variables.processes)

        jobs = []
        for year in years_download:
            link = variables.esa_base_path.format(year = year)
            raster_fn = f"./landuse-ws/ESACCI-LC-L4-LCCS-Map-300m-P1Y-{year}-v2.0.7.tif"

            if not exists(raster_fn):
                jobs.append([f'ftp://geo10.elie.ucl.ac.be/{link}', f'{raster_fn}'])

        results = pool.starmap_async(wget.download, jobs)
        results.get()
        print()

    ds = None
    for region in regions:

        details['region'] = region

        # gdal.WarpOptions()

        print(f"\t# setting bounds to  {variables.cutline.format(**details)}")
        print("\t> creating look up table")
        # Use Warp with precise settings
        ds = gdal.Warp(final_raster.format(**details),
                "./landuse-ws/ricemap-v1-2025.tif", 
                # f"./landuse-ws/ESACCI-LC-L4-LCCS-Map-300m-P1Y-{year_model}-v2.0.7.tif", 
                cropToCutline=True,
                dstSRS='{auth}:{code}'.format(**details), 
                resampleAlg="mode", 
                srcNodata=0, 
                dstNodata=-999,
                outputType=gdal.GDT_Int16, 
                xRes=variables.data_resolution, yRes=variables.data_resolution,
                targetAlignedPixels=True,  # Ensure output pixels are aligned to the target coordinates
                cutlineDSName=variables.cutline.format(**details)
        )

        copy_file('./resources/landuse_lookup.csv', '../model-data/{region}/tables/worldLanduseLookup.csv'.format(**details), v = False)

        ref_raster = None
    ds = None


