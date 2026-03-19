#!/bin/python3

'''
This script prepares the DEM for the whole world at a selected resolution.
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
from cjfx import download_file, unzip_file, list_files, delete_file, file_name, resample_raster, clip_raster, set_nodata
import multiprocessing as mp
from osgeo_utils import gdal_merge
from osgeo import gdal
import datavariables as variables


# variables
dem_bas_url = "http://srtm.csi.cgiar.org/wp-content/uploads/files/srtm_5x5/TIFF/srtm_{url_easting}_{url_northing}.zip"
tile_urls   = []
final_raster = "../model-data/raster/world-dem-srtm.tif"

# the range just ensures every possible tile is captured in the download
pairs_min_max = [0,190]

if __name__ == "__main__":

    # append the pairs to download list
    for easting in range(pairs_min_max[0], pairs_min_max[1]):
        for northing in range(pairs_min_max[0], pairs_min_max[1]):
            tile_urls.append([dem_bas_url.format(url_easting = easting if easting > 9 else f"0{easting}", url_northing = northing if northing > 9 else f"0{northing}",), "./dem-ws/srtm/tiles/srtm_{url_easting}_{url_northing}.zip".format( url_easting = easting if easting > 9 else f"0{easting}", url_northing = northing if northing > 9 else f"0{northing}",)])
    
    # create a pool of workers
    pool = mp.Pool(variables.processes)

    # download in parallel. these files have a resolution of 0.0008333333333333333868
    results = pool.starmap_async(download_file, tile_urls)
    results.get()  # wait fot download to complete

    # extract the downloaded files
    zip_dem_files = list_files("./dem-ws/srtm/tiles")       # list all remaining zipped files files

    unzip_list = []
    for fn in zip_dem_files:
        unzip_list.append([fn, "./dem-ws/srtm/unzipped/"])
    
    # unzip in parallel
    results = pool.starmap_async(unzip_file, unzip_list)
    results.get()

    [delete_file(fname) for fname in list_files("./dem-ws/srtm/unzipped", "hdr")]
    [delete_file(fname) for fname in list_files("./dem-ws/srtm/unzipped", "tfw")]
    [delete_file(fname) for fname in list_files("./dem-ws/srtm/unzipped", "txt")]

    unzip_dem_files = list_files("./dem-ws/srtm/unzipped", "tif")   # list files that have been unzipped

    jobs = []
    [jobs.append([fn, f"./dem-ws/srtm/resampled/{file_name(fn, extension=True)}", variables.data_resolution]) for fn in unzip_dem_files]

    results = pool.starmap_async(resample_raster, jobs)
    results.get()

    [delete_file(fname) for fname in list_files("./dem-ws/srtm/unzipped", "tif")]

    resampled_dem_files = list_files("./dem-ws/srtm/resampled", "tif")   # list files that have been resampled

    args_ = ['', '-init', '-999', '-o', './dem-ws/srtm/global-srtm.tif']
    [args_.append(tif_file) for tif_file in resampled_dem_files]
    gdal_merge.main(args_)

    set_nodata("./dem-ws/srtm/global-srtm.tif", final_raster)


