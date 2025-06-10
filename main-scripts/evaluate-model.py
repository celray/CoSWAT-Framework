#!/bin/python3

import os
import sys
import argparse

import hydroeval
from cjfx import (create_path, distance, exists, geopandas, list_all_files,
                  list_folders, pandas, points_to_geodataframe, report, ignore_warnings,
                  resample_ts_df, write_to, delete_file)

# change working directory
me = os.path.realpath(__file__)
os.chdir(os.path.dirname(me))

ignore_warnings()

sys.path.insert(0, "../data-preparation")
import warnings

import datavariables as variables

warnings.filterwarnings('ignore')

if __name__ == "__main__":
        
    # get model setup version
    parser = argparse.ArgumentParser(description="a script for evaluating models.")

    parser.add_argument("r", help="the name of the region to run the model for. If not specified, all regions will be processed.", nargs='*', default=[])
    parser.add_argument("--v", help="the version of the model setup to use. If not specified, the datavariables value will be used.", nargs='?', default=None)

    args = parser.parse_args()
    
    # get model setup version
    if args.v is None: version = variables.version
    else: version = args.v  

    # get regions
    if len(args.r) > 0: regions = args.r
    else: regions = list_folders(f"../model-setup/CoSWATv{version}/")

    if not exists(f"../model-setup/CoSWATv{version}"):
        print(f'\t! the version, CoSWATv{version}, does not exist, the following versions are available:')
        for v in list_folders('../model-setup/'):
            if v.startswith('CoSWATv'):
                print(f'\t\t- {v}')
        print(f'\t> please specify a valid version using the --v argument')
        sys.exit(1)

    for region in regions:

        details         = {
            'auth'          : variables.final_proj_auth,
            'code'          : variables.final_proj_code,
            'region'        : region,
            'model_version' : version,
        }

        print(f'\t# evaluating {region}')

        model_dir = '../model-setup/CoSWATv{model_version}/{region}'.format(**details)


        grdc_vector_fn      = "../model-data/{region}/shapes/grdc_stations-{auth}-{code}.gpkg".format(**details)
        rivs_vector_fn      = f"{model_dir}/Watershed/Shapes/rivs1.shp"

        outlets_vector_fn   = f"{model_dir}/Watershed/Shapes/outlets_sel.shp"
        if not exists(outlets_vector_fn): outlets_vector_fn = f"{model_dir}/Watershed/Shapes/outlets.shp"

        rivs_vector_gdf     = geopandas.read_file(rivs_vector_fn)
        grdc_vector_gdf     = geopandas.read_file(grdc_vector_fn)
        outlets_vector_gdf  = geopandas.read_file(outlets_vector_fn)

        outlet_closest_channels = {}
        outlet_closest_stations = {}
        outlet_coordinates      = {}

        outlet_channel          = {}
        all_channels            = []

        print(f'\t> matching stations and outlets')
        for index, point in outlets_vector_gdf.iterrows():
            point_coordinates = (point.geometry.x, point.geometry.y)
            outlet_coordinates[point.ID] = point_coordinates
            closeness = None
            for index2, river in rivs_vector_gdf.iterrows():

                if int(river.ChannelR) == 0:
                    outlet_channel[river.Channel] = True
                else:
                    outlet_channel[river.Channel] = False

                if not river.Channel in all_channels:
                    all_channels.append(river.Channel)

                coordinates_list    = str(river['geometry']).split("(")[-1].split(")")[0].split(",")[0]
                river_coordinates   = [float(x) for x in coordinates_list.strip().split(' ')]

                distance_between_   = distance(point_coordinates, river_coordinates)
                
                if closeness is None:
                    closeness = distance_between_
                    outlet_closest_channels[point.ID] = river.Channel

                if distance_between_ < closeness:
                    outlet_closest_channels[point.ID] = river.Channel
                    closeness = distance_between_
            
            if outlet_channel[outlet_closest_channels[point.ID]]:
                del(outlet_closest_channels[point.ID])
                continue


            if not point.ID in outlet_closest_channels: continue
            closeness = None
            for index3, grdc_station in grdc_vector_gdf.iterrows():
                grdc_coordinates = (grdc_station.geometry.x, grdc_station.geometry.y)

                distance_between_ = distance(point_coordinates, grdc_coordinates)

                if closeness is None:
                    closeness = distance_between_
                    outlet_closest_stations[point.ID] = grdc_station.grdc_no

                if distance_between_ < closeness:
                    outlet_closest_stations[point.ID] = grdc_station.grdc_no
                    closeness = distance_between_
            
        # evaluate model performance
        swatplus_ts_fn = f'{model_dir}/Scenarios/Default/TxtInOut/channel_sdmorph_mon.txt'

        simulations_df = None
        if exists(swatplus_ts_fn):
            print(f'\t> reading monthly channel outputs for {region}')
            simulations_df = pandas.read_csv(swatplus_ts_fn, skiprows = 4, delim_whitespace = True, index_col = False, names = ["jday", "mon", "day", "yr", "unit", "gis_id", "name", "flo_in", "geo_bf", "flo_out", "peakr", "sed_in", "sed_out", "washld", "bedld", "dep", "deg_btm", "deg_bank", "hc_sed", "width", "depth", "slope", "deg_btm_m", "deg_bank_m", "hc_len", "flo_in_mm", "aqu_in_mm", "flo_out_mm", "other1"])
        else:
            print('run the model with monthly output automaticaly, mu-hahahahaha!')
            continue
            # quit()

        print('\t> adding dates and removing unnecessary data')
        simulations_df['date'] = ''
        simulations_df = simulations_df[['date', 'yr', 'mon', 'day', 'flo_out', 'unit']]

        for index, day in simulations_df.iterrows():
            simulations_df.loc[index, 'date'] = f'{day.yr}-{day.mon}-{day.day}'


        perfornance_data = []

        lookup_string = "grdc_id,channel\n"
        for id in outlet_closest_channels:
            lookup_string += f"{outlet_closest_stations[id]},{outlet_closest_channels[id]},"

            report(f'\t> processing channel {outlet_closest_channels[id]}                                                   ')
            # read grdc and swat_output
            grdc_ts_fn = f"../model-data/{region}/observations/{outlet_closest_stations[id]}.csv"
            if exists(grdc_ts_fn):
                lookup_string += f"done\n"

                observations_data = pandas.read_csv(grdc_ts_fn, skiprows = 1, na_values = '', names = ["date", "observed", 'other'], index_col=False)

                observations_data['date'] = pandas.to_datetime(observations_data['date'])
                
                simulation_data = simulations_df[simulations_df['unit'] == int(outlet_closest_channels[id])]

                simulation_data = resample_ts_df(simulation_data, 'date')
                
                final_dataset = (simulation_data.merge(observations_data, on = 'date'))

                nse     = hydroeval.evaluator(hydroeval.nse, final_dataset['flo_out'].tolist(), final_dataset['observed'].tolist())[0]
                pbias   = hydroeval.evaluator(hydroeval.pbias, final_dataset['flo_out'].tolist(), final_dataset['observed'].tolist())[0]

                perfornance_data.append([outlet_closest_stations[id], outlet_closest_channels[id], nse, pbias, outlet_coordinates[id][0], outlet_coordinates[id][1]])

                try: del plt
                except: pass
                try: del matplotlib
                except: pass
                try: del make_plot
                except: pass
                import matplotlib.pyplot as plt

                import matplotlib
                matplotlib.use("Agg")

                from cjfx import make_plot

                img_pth = f'{model_dir}/Evaluation/Figures/channel_{outlet_closest_channels[id]}-grdc_{outlet_closest_stations[id]}.png'

                delete_file(img_pth, v = False)
                create_path(img_pth, v = False)

                try:
                    fig, axs = plt.subplots(figsize=(12, 5))
                    plot__ = make_plot(
                        final_dataset, 'date', ['flo_out', 'observed'], 'Discharge (m3/s)', img_pth,
                        f"NSE = {round(nse, 4)}, PBIAS = {round(pbias, 4)}",
                        y1_labels=[f'Simulated (Channel {outlet_closest_channels[id]})', f'Observed (GRDC NO: {outlet_closest_stations[id]})'], legend=True
                        
                    )

                    del plot__
                except:
                    pass
                    # final_dataset["flo_out"].plot.line(ax=axs)
                    # final_dataset["observed"].plot.line(ax=axs)
                    # axs.set_ylabel("Discharge (m3/s)")
                    # axs.set_xlabel(f"NSE = {round(nse, 4)}, PBIAS = {round(pbias, 4)}")


                    # fig.legend([f'Simulated (Channel {outlet_closest_channels[id]})', f'Observed (GRDC NO: {outlet_closest_stations[id]})'])
                    # fig.savefig(img_pth)

                report(f'\t> saving fig channel_{outlet_closest_channels[id]}-grdc_{outlet_closest_stations[id]}.png      ')

            else:
                lookup_string += f"nan\n"

        print('\n\t> saving channels lookup    ')
        write_to(f'{model_dir}/Evaluation/Text/grdc_observations_lookup.csv', lookup_string)

        shape_out_fn = f'{model_dir}/Evaluation/Shape/indices.gpkg'
        create_path(shape_out_fn, v = False)
        print('\t> saving shapefiles    \n')

        if len(perfornance_data) > 0:
            indices_all = points_to_geodataframe(perfornance_data, out_shape=shape_out_fn, columns=["grdc_no", "channel", 'nse', 'pbias', 'latitude', 'longitude'], auth = details['auth'], code = details['code'])
            indices_all["graph_field"] = ""

            for index, row in indices_all.iterrows():
                indices_all.loc[index, 'graph_field'] = f"region_{region}-channel_{row.channel}-grdc_{row.grdc_no}.png"
            
            indices_all = indices_all.to_crs('EPSG:4326')
            indices_all.to_file(f'{model_dir}/Evaluation/Shape/indices.geojson')

        if len(rivs_vector_gdf.index) > 1:
            rivers      = rivs_vector_gdf.to_file(f'{model_dir}/Evaluation/Shape/channels.gpkg')



        from cjfx import alert
        alert(f'model evaluated for {region}', 'Model Evaluation Complete')
