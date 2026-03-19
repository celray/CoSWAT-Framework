#!/bin/python3

import sys, os
from ccfx import *
from coswatFX import *
import argparse

ignore_warnings()

# change working directory
me = os.path.realpath(__file__)
os.chdir(os.path.dirname(me))

import datavariables as variables

if __name__ == '__main__':

    # create argument parser
    parser = argparse.ArgumentParser(description="a script to mark SWAT+ project(s) for given region(s) as 'has error or not")

    parser.add_argument("r", help="the name of the region(s) to mark the model. script will quit", nargs='*', default=[])
    parser.add_argument("--v", help="the version of the model setup to mark. If not specified, the datavariables value will be used.", nargs='?', default=None)
    parser.add_argument("--error", help="mark the project as having an error, if not specified, the mark is cleared", action='store_true')

    args = parser.parse_args()

    print('\n# marking SWAT+ project(s)')
    version = variables.version

    if args.v:
        version = args.v

    setup_dir = f'../model-setup/CoSWATv{version}'
    
    # Check if setup directory exists
    if not exists(setup_dir):
        print(f"model setup directory not found: {setup_dir}")
        print("no models to mark.")
        sys.exit(1)

    # Get available regions from the setup directory
    available_regions = [d for d in list_folders(setup_dir) if exists(f'{setup_dir}/{d}/{d}.qgs')]
    
    if len(available_regions) == 0:
        print(f"no model projects found in: {setup_dir}")
        sys.exit(1)

    if len(args.r) > 0: 
        regions = args.r
        if len(regions) == 1 and regions[0] == 'all': 
            regions = available_regions
        else:
            # Validate that specified regions exist
            invalid_regions = [r for r in regions if r not in available_regions]
            if invalid_regions:
                print(f"the following regions were not found: {', '.join(invalid_regions)}")
                print(f"available regions: {', '.join(available_regions)}")
                sys.exit(1)
    else: 
        print(f"\navailable model projects in CoSWATv{version}:")
        for i, region in enumerate(available_regions, 1):
            print(f"  {i}. {region}")
        print(f"\nTo mark specific regions, run:")
        print(f"  python mark-error.py <region1> <region2> --error  # to mark as having error")
        print(f"  python mark-error.py <region1> <region2>           # to clear error mark")
        print(f"  python mark-error.py all --error # to mark all regions")
        sys.exit(0)

    deleted_count = 0
    skipped_count = 0

    for region in regions:
        region_dir = f'{setup_dir}/{region}'
        
        if not exists(region_dir):
            print(f"region '{region}' not found, skipping...")
            skipped_count += 1
            continue

        if not exists(f'{region_dir}/{region}.qgs'):
            print(f"no valid project found for region '{region}', skipping...")
            skipped_count += 1
            continue

        error_file = f'{region_dir}/.has_error'

        if args.error:
            # Mark the project as having an error
            try:
                with open(error_file, 'w') as f:
                    f.write('error')
                print(f"\t> successfully marked project for region '{region}' as having an error")
                deleted_count += 1
            except Exception as e:
                print(f"\t> ❌ Failed to mark project for region '{region}': {str(e)}")
                skipped_count += 1
        else:
            # Clear the error mark
            if exists(error_file):
                try:
                    os.remove(error_file)
                    print(f"\t> successfully cleared error mark for region '{region}'")
                    deleted_count += 1
                except Exception as e:
                    print(f"\t> ❌ Failed to clear error mark for region '{region}': {str(e)}")
                    skipped_count += 1
            else:
                print(f"\t> no error mark found for region '{region}', skipping...")
                skipped_count += 1

    print(f"\n📊 Summary:")
    print(f"  - Marked: {deleted_count} project(s)")
    print(f"  - Skipped: {skipped_count} project(s)")
    
    if deleted_count > 0:
        print(f"✅ operation completed. {deleted_count} model project(s) have been marked.")
    else:
        print(f"\n💡no projects were marked.")

print()
