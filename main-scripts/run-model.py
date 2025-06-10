#!/bin/python3

'''
This script runs the COmmunity SWAT+ Model
(CoSWAT-Global) one by one.

Author  : Celray James CHAWANDA
Date    : 14/07/2022
Contact : celray@chawanda.com
Licence : MIT
GitHub  : github.com/celray
'''

import os, sys, platform, argparse
from cjfx import list_all_files, exists, write_to, ignore_warnings, list_folders
from coswatFX import runSWATPlus

ignore_warnings()

# change working directory
me = os.path.realpath(__file__)
os.chdir(os.path.dirname(me))

import datavariables as variables
from resources.print_file import print_prt

if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="a script for running the model setup and delineation.")

    parser.add_argument("r", help="the name of the region to run the model for. If not specified, all regions will be processed.", nargs='*', default=[])
    parser.add_argument("--v", help="the version of the model setup to use. If not specified, the datavariables value will be used.", nargs='?', default=None)
    parser.add_argument("--y", help="the years to run the model for. If not specified, the datavariables value will be used.", nargs='?', default=None)

    args = parser.parse_args()

    # get years
    if args.y is None: years = variables.run_period
    else: years = args.y
    yr_fro, yr_to = years.split("-")

    # get model setup version
    if args.v is None: version = variables.version
    else: version = args.v  

    if not exists(f"../model-setup/CoSWATv{version}"):
        print(f'\t! the version, CoSWATv{version}, does not exist, the following versions are available:')
        for v in list_folders('../model-setup/'):
            if v.startswith('CoSWATv'):
                print(f'\t\t- {v}')
        print(f'\t> please specify a valid version using the --v argument')
        sys.exit(1)

    # get regions
    if len(args.r) > 0: regions = args.r
    else: regions = list_folders(f"../model-setup/CoSWATv{version}/")

    for region in regions:
        txtDir = f"{os.path.dirname(me)}/../model-setup/CoSWATv{version}/{region}/Scenarios/Default/TxtInOut"

        write_to(f"{txtDir}/time.sim", f"time.sim: written by CoSWAT Data Writer\nday_start  yrc_start   day_end   yrc_end      step  \n       0      {yr_fro}         0      {yr_to}         0  ")
        write_to(f"{txtDir}/print.prt", print_prt)
        if exists(f"{txtDir}/file.cio"):
            end_section = '\n' if platform.system() == 'Windows' else ''
            print(f"\n\n# running SWAT+ for {region}{end_section}")
            runSWATPlus(txtDir, executable_path = variables.executable_path, modelName = region)
            if platform.system() == "Windows": print()
        else:
            print(f"\n\n! cannot run SWAT+ for {region}")
    


        

