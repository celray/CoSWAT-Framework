#!/bin/python3

'''



'''

import sys, os
from cjfx import create_polygon_geodataframe, list_folders, read_from, clip_features, exists, report, create_path, ignore_warnings

ignore_warnings()


# change working directory
me = os.path.realpath(__file__)
os.chdir(os.path.dirname(me))

import datavariables as variables

if __name__ == '__main__':
    
    print('\n# preparing bounding boxes')
    if len(sys.argv) < 2:
        print(f"! select a region for which to prepare the dataset. options are: {', '.join(list_folders('./resources/regions/'))}\n")
        sys.exit()

    regions = sys.argv[1:]
    
    details = {
        'auth': variables.final_proj_auth,
        'code': variables.final_proj_code,
    }

    if not exists("resources/regions/"):
        # extract the regions.zip file
        os.system("unzip resources/regions.zip -d resources/")

    if not exists("resources/burn_shape-ESRI-54003.gpkg"):
        # download and unzip from 'https://celray.chawanda.com/assets/downloads/burn_shape-ESRI-54003.zip'

        # we will use the following bash commands
        # tmpFile="$(mktemp finalFile.tmp.XXXXXX)"

        # wget -O "$tmpFile" "https://example.com/file" \
        # && sync "$tmpFile" \
        # && mv -f "$tmpFile" finalFile

        command = '''
        tmpFile="$(mktemp burn_shape-ESRI-54003.gpkg.tmp.XXXXXX)" \
        && wget -O "$tmpFile" "https://celray.chawanda.com/assets/downloads/burn_shape-ESRI-54003.zip" \
        && sync "$tmpFile" \
        && mv -f "$tmpFile" "resources/burn_shape-ESRI-54003.zip"
        '''
        os.system(command)

        # unzip the file replacing any if necessary
        os.system("unzip resources/burn_shape-ESRI-54003.zip -d resources/")

    for region in regions:

        report(f"\t> preparing bounding box for {region}                ")
        details['region'] = region

        if len(region.split('-')) < 2:
            print(f"the region {region} is not named correctly, the naming structure is '[continent]-[zone]'")
            quit()

        details['continent'] = region.split('-')[0]

        fn = "./resources/regions/{region}/bounding-box-EPSG-4326.txt".format(**details)
        if not exists(fn):
            print(f"!the coordinate file does not exist:\n\t> {fn}")
            quit()

        fc = [line.strip().split(',') for line in read_from(fn)]

        lat_list = [fc[1][-2], fc[0][-2], fc[0][-2], fc[1][-2]]
        lon_list = [fc[0][-1], fc[0][-1], fc[1][-1], fc[1][-1]]

        lat_list, lon_list = [float(coord) for coord in lat_list], [float(coord) for coord in lon_list]

        gdf = create_polygon_geodataframe(lat_list, lon_list)
        gdf.to_crs('{auth}:{code}'.format(**details))

        mask_fn = "./resources/regions/{region}/bounding-box-{auth}-{code}.gpkg".format(**details)
        gdf.to_file(mask_fn)

        create_path("../model-data/{region}/shapes/burn-shape-{auth}-{code}.shp".format(**details), v = False)

        if exists("./resources/continents/{continent}-{auth}-{code}.gpkg".format(**details)):
            clip_features(
                mask_fn,
                "./resources/continents/{continent}-{auth}-{code}.gpkg".format(**details),
                "./resources/regions/{region}/land_mass-{auth}-{code}.gpkg".format(**details),
            )
        else:
            clip_features(
                mask_fn,
                "./resources/CoSWAT-GM-world-land-masses-{auth}-{code}.gpkg".format(**details),
                "./resources/regions/{region}/land_mass-{auth}-{code}.gpkg".format(**details),
            )
        clip_features("./resources/regions/{region}/land_mass-{auth}-{code}.gpkg".format(**details), "resources/burn_shape-{auth}-{code}.gpkg".format(**details), "../model-data/{region}/shapes/burn-shape-{auth}-{code}.shp".format(**details))

    print()
    print()





