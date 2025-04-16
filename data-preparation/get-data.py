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

# imports
import os, sys
from cjfx import list_folders, ignore_warnings

ignore_warnings()

import datavariables as variables

# functions
def get_python_exe() -> str:
    return "python" if os.name == "nt" else "python3"

# change directory to file location
me = os.path.realpath(__file__)
os.chdir(os.path.dirname(me))

if not os.name == "nt":
    pass
    # os.system("clear")

if len(sys.argv) >= 2: regions = sys.argv[1:]
else: regions = list_folders("./resources/regions/")

regions_ = ' '.join(regions)

# create bounding boxes and land-mass masks used in next steps
os.system(f"{get_python_exe()} make-bounding-boxes.py {regions_}")

# create dem
os.system(f"{get_python_exe()} prepare-dem-aster.py {regions_}")

# create soil map based on dem
os.system(f"{get_python_exe()} prepare-soils.py {regions_}")

# create landuse map based on dem
os.system(f"{get_python_exe()} prepare-landuse.py {regions_}")

# create lake shapefile
os.system(f"{get_python_exe()} prepare-lakes-data.py {regions_}")

# create weather data
os.system(f"{get_python_exe()} prepare-weather.py {regions_}")

# get grdc stations
os.system(f"{get_python_exe()} get-grdc-stations.py {regions_}")


from cjfx import alert
alert(f'Finished getting data for {regions_}', 'Data Preparation Complete')
print()
