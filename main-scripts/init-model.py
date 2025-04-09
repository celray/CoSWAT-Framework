#!/bin/python3

import sys, os
from cjfx import *
import sqlalchemy

ignore_warnings()

# change working directory
me = os.path.realpath(__file__)
os.chdir(os.path.dirname(me))

import datavariables as variables
from resources.template_proj import template_string
import resources.project_init_template as template

if __name__ == '__main__':
    
    print('\n# initialising SWAT+ project')
    if len(sys.argv) < 3:
        print(f"! select version and a region for which to initialise the SWAT+ project. options are: {', '.join(list_folders('../data-preparation/resources/regions/'))}\n")
        sys.exit()

    version = sys.argv[1]
    regions = sys.argv[2:]
    
    details = {
        'auth': variables.final_proj_auth,
        'code': variables.final_proj_code,
    }

    for region in regions:
        report(f"\t> initializing {region}.qgs                ")

        continent = region.split('-')[0]
        zone = region.split('-')[1]

        dst_dir = create_path(f'../model-setup/CoSWATv{version}/')

        if exists(f'{dst_dir}/{region}/{region}.qgs'):
            # remove the directory path before continuing
            print()
            delete_path(f'{dst_dir}/{region}/')
            print("\t> creating a new project...")

        proj_name   = f"{region}"
        proj_dir    = f'{dst_dir}/{proj_name}'

        data_dir    = f'../model-data/{proj_name}'
        details['data_dir'] = data_dir

        # data source paths
        dem_fn          = f"{data_dir}/raster/dem-aster-{variables.final_proj_auth}-{variables.final_proj_code}.tif"
        # landuse_fn      = f"{data_dir}/raster/landuse-esa-{variables.esa_landuse_year}-{variables.final_proj_auth}-{variables.final_proj_code}.tif"
        landuse_fn      = "{data_dir}/raster/ricemap-v1-2025-{auth}-{code}.tif".format(**details)
        soils_fn        = f"{data_dir}/raster/soils-fao-{variables.final_proj_auth}-{variables.final_proj_code}.tif"

        lakes_fn        = f"{data_dir}/shapes/lakes-grand-{variables.final_proj_auth}-{variables.final_proj_code}.shp"
        burn_shape_fn   = f"{data_dir}/shapes/burn-shape-{variables.final_proj_auth}-{variables.final_proj_code}.shp"

        # create project structure
        create_path(f"{proj_dir}/")
        dir_DEM         = create_path(f"{proj_dir}/Watershed/Rasters/DEM/")
        dir_Landscape   = create_path(f"{proj_dir}/Watershed/Rasters/Landscape/")
        dir_Landuse     = create_path(f"{proj_dir}/Watershed/Rasters/Landuse/")
        dir_Soil        = create_path(f"{proj_dir}/Watershed/Rasters/Soil/")

        dir_Shapes      = create_path(f"{proj_dir}/Watershed/Shapes/")

        copy_file(dem_fn, f"{dir_DEM}/{file_name(dem_fn)}")
        copy_file(landuse_fn, f"{dir_Landuse}/{file_name(landuse_fn)}")
        copy_file(soils_fn, f"{dir_Soil}/{file_name(soils_fn)}")
        
        
        with zipfile.ZipFile("../data-preparation/resources/shapes.dat", 'r') as zip_ref:
            zip_ref.extractall(dir_Shapes)
        
        shapes_files = list_files(f'{dir_Shapes}')
        for shapes_file in shapes_files:
            if "[dem]" in shapes_file:
                copy_file(shapes_file, shapes_file.replace('[dem]', f'{file_name(dem_fn, extension=False)}'), delete_source=True)

        geopandas.read_file(burn_shape_fn).to_file(f"{dir_Shapes}/{file_name(burn_shape_fn)}")
        geopandas.read_file(lakes_fn).to_file(f"{dir_Shapes}/{file_name(lakes_fn)}")

        # prepare qgs project
        project_string = template_string.format(
            project_name        = proj_name,
            authid              = '{auth}:{code}'.format(**details),

            rivs_1_id           = f'{rand_apha_num(8)}_{rand_apha_num(4)}_{rand_apha_num(4)}_{rand_apha_num(4)}_{rand_apha_num(12)}',
            channel_shape_id    = f'{rand_apha_num(8)}_{rand_apha_num(4)}_{rand_apha_num(4)}_{rand_apha_num(4)}_{rand_apha_num(12)}',
            dem_id              = f'{rand_apha_num(8)}_{rand_apha_num(4)}_{rand_apha_num(4)}_{rand_apha_num(4)}_{rand_apha_num(12)}',
            lsus_shape_id       = f'{rand_apha_num(8)}_{rand_apha_num(4)}_{rand_apha_num(4)}_{rand_apha_num(4)}_{rand_apha_num(12)}',
            hillshade_id        = f'{rand_apha_num(8)}_{rand_apha_num(4)}_{rand_apha_num(4)}_{rand_apha_num(4)}_{rand_apha_num(12)}',
            outlets_id          = f'{rand_apha_num(8)}_{rand_apha_num(4)}_{rand_apha_num(4)}_{rand_apha_num(4)}_{rand_apha_num(12)}',
            landuse_id          = f'{rand_apha_num(8)}_{rand_apha_num(4)}_{rand_apha_num(4)}_{rand_apha_num(4)}_{rand_apha_num(12)}',
            reservoir_shape_id  = f'{rand_apha_num(8)}_{rand_apha_num(4)}_{rand_apha_num(4)}_{rand_apha_num(4)}_{rand_apha_num(12)}',
            se_outlets_shape_id = f'{rand_apha_num(8)}_{rand_apha_num(4)}_{rand_apha_num(4)}_{rand_apha_num(4)}_{rand_apha_num(12)}',
            soils_id            = f'{rand_apha_num(8)}_{rand_apha_num(4)}_{rand_apha_num(4)}_{rand_apha_num(4)}_{rand_apha_num(12)}',
            burn_shape_id       = f'{rand_apha_num(8)}_{rand_apha_num(4)}_{rand_apha_num(4)}_{rand_apha_num(4)}_{rand_apha_num(12)}',
            stream_shape_id     = f'{rand_apha_num(8)}_{rand_apha_num(4)}_{rand_apha_num(4)}_{rand_apha_num(4)}_{rand_apha_num(12)}',
            subbasins_id        = f'{rand_apha_num(8)}_{rand_apha_num(4)}_{rand_apha_num(4)}_{rand_apha_num(4)}_{rand_apha_num(12)}',
            lakes_id            = f'{rand_apha_num(8)}_{rand_apha_num(4)}_{rand_apha_num(4)}_{rand_apha_num(4)}_{rand_apha_num(12)}',
            
            thresholdCh         = variables.thresholdCh,
            thresholdSt         = variables.thresholdSt,

            dem_file_name       = file_name(dem_fn, extension=False),
            land_use_file_name  = file_name(landuse_fn, extension=False),
            soils_file_name     = file_name(soils_fn, extension=False),
            burn_file_name      = file_name(burn_shape_fn, extension=False),
            lakes_file_name     = file_name(lakes_fn, extension=False),
            
            dem_file_name_underscore_hyphens        = file_name(dem_fn, extension=False).replace('-', '_'),
            land_use_file_name_underscore_hyphens   = file_name(landuse_fn, extension=False).replace('-', '_'),
            soils_file_name_underscore_hyphens      = file_name(soils_fn, extension=False).replace('-', '_'),
            burn_file_name_underscore_hyphens       = file_name(burn_shape_fn, extension=False).replace('-', '_'),
            lakes_file_name_underscore_hyphens      = file_name(lakes_fn, extension=False).replace('-', '_'),

        )

        write_to(f'{proj_dir}/{proj_name}.qgs', project_string)
        print(f'\n\t> initialised {proj_name}.qgs\n')

print()
