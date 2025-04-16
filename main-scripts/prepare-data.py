#!/bin/python3

'''
This script coordinates data preparation for the COmmunity SWAT+ Model
(CoSWAT-Global) development. A project aimed at providing a community
contributed global SWAT+ model initiated and led by Celray James CHAWANDA.

Author  : Celray James CHAWANDA
Date    : 14/07/2022
Contact : celray@chawanda.com
Licence : MIT
GitHub  : github.com/celray
'''
from ccfx import createPath, listFolders
import sys, os


# change directory to file location
me = os.path.realpath(__file__)
os.chdir(os.path.dirname(me))


if len(sys.argv) >= 2: regions = sys.argv[1:]
else: regions = listFolders("../data-preparation/resources/regions/")
regions = [region for region in regions if not "test" in region]  # exclude global region

regions_ = ' '.join(regions)

print(regions_)

# create bounding boxes and land-mass masks used in next steps
os.system(f"make-bounding-boxes.py {regions_}")

# create dem
os.system(f"prepare-dem-aster.py {regions_}")

# create soil map based on dem
os.system(f"prepare-soils.py {regions_}")

# create landuse map based on dem
os.system(f"prepare-landuse.py {regions_}")

# create lake shapefile
os.system(f"prepare-lakes-data.py {regions_}")

# create weather data
os.system(f"prepare-weather.py {regions_}")

# get grdc stations
os.system(f"get-grdc-stations.py {regions_}")

