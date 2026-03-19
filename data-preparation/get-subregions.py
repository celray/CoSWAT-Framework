#!/bin/python3

'''
This script copies subregion data (masks and routing points) to the model-data
directory if available for the specified region(s).

Author  : Celray James CHAWANDA
Contact : celray@chawanda.com
Licence : MIT
'''

import sys, os
from cjfx import list_folders, exists, copy_file, create_path, ignore_warnings

ignore_warnings()

me = os.path.realpath(__file__)
os.chdir(os.path.dirname(me))

if __name__ == '__main__':

    print('\n# checking for subregion data')

    if len(sys.argv) < 2:
        print(f"! select a region for which to prepare the dataset. options are: {', '.join(list_folders('./resources/regions/'))}\n")
        sys.exit()

    regions = sys.argv[1:]

    for region in regions:
        subregionsFn = f"./resources/regions/{region}/subregions.gpkg"
        destFn       = f"../model-data/{region}/shapes/subregions.gpkg"

        if exists(subregionsFn):
            create_path(destFn, v=False)
            copy_file(subregionsFn, destFn)
            print(f"\t> copied subregions data for {region}")

    print()
