#!/bin/python3

import os
from io import StringIO

from cjfx import (clip_features, create_path, exists, geopandas, list_folders, ignore_warnings,
                  pandas, read_from, resample_ts_df, show_progress, sys)

# change working directory
me = os.path.realpath(__file__)
os.chdir(os.path.dirname(me))

ignore_warnings()

import datavariables as variables

metadata    = pandas.read_excel("./resources/GRDC_Stations.xlsx")
grdc_ts_dir = "./resources/grdc_timeseries"

if not exists(f"{grdc_ts_dir}/"):
    os.system(f"unzip ./resources/grdc_timeseries.zip -d ./resources")

create_path("./resources/ws/")

if len(sys.argv) < 2:
    print(f"! select a region for which to prepare the dataset. options are: {', '.join(list_folders('./resources/regions/'))}\n")
    sys.exit()

regions = sys.argv[1:]

details = {
    'auth'      : variables.final_proj_auth,
    'code'      : variables.final_proj_code,
    'skipday'   : 36,
    'skipmon'   : 38,
}

print('# preparing grdc observations')
gdf = geopandas.GeoDataFrame(metadata, geometry=geopandas.points_from_xy(metadata.long, metadata.lat), crs = "EPSG:4326")
gdf = gdf.to_crs("{auth}:{code}".format(**details))

if not os.path.isfile("./resources/ws/grdc_tmp.gpkg"):
    gdf.to_file("./resources/ws/grdc_tmp.gpkg", driver = "GPKG", )

for region in regions:
    details['region'] = region
    final_grdc_stations_gpd = clip_features(variables.cutline.format(**details), "./resources/ws/grdc_tmp.gpkg", variables.grdc_final_gpkg.format(**details))

    print(f'\t> collecting time series for {region}')

    current = 0
    end = len(final_grdc_stations_gpd.index)
    for index, row in final_grdc_stations_gpd.iterrows():
        current +=  1
        show_progress(current, end)
        fn = f"{grdc_ts_dir}/monthly/{row['grdc_no']}_Q_Month.txt"
        file_exists = False
        skiped_lines = "skipmon"

        if exists(fn):
            file_exists = True
        else:
            fn = f"{grdc_ts_dir}/daily/{row['grdc_no']}_Q_Day.Cmd.txt"
            if exists(fn):
                file_exists = True
                skiped_lines = "skipday"

        if file_exists:
            str_data = read_from(fn, decode_codec = 'ISO-8859-1'); fstring = "";
            for line in str_data:
                fstring += line

            fc = StringIO(fstring)

            ts_df = pandas.read_csv(fc, delimiter = ';', skiprows = details[skiped_lines], na_values = '-999')
            
            if len(ts_df.index) == 0: continue

            if " Calculated" in ts_df.columns:
                ts_df[' Original'].fillna(ts_df[' Calculated'], inplace=True)


            ts_df['YYYY-MM-DD'] = pandas.to_datetime(ts_df['YYYY-MM-DD'])


            ts_m_df = resample_ts_df(ts_df, "YYYY-MM-DD")

            create_path("../model-data/{region}/observations/".format(**details), v = False)
            ts_m_df.to_csv(f"../model-data/{region}/observations/{row['grdc_no']}.csv")
    
    print()

