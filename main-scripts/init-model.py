#!/bin/python3

import sys, os, json
from cjfx import *
from coswatFX import resolveRegions
import argparse

ignore_warnings()

# change working directory
me = os.path.realpath(__file__)
os.chdir(os.path.dirname(me))

import datavariables as variables
from resources.template_proj import template_string

if __name__ == '__main__':

    # create argument parser
    parser = argparse.ArgumentParser(description="a script to initialise a SWAT+ project for a given region")

    parser.add_argument("r", help="the name of the region to initialise the model for. If not specified, all regions will be processed.", nargs='*', default=[])
    parser.add_argument("--v", help="the version of the model setup to use. If not specified, the datavariables value will be used.", nargs='?', default=None)
    parser.add_argument("--sr", help="subregion id(s) to initialise", nargs='*', default=None)
    # if arg -m is passed, it means this was a mannual run
    parser.add_argument("--m", help="indicates this is a mannual run", action='store_true')

    args = parser.parse_args()


    print('\n# initialising SWAT+ project')
    version = variables.version

    if args.v:
        version = args.v

    if len(args.r) > 0: 
        regions = resolveRegions(args.r)
        if len(regions) == 1 and regions[0] == 'all': regions = list_folders('../model-data/')
    else: regions = list_folders('../model-data/')

    details = {
        'auth': variables.final_proj_auth,
        'code': variables.final_proj_code,
    }

    for region in regions:

        continent   = region.split('-')[0]
        zone        = region.split('-')[1]

        data_dir    = f'../model-data/{region}'
        dst_dir     = create_path(f'../model-setup/CoSWATv{version}/')

        # check if subregions exist
        subregionsFn = f"{data_dir}/shapes/subregions.gpkg"
        if exists(subregionsFn):
            subregionsGdf = geopandas.read_file(subregionsFn, layer='masks')
            subList = []
            for _, row in subregionsGdf.iterrows():
                subId   = row['subregion']
                subName = row.get('name', None)
                if subName: subList.append(f"{subId}-{subName}")
                else: subList.append(f"{subId}")
            # filter by --sr if specified
            if args.sr is not None:
                subList = [s for s in subList if s.split('-')[0] in args.sr]
                if not subList:
                    print(f"\t! no matching subregions for --sr {args.sr}")
                    continue

            print(f"\t> subregions to init: {', '.join(subList)}")

            # build subregion id lookup and generate connectivity schema
            subLookup = {}
            for _, row in subregionsGdf.iterrows():
                subId   = row['subregion']
                subName = row.get('name', None)
                if subName: subLookup[subId] = f"{subId}-{subName}"
                else: subLookup[subId] = f"{subId}"

            pointsGdf   = geopandas.read_file(subregionsFn, layer='points')
            connections = []
            for _, pt in pointsGdf.iterrows():
                connections.append({
                    "from":  subLookup.get(pt['OUTLET_MASK'], pt['OUTLET_MASK']),
                    "to":    subLookup.get(pt['INLET_MASK'], pt['INLET_MASK']),
                    "point": [round(pt.geometry.x, 2), round(pt.geometry.y, 2)],
                })

            schema = {
                "region":       region,
                "subregions":   subList,
                "connections":  connections,
            }

        else:
            schema      = None
            subList     = [None]

        # data source paths
        demFn           = f"{data_dir}/raster/dem-aster-{variables.final_proj_auth}-{variables.final_proj_code}.tif"
        landuseFn       = f"{data_dir}/raster/landuse-esa-{variables.esa_landuse_year}-{variables.final_proj_auth}-{variables.final_proj_code}.tif"
        soilsFn         = f"{data_dir}/raster/soils-fao-{variables.final_proj_auth}-{variables.final_proj_code}.tif"

        lakesFn         = f"{data_dir}/shapes/lakes-grand-{variables.final_proj_auth}-{variables.final_proj_code}.shp"
        burnShapeFn     = f"{data_dir}/shapes/burn-shape-{variables.final_proj_auth}-{variables.final_proj_code}.shp"

        # read shapefiles once for all subregions
        burnShapeGdf    = geopandas.read_file(burnShapeFn)
        lakesGdf        = geopandas.read_file(lakesFn)

        # delete existing model before initialising
        if args.sr is not None:
            # only delete specific subregion directories
            for sub in subList:
                subPath = f'{dst_dir}/{region}/{sub}/'
                if exists(subPath):
                    delete_path(subPath)
                    print(f"\t> removed existing model for {region}/{sub}")
        else:
            if exists(f'{dst_dir}/{region}/'):
                print()
                delete_path(f'{dst_dir}/{region}/')
                print(f"\t> removed existing model for {region}")

        # write connectivity schema (skip if only re-initing specific subregions)
        if schema is not None and args.sr is None:
            schemaPath = f'{dst_dir}/{region}/schema.json'
            create_path(schemaPath, v=False)
            write_to(schemaPath, json.dumps(schema, indent=4))
            print(f"\t> wrote connectivity schema for {region}")

        os.system(f'prepare-topo-parallel.py {region} --v {version}')

        for sub in subList:
            if sub is not None:
                projName    = f"{region}/{sub}"
                qgsName     = f"{region}-{sub}"
            else:
                projName    = region
                qgsName     = region

            projDir     = f'{dst_dir}/{projName}'

            report(f"\t> initializing {projName}.qgs                ")

            # create project structure
            create_path(f"{projDir}/")
            dirDEM          = create_path(f"{projDir}/Watershed/Rasters/DEM/")
            dirLandscape    = create_path(f"{projDir}/Watershed/Rasters/Landscape/")
            dirLanduse      = create_path(f"{projDir}/Watershed/Rasters/Landuse/")
            dirSoil         = create_path(f"{projDir}/Watershed/Rasters/Soil/")

            dirShapes       = create_path(f"{projDir}/Watershed/Shapes/")

            copy_file(demFn, f"{dirDEM}/{file_name(demFn)}")
            copy_file(landuseFn, f"{dirLanduse}/{file_name(landuseFn)}")
            copy_file(soilsFn, f"{dirSoil}/{file_name(soilsFn)}")


            with zipfile.ZipFile("../data-preparation/resources/shapes.dat", 'r') as zip_ref:
                zip_ref.extractall(dirShapes)

            shapesFiles = list_files(f'{dirShapes}')
            for shapesFile in shapesFiles:
                if "[dem]" in shapesFile:
                    copy_file(shapesFile, shapesFile.replace('[dem]', f'{file_name(demFn, extension=False)}'), delete_source=True)

            burnShapeGdf.to_file(f"{dirShapes}/{file_name(burnShapeFn)}")

            # clip lakes by subregion mask so only relevant reservoirs are included
            if sub is not None:
                subId       = sub.split('-')[0]
                maskGeom    = subregionsGdf[subregionsGdf['subregion'] == subId]
                subLakes    = geopandas.clip(lakesGdf, maskGeom)
                subLakes.to_file(f"{dirShapes}/{file_name(lakesFn)}")
            else:
                lakesGdf.to_file(f"{dirShapes}/{file_name(lakesFn)}")

            # prepare qgs project
            projectString = template_string.format(
                project_name        = qgsName,
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
                burnInDepth         = variables.burnInDepth,

                dem_file_name       = file_name(demFn, extension=False),
                land_use_file_name  = file_name(landuseFn, extension=False),
                soils_file_name     = file_name(soilsFn, extension=False),
                burn_file_name      = file_name(burnShapeFn, extension=False),
                lakes_file_name     = file_name(lakesFn, extension=False) if variables.include_reservoirs else "",

                dem_file_name_underscore_hyphens        = file_name(demFn, extension=False).replace('-', '_'),
                land_use_file_name_underscore_hyphens   = file_name(landuseFn, extension=False).replace('-', '_'),
                soils_file_name_underscore_hyphens      = file_name(soilsFn, extension=False).replace('-', '_'),
                burn_file_name_underscore_hyphens       = file_name(burnShapeFn, extension=False).replace('-', '_'),
                lakes_file_name_underscore_hyphens      = file_name(lakesFn, extension=False).replace('-', '_') if variables.include_reservoirs else "",
            )

            write_to(f'{projDir}/{qgsName}.qgs', projectString)
            print(f'\n\t> initialised {projName}.qgs\n')

            if args.m:
                answer = input("run qswatplus for this region? (Y/n): ")
                if answer.lower() in ['y', 'yes', '']:
                    os.system(f'run-qswatplus.py {region} --m')

print()
