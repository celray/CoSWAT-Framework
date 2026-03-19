#!/bin/python3

'''
this script maps channel outputs from the COmmunity SWAT+ Model
(CoSWAT-Global) simulations. It creates:
  1. A GeoPackage with river geometries joined to annual average channel data
  2. Per-region SQLite databases with channel timeseries for web lookup,
     one database per timestep: _aa, _yr, _mon, _day

Author  : Celray James CHAWANDA
Date    : 18/03/2026

Contact : celray@chawanda.com
          celray.chawanda.com

Licence : MIT 2026
GitHub  : github.com/celray
'''

import os
import sys
import sqlite3
from ccfx import *
from coswatFX import *
from coswatFX import resolveRegions
import argparse

ignore_warnings()

# change working directory
me = os.path.realpath(__file__)
os.chdir(os.path.dirname(me))

import datavariables as variables

timesteps = ['aa', 'yr', 'mon', 'day']

timestep_aliases = {
    'aa':       'aa',   'annual_average': 'aa', 'avg': 'aa',
    'yr':       'yr',   'year': 'yr',   'yearly': 'yr',  'annual': 'yr',
    'mon':      'mon',  'month': 'mon', 'monthly': 'mon', 'mn': 'mon',
    'day':      'day',  'daily': 'day', 'dy': 'day',
}

def resolve_timesteps(raw):
    '''resolve user-provided timestep aliases to canonical names'''
    resolved = []
    for ts in raw:
        canonical = timestep_aliases.get(ts.lower(), None)
        if canonical is None:
            print(f'\t! unknown timestep "{ts}", available: {", ".join(sorted(set(timestep_aliases.keys())))}')
            sys.exit(1)
        if canonical not in resolved:
            resolved.append(canonical)
    return resolved


def make_channel_gpkg(region, version, map_columns, map_log, subDir=None):
    '''join rivs1.shp with channel_sd_aa.txt for a static spatial layer'''

    if subDir is not None:
        projBase    = f'../model-setup/CoSWATv{version}/{region}/{subDir}'
        simBase     = f'../simulations/CoSWATv{version}/{region}/{subDir}'
        label       = f'{region}/{subDir}'
    else:
        projBase    = f'../model-setup/CoSWATv{version}/{region}'
        simBase     = f'../simulations/CoSWATv{version}/{region}'
        label       = region

    rivs_fn         = f'{projBase}/Watershed/Shapes/rivs1.shp'
    channel_aa_fn   = f'{simBase}/channel_sd_aa.txt'

    if not (exists(rivs_fn) and exists(channel_aa_fn)):
        write_to(map_log, f'{datetime.datetime.now()} - ! cannot map channel results from {label}', mode='a')
        print(f'\t! cannot map channel results from {label}')
        return None

    print(f'\t> mapping channels for {label}')

    rivs_gpd                = geopandas.read_file(rivs_fn, columns=['Channel', 'geometry'])
    rivs_gpd['region']      = region
    if subDir is not None:
        rivs_gpd['subregion'] = subDir

    useCols     = ['gis_id', 'jday'] + map_columns
    ch_pd       = pandas.read_csv(channel_aa_fn, skiprows=1, sep=r'\s+', engine='c', usecols=lambda c: c in useCols, low_memory=False)
    ch_pd       = ch_pd[ch_pd['jday'] != 'mm'].drop(columns='jday')

    ch_pd['gis_id']         = pandas.to_numeric(ch_pd['gis_id'], errors='coerce')
    rivs_gpd['Channel']     = pandas.to_numeric(rivs_gpd['Channel'], errors='coerce')

    numCols = [c for c in map_columns if c in ch_pd.columns]
    ch_pd[numCols] = ch_pd[numCols].apply(pandas.to_numeric, errors='coerce')

    merged_pd   = pandas.merge(rivs_gpd, ch_pd, how='inner', left_on='Channel', right_on='gis_id')
    maps_gpd    = geopandas.GeoDataFrame(merged_pd, geometry='geometry', crs=rivs_gpd.crs)

    if len(maps_gpd.index) == 0:
        print(f'\t! no matching channel data for {label}')
        return None

    fn = f'{simBase}/evaluation/Shape/channel_map_vars.gpkg'
    create_path(fn)
    delete_file(fn, v=False)
    maps_gpd.to_file(fn)

    return maps_gpd


