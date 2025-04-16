#!/bin/python3

'''
This script prepares the soil data for the whole world at a selected resolution.
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
from osgeo import gdal
from osgeo import ogr
from osgeo import gdalconst
import sys, os
import rasterio

from cjfx import open_tif_as_array, read_from, write_to, list_folders, ignore_warnings, create_path

ignore_warnings()

# change working directory
me = os.path.realpath(__file__)
os.chdir(os.path.dirname(me))

import datavariables as variables

# functions
def rasterise_shape(shape_file:str, column_name:str, destination_tif:str, template_tif:str, no_data:int = -999) -> None:
    data = gdal.Open(template_tif, gdalconst.GA_ReadOnly)
    geo_transform = data.GetGeoTransform()
    x_min = geo_transform[0]
    y_max = geo_transform[3]
    x_max = x_min + geo_transform[1] * data.RasterXSize
    y_min = y_max + geo_transform[5] * data.RasterYSize
    x_res = data.RasterXSize
    y_res = data.RasterYSize
    mb_v = ogr.Open(shape_file)
    mb_l = mb_v.GetLayer()
    pixel_width = geo_transform[1]
    target_ds = gdal.GetDriverByName('GTiff').Create(destination_tif, x_res, y_res, 1, gdal.GDT_Int32)
    target_ds.SetGeoTransform(data.GetGeoTransform())
    target_ds.SetProjection(data.GetProjection())
    # target_ds.SetGeoTransform((x_min, pixel_width, 0, y_min, 0, pixel_width))
    band = target_ds.GetRasterBand(1)
    band.SetNoDataValue(no_data)
    band.FlushCache()
    gdal.RasterizeLayer(target_ds, [1], mb_l, options=[f"ATTRIBUTE={column_name}"])

    target_ds = None

        

if __name__ == "__main__":

    # rasterise shapefile and clip to land masses
    if len(sys.argv) < 2:
        print(f"! select a region for which to prepare the dataset. options are: {', '.join(list_folders('./resources/regions/'))}\n")
        sys.exit()

    print('# preparing soil data...')

    regions = sys.argv[1:]

    details = {
        'auth': variables.final_proj_auth,
        'code': variables.final_proj_code,
    }


    if not os.path.exists(variables.fao_tmp_raster):
        print(f'\t> rasterising {variables.fao_soil_shape_fn.format(**details)}')
        create_path(variables.fao_tmp_raster)
        rasterise_shape(variables.fao_soil_shape_fn.format(**details), "SNUM", variables.fao_tmp_raster, variables.aster_tmp_tif)

    for region in regions:
        details['region'] = region

        print(f'\t# setting bounds to  {variables.cutline.format(**details)}')
        ds = gdal.Warp(variables.fao_final_raster.format(**details),
                       variables.fao_tmp_raster,
                       cropToCutline = True, 
                       srcNodata=-999, dstNodata=variables.no_data_value, 
                       outputType=gdal.GDT_Int16, 
                       targetAlignedPixels=True,
                       dstSRS='{auth}:{code}'.format(**details), 
                       xRes=variables.data_resolution, yRes=variables.data_resolution,
                       resampleAlg=f"mode",
                       cutlineDSName = variables.cutline.format(**details))
        ds = None

        # get all values from tif
        print('\t> getting all available soil values')
        soil_array = open_tif_as_array(variables.fao_final_raster.format(**details), big_tif=False)

        print('\t> sorting soil data')
        # keep unique
        soil_values = soil_array.flatten().tolist()

        soil_values = list(dict.fromkeys(soil_values))

        # create usersoil and soil lookup
        usersoil_dict = {}
        usersoil_fc = read_from(variables.fao_usersoil_db)

        for line in usersoil_fc:
            usersoil_dict[line.split(",")[2].replace('"', "")] = line

        print('\t> creating tables\n')
        usersoil_string = usersoil_fc[0]
        lookup_string   = "VALUE,SNAM\n"
        for value in soil_values:
            if value == variables.no_data_value: continue
            if value < 0: continue
            snam = usersoil_dict[str(value)].split(',')[3].replace('"', "")

            lookup_string +=f"{value},{snam}\n"
            usersoil_string += usersoil_dict[str(value)]

        write_to(variables.fao_lookup_fn.format(**details), lookup_string)
        write_to(variables.fao_usersoil_fn.format(**details), usersoil_string)

        # update dem incase there is no soil data
        print('\t> updating dem bounds')
        # Open raster files
        with rasterio.open(variables.fao_final_raster.format(**details)) as srcA:
            rasterA = srcA.read(1)  # Assuming single band

        with rasterio.open(variables.aster_final_raster.format(**details)) as srcB:
            rasterB = srcB.read(1)

        # Set corresponding pixels to NaN
        try:
            rasterB[rasterA == -999] = -999
        except:
            pass #rasterB[rasterA == -999] = -999

        # Save the modified raster B
        with rasterio.open(variables.aster_final_raster.format(**details), 'w', **srcB.meta) as dst:
            dst.write(rasterB, 1)
