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

    os.system(f'init-model.py {version_} {region_}')
    os.system(f'run-qswatplus.py {version_} {region_}')
    os.system(f'edit-model.py {version_} {region_}')

    os.system(f'run-model.py {version_} {period_} {region_}')
    os.system(f'evaluate-model.py {version_} {region_}')

args = sys.argv

# example set-up-model.py 0.4.0 n 10 africa-madagascar
if len(sys.argv) >= 5: regions = sys.argv[4:]
else: regions = list_folders("../data-preparation/resources/regions/")

version = args[1]
get_data = args[2] if len(sys.argv) >= 3 else 'y'

processes = args[3] if len(sys.argv) >= 4 else variables.processes

if __name__ == "__main__":
    
    pool = multiprocessing.Pool(int(processes))

    jobs = []    

    counter = 0
    for region in regions:
        counter += 1
        # prepare dataset
        # set data preparation options in ./data-preparation/resources/datavariables.py
        jobs.append([region, version, get_data, variables.run_period])

        # alert(f'Setting up {region}', f'Setting up progress {counter} of {len(regions)}')
        # set_up_model(region, version, get_data, variables.run_period)

    
    result = pool.starmap_async(set_up_model, jobs)
    result.get()

    pool.close()

    os.chdir(os.path.dirname(me))
    os.system(f'map-outputs.py {version}')


    # from cjfx import alert
    # alert('mapping outputs for all regions complete', 'Mapping Variables Complete')

    # os.system(f'python /drive/d1/github/websites/coswat/assets/scripts/get-models.py {version} yes ')
    # alert('server files created successfully', 'Server Files Creation Complete')

alert('all tasks complete', 'Global Model Setup Complete')