def build_date_column(ch_pd, timestep):
    '''build a date/period string column appropriate for the timestep'''
    if timestep == 'aa':
        ch_pd['date'] = 'aa'
        return ch_pd

    ch_pd['yr']  = pandas.to_numeric(ch_pd['yr'], errors='coerce')
    ch_pd['mon'] = pandas.to_numeric(ch_pd['mon'], errors='coerce')
    ch_pd['day'] = pandas.to_numeric(ch_pd['day'], errors='coerce')
    ch_pd = ch_pd.dropna(subset=['yr'])

    if timestep == 'yr':
        ch_pd['date'] = ch_pd['yr'].astype(int).astype(str)
        return ch_pd

    if timestep == 'mon':
        ch_pd['date'] = ch_pd['yr'].astype(int).astype(str) + '-' + ch_pd['mon'].astype(int).apply(lambda m: f'{m:02d}')
        return ch_pd

    # day
    ch_pd['date'] = pandas.to_datetime(
        ch_pd[['yr', 'mon', 'day']].rename(columns={'yr': 'year', 'mon': 'month', 'day': 'day'}),
        errors='coerce'
    ).dt.strftime('%Y-%m-%d')

    return ch_pd


def build_channel_ts(region, version, ts_columns, map_log, timestep, subDir=None):
    '''read channel_sd_{timestep}.txt and return a dataframe for SQLite ingestion'''

    if subDir is not None:
        simBase     = f'../simulations/CoSWATv{version}/{region}/{subDir}'
        label       = f'{region}/{subDir}'
    else:
        simBase     = f'../simulations/CoSWATv{version}/{region}'
        label       = region

    channel_fn = f'{simBase}/channel_sd_{timestep}.txt'

    if not exists(channel_fn):
        write_to(map_log, f'{datetime.datetime.now()} - ! no channel_sd_{timestep}.txt for {label}', mode='a')
        print(f'\t! no channel_sd_{timestep}.txt for {label}')
        return None

    print(f'\t> reading channel {timestep} timeseries for {label}')

    dateCols    = ['jday', 'mon', 'day', 'yr']
    useCols     = ['gis_id'] + dateCols + ts_columns
    ch_pd       = pandas.read_csv(channel_fn, skiprows=1, sep=r'\s+', engine='c', usecols=lambda c: c in useCols, low_memory=False)
    ch_pd       = ch_pd[ch_pd['jday'] != 'mm']

    ch_pd['gis_id'] = pandas.to_numeric(ch_pd['gis_id'], errors='coerce')
    ch_pd = build_date_column(ch_pd, timestep)

    numCols = [c for c in ts_columns if c in ch_pd.columns]
    ch_pd[numCols] = ch_pd[numCols].apply(pandas.to_numeric, errors='coerce')

    keepCols = ['gis_id', 'date'] + numCols
    if subDir is not None:
        ch_pd['subregion'] = subDir
        keepCols.insert(1, 'subregion')

    ch_pd = ch_pd[keepCols].dropna(subset=['gis_id', 'date'])
    ch_pd['gis_id'] = ch_pd['gis_id'].astype(int)

    return ch_pd


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="a terminal script for mapping channel outputs from the coswat models.")

    parser.add_argument("r", help="the name of the region to map. If not specified, all regions will be processed.", nargs='*', default=[])
    parser.add_argument("--v", help="the version of the model setup to use.", nargs='?', default=None)
    parser.add_argument("--ts", "-ts", help="timesteps to process (default: all). options: aa/avg, yr/year/annual, mon/month/mn, day/daily", nargs='*', default=None)

    args = parser.parse_args()

    if args.v is None: version_ = variables.version
    else: version_ = args.v

    if len(args.r) > 0:
        regions = resolveRegions(args.r)
        if len(regions) == 1 and regions[0] == 'all':
            regions = list_folders(f"../simulations/CoSWATv{version_}/")
    else: regions = list_folders(f"../simulations/CoSWATv{version_}/")

    if not exists(f"../simulations/CoSWATv{version_}"):
        print(f'\t! the version, CoSWATv{version_}, does not exist, the following versions are available:')
        for v in list_folders('../simulations/'):
            if v.startswith('CoSWATv'):
                print(f'\t\t- {v}')
        print(f'\t> please specify a valid version using the --v argument')
        sys.exit(1)

    if args.ts is None: requested_timesteps = timesteps[:]
    else: requested_timesteps = resolve_timesteps(args.ts)

    # columns for the static GeoPackage (annual averages)
    map_columns_    = [
        "flo_out", "sed_out", "orgn_out", "sedp_out", "no3_out",
        "solp_out", "chla_out", "dox_out", "water_temp",
    ]

    # columns for timeseries SQLite
    ts_columns_     = [
        "flo_in", "flo_out", "sed_in", "sed_out",
        "orgn_in", "orgn_out", "sedp_in", "sedp_out",
        "no3_in", "no3_out", "solp_in", "solp_out",
        "water_temp",
    ]

    out_channel_gpkg_fn     = f'../model-outputs/version-{version_}/maps/shapefiles/channel-data.gpkg'
    out_ts_dir              = f'../model-outputs/version-{version_}/maps/tsDatabases'

    map_log_ = write_to(f'../model-outputs/version-{version_}/maps/channel-map.log', '', mode='o')

    import json as jsonmod

    # build jobs list (region, subDir)
    jobs = []
    for region_ in regions:
        schemaFn = f'../model-setup/CoSWATv{version_}/{region_}/schema.json'
        if exists(schemaFn):
            with open(schemaFn, 'r') as f:
                schemaData = jsonmod.load(f)
            for subDir in schemaData['subregions']:
                jobs.append([region_, subDir])
        else:
            jobs.append([region_, None])

    # --- Step 1: Build static GeoPackage (annual averages) ---
    if 'aa' in requested_timesteps:
        print('\n\t--- mapping channel annual averages ---')
        allGpkgResults = []
        for region_, subDir_ in jobs:
            result = make_channel_gpkg(region_, version_, map_columns_, map_log_, subDir_)
            if result is not None:
                allGpkgResults.append(result)

        if allGpkgResults:
            cumulative = geopandas.GeoDataFrame(
                pandas.concat(allGpkgResults, ignore_index=True),
                geometry='geometry', crs=allGpkgResults[0].crs
            )
            create_path(out_channel_gpkg_fn)
            delete_file(out_channel_gpkg_fn, v=False)
            cumulative.to_file(out_channel_gpkg_fn)
            print(f'\t> saved cumulative channel map: {out_channel_gpkg_fn}')

    # --- Step 2: Build per-region SQLite timeseries databases ---
    for timestep_ in requested_timesteps:
        print(f'\n\t--- building channel {timestep_} timeseries databases ---')
        regionFrames    = {}
        hasSubregions   = {}

        for region_, subDir_ in jobs:
            ts_df = build_channel_ts(region_, version_, ts_columns_, map_log_, timestep_, subDir_)
            if ts_df is not None:
                if region_ not in regionFrames:
                    regionFrames[region_] = []
                    hasSubregions[region_] = False
                regionFrames[region_].append(ts_df)
                if subDir_ is not None:
                    hasSubregions[region_] = True

        for region_, frames in regionFrames.items():
            db_fn = f'{out_ts_dir}/{region_}_{timestep_}.sqlite'
            create_path(db_fn)
            delete_file(db_fn, v=False)

            combined    = pandas.concat(frames, ignore_index=True)
            tableName   = f'channel_sd_{timestep_}'

            print(f'\t> writing {len(combined)} rows to {region_}_{timestep_}.sqlite')
            conn = sqlite3.connect(db_fn)
            combined.to_sql(tableName, conn, if_exists='replace', index=False)

            if hasSubregions[region_]:
                conn.execute(f'CREATE INDEX idx_channel_sd ON {tableName}(gis_id, subregion, date)')
            else:
                conn.execute(f'CREATE INDEX idx_channel_sd ON {tableName}(gis_id, date)')

            conn.close()

    print('\n\t> channel mapping complete')
