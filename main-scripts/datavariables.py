'''
# aster tiles are at 30.95308688535040176 m in EPSG 3395 (30.91819138974098635 in ESRI 54003) we want 2000 m
# that is 65 * 30.95308688535040176 which is 2011.950647577761144 m
history: 110, 128,
'''

import platform


# version
version                     = "0.4.5"

# general
data_resolution             = 30.91819138974098635 * 30     # 65

processes                   = 10
no_data_value               = -999

# dem variables
re_resample                 = True
remerge_dem                 = True
redownload_dem              = True

# outlets variables
channel_snap_thres          = 3500
proximity_thres             = 7000
start_index_value           = 7 
end_index_value             = 5
minimum_channel_segments    = 11 

thresholdSt                 = 150 # 866
thresholdCh                 = 150 # 866

executable_path             = "C:/SWAT/SWATPlus/SWATPlusEditor/resources/app.asar.unpacked/swat_exe/rev60.5.4_64rel.exe" if platform.system() == "Windows" else "/root/.local/share/SWATPlus/SWATPlusEditor/resources/app.asar.unpacked/static/swat_exe/rev60.5.7_64rel_linux"

continental_mass            = './resources/CoSWAT-GM-world-land-masses-{auth}-{code}.gpkg'
cutline                     = './resources/regions/{region}/land_mass-{auth}-{code}.gpkg'

final_proj_auth             = "ESRI"
final_proj_code             = 54003

aster_download_tiles_dir    = './dem-ws/aster/downloaded-tiles'
aster_remote_tiles_dir      = './non-existing-path'

aster_resampled_dir         = './dem-ws/aster/resampled'

aster_download_links        = './resources/aster-tile-links.txt'
aster_url                   = "https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N01E042_dem.tif"
aster_base_url              = 'https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003'

aster_tmp_tif               = './dem-ws/aster/global-aster.tif'
aster_final_raster          = "../model-data/{region}/raster/dem-aster-{auth}-{code}.tif"

fao_final_raster            = "../model-data/{region}/raster/soils-fao-{auth}-{code}.tif"
fao_tmp_raster              = "./soil-ws/fao/rasterised.tif"
fao_lookup_fn               = "../model-data/{region}/tables/worldSoilsLookup.csv"
fao_usersoil_fn             = "../model-data/{region}/tables/worldSoilsUsersoil.csv"

fao_soil_shape_fn           = "./resources/CoSWAT-GM-fao-soil-DSMW-{auth}-{code}.gpkg"
fao_usersoil_db             = "./resources/usersoilFAO.csv"

esa_final_raster            = "../model-data/{region}/raster/ricemap-v1-2025-{auth}-{code}.tif"
# esa_final_raster            = "../model-data/{region}/raster/landuse-esa-{year_model}-{auth}-{code}.tif"
# esa_base_url                = "https://dap.ceda.ac.uk"
# esa_base_path               = "neodc/esacci/land_cover/data/land_cover_maps/v2.0.7/ESACCI-LC-L4-LCCS-Map-300m-P1Y-{year}-v2.0.7.tif"
esa_landuse_year            = 2011

grand_and_lakes             = './resources/reservoirsAndLakes.gpkg'
grand_and_lakes_ws          = './lakes-ws/grand'
grand_final_shp             = "../model-data/{region}/shapes/lakes-grand-{auth}-{code}.shp"
grand_final_gpkg            = "../model-data/{region}/shapes/lakes-grand-{auth}-{code}.gpkg"
grand_lake_thres            = 30

grdc_final_gpkg             = "../model-data/{region}/shapes/grdc_stations-{auth}-{code}.gpkg"

# weather parameters
weather_points_all          = './weather-ws/global-points.gpkg'
weather_points_final        = './weather-ws/global-weather-points.gpkg'

weather_resolution          = 0.5      # decimal degrees was 5

prepare_weather             = True
redo_weather                = False
weather_redownload          = False

# run settings
run_period                  = '1987-1990'
# run_period                  = '1981-1990'
# historical_period           = '1981-2010'
# future_period               = '2071-2100'

# output processing
output_re_shape             = True


# weather data
available_scenarios        = ['observed',] # 'historical', 'ssp126', 'ssp370', 'ssp585']
available_models           = ['gswp3-ewembi', 'mpi-esm1-2-hr', 'ukesm1-0-ll', 'gfdl-esm4', 'ipsl-cm6a-lr', 'mri-esm2-0']


weather_pr_links_list       = {}
weather_hurs_links_list     = {}
weather_tasmin_links_list   = {}
weather_tasmax_links_list   = {}
weather_wind_links_list     = {}
weather_rlds_links_list     = {}

scenariosData = {
    'observed'  : ['gswp3-ewembi',],
    'historical': ['mpi-esm1-2-hr', 'ukesm1-0-ll', 'gfdl-esm4', 'ipsl-cm6a-lr', 'mri-esm2-0'],
    'picontrol' : ['mpi-esm1-2-hr', 'ukesm1-0-ll', 'gfdl-esm4', 'ipsl-cm6a-lr', 'mri-esm2-0'],
    'ssp126'    : ['mpi-esm1-2-hr', 'ukesm1-0-ll', 'gfdl-esm4', 'ipsl-cm6a-lr', 'mri-esm2-0'],
    'ssp370'    : ['mpi-esm1-2-hr', 'ukesm1-0-ll', 'gfdl-esm4', 'ipsl-cm6a-lr', 'mri-esm2-0'],
    'ssp585'    : ['mpi-esm1-2-hr', 'ukesm1-0-ll', 'gfdl-esm4', 'ipsl-cm6a-lr', 'mri-esm2-0'],
}

for scenario in scenariosData.keys():
    if not scenario in available_scenarios: continue
    weather_pr_links_list[scenario]         = {}
    weather_hurs_links_list[scenario]       = {}
    weather_tasmin_links_list[scenario]     = {}
    weather_tasmax_links_list[scenario]     = {}
    weather_wind_links_list[scenario]       = {}
    weather_rlds_links_list[scenario]       = {}
    for model in scenariosData[scenario]:
        if not model in available_models: continue
        weather_pr_links_list[scenario][model]         = f'./resources/weather-lists/{scenario}/{model}/pr.txt'
        weather_hurs_links_list[scenario][model]       = f'./resources/weather-lists/{scenario}/{model}/hurs.txt'
        weather_tasmin_links_list[scenario][model]     = f'./resources/weather-lists/{scenario}/{model}/tasmin.txt'
        weather_tasmax_links_list[scenario][model]     = f'./resources/weather-lists/{scenario}/{model}/tasmax.txt'
        weather_wind_links_list[scenario][model]       = f'./resources/weather-lists/{scenario}/{model}/sfcwind.txt'
        weather_rlds_links_list[scenario][model]       = f'./resources/weather-lists/{scenario}/{model}/rlds.txt'
