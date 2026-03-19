#!/bin/python3

import sys, os
from cjfx import *
import argparse

ignore_warnings()

# change working directory
me = os.path.realpath(__file__)
os.chdir(os.path.dirname(me))

import datavariables as variables

def confirm_deletion(region, version, no_confirm=False):
    """Ask for user confirmation before deleting a model project."""
    if no_confirm:
        return True
    
    print(f"\n⚠️ WARNING: You are about to delete the model project for region '{region}' (version {version})")
    
    while True:
        response = input(f"\t> are you sure you want to delete '{region}'? (yes/no): ").lower().strip()
        if response in ['yes', 'y']:
            return True
        elif response in ['no', 'n']:
            return False
        else:
            print("\t please enter 'yes' or 'no'")

if __name__ == '__main__':

    # create argument parser
    parser = argparse.ArgumentParser(description="a script to delete SWAT+ project(s) for given region(s)")

    parser.add_argument("r", help="the name of the region(s) to delete the model for. If not specified, all regions will be listed for selection.", nargs='*', default=[])
    parser.add_argument("--v", help="the version of the model setup to delete. If not specified, the datavariables value will be used.", nargs='?', default=None)
    parser.add_argument("--no-confirm", help="skip confirmation prompts and delete without asking", action='store_true')

    args = parser.parse_args()

    print('\n# deleting SWAT+ project(s)')
    version = variables.version

    if args.v:
        version = args.v

    setup_dir = f'../model-setup/CoSWATv{version}'
    
    # Check if setup directory exists
    if not exists(setup_dir):
        print(f"❌ Model setup directory not found: {setup_dir}")
        print("No models to delete.")
        sys.exit(1)

    # Get available regions from the setup directory
    available_regions = [d for d in list_folders(setup_dir) if exists(f'{setup_dir}/{d}/{d}.qgs')]
    
    if len(available_regions) == 0:
        print(f"❌ No model projects found in: {setup_dir}")
        sys.exit(1)

    if len(args.r) > 0: 
        regions = args.r
        if len(regions) == 1 and regions[0] == 'all': 
            regions = available_regions
        else:
            # Validate that specified regions exist
            invalid_regions = [r for r in regions if r not in available_regions]
            if invalid_regions:
                print(f"❌ The following regions were not found: {', '.join(invalid_regions)}")
                print(f"Available regions: {', '.join(available_regions)}")
                sys.exit(1)
    else: 
        print(f"\nAvailable model projects in CoSWATv{version}:")
        for i, region in enumerate(available_regions, 1):
            print(f"  {i}. {region}")
        print(f"\nTo delete specific regions, run:")
        print(f"  python delete-model.py <region1> <region2> ...")
        print(f"  python delete-model.py all  # to delete all regions")
        sys.exit(0)

    deleted_count = 0
    skipped_count = 0

    for region in regions:
        region_dir = f'{setup_dir}/{region}'
        
        if not exists(region_dir):
            print(f"⚠️  Region '{region}' not found, skipping...")
            skipped_count += 1
            continue

        if not exists(f'{region_dir}/{region}.qgs'):
            print(f"⚠️  No valid project found for region '{region}', skipping...")
            skipped_count += 1
            continue

        # Ask for confirmation
        if confirm_deletion(region, version, args.no_confirm):
            try:
                report(f"\t> deleting {region} project                \n")
                delete_path(region_dir)
                print(f"\t> ✅ Successfully deleted project for region '{region}'")
                deleted_count += 1
            except Exception as e:
                print(f"\t> ❌ Failed to delete project for region '{region}': {str(e)}")
                skipped_count += 1
        else:
            print(f"\t> 🚫 Deletion cancelled for region '{region}'")
            skipped_count += 1

    print(f"\n📊 Summary:")
    print(f"  - Deleted: {deleted_count} project(s)")
    print(f"  - Skipped: {skipped_count} project(s)")
    
    if deleted_count > 0:
        print(f"✅ operation completed. {deleted_count} model project(s) have been deleted.")
    else:
        print(f"\n💡no projects were deleted.")

print()
