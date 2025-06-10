#!/bin/python3

'''
this script coordinates the setup of the COmmunity SWAT+ Model
(CoSWAT-Global) development. A project aimed at providing a community
contributed global SWAT+ model initiated and led by Celray James CHAWANDA.

Author  : Celray James CHAWANDA
Date    : 23/07/2022

Contact : celray@chawanda.com
          celray.chawanda.com

Licence : MIT 2022
GitHub  : github.com/celray
'''

import os
import sys
from cjfx import list_folders, ignore_warnings, alert
import multiprocessing
import argparse

ignore_warnings()

# change working directory
me = os.path.realpath(__file__)
os.chdir(os.path.dirname(me))

import datavariables as variables

def set_up_model(region_, version_, get_data_, period_):
    '''
    This function coordinates the setup of the COmmunity SWAT+ Model
    '''
    alert(f'Setting up {region_}', f'Setting up {region_}')
    if get_data_ == 'y': os.system(f'get-data.py {region_}')

    os.system(f'init-model.py {region_} --v {version_}')
    os.system(f'run-qswatplus.py {region_} --v {version_}')
    os.system(f'edit-model.py {region_} --v {version_}')

    os.system(f'run-model.py {region_} --v {version_} --y {period_}')
    os.system(f'evaluate-model.py {region_} --v {version_}')

args = sys.argv

parser = argparse.ArgumentParser(description="a script to set up the CoSWAT-Global model for a given region")
parser.add_argument("r", help="the name of the region to set up the model for. If not specified, all regions will be processed.", nargs='*', default=[])
parser.add_argument("--v", help="the version of the model setup to use. If not specified, the datavariables value will be used.", nargs='?', default=variables.version)
parser.add_argument("--d", help="whether to prepare data for regions. If not specified, the data will be prepared.", nargs='?', default='y')

args = parser.parse_args()

# get regions
if len(args.r) > 0: 
    regions = args.r
    if len(regions) == 1 and regions[0] == 'all': 
        regions = list_folders("../data-preparation/resources/regions/")
else:
    regions = list_folders("../data-preparation/resources/regions/")

# get model setup version
version = args.v if args.v else variables.version

# get data preparation option
get_data = args.d if args.d else 'y'

# get number of processes to use
processes = variables.processes

if __name__ == "__main__":
    
    pool = multiprocessing.Pool(int(processes))

    jobs = []    

    counter = 0
    for region in regions:
        counter += 1
        # set data preparation options in ./data-preparation/resources/datavariables.py
        jobs.append([region, version, get_data, variables.run_period])
    
    result = pool.starmap_async(set_up_model, jobs)
    result.get()

    pool.close()

    os.chdir(os.path.dirname(me))
    os.system(f'map-outputs.py --v {version}')

alert('all tasks complete', 'Global Model Setup Complete')
