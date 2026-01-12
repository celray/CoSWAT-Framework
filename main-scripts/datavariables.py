'''
this is the control file. the model configuration is set here
'''

import platform


# version
version                     = "1.2.0"

# general
data_resolution             = 500
processes                   = 64
taudemProcesses             = 64
no_data_value               = -999

# dem variables
re_resample                 = False
redownload_dem              = False

# outlets variables
channel_snap_thres          = 3500
proximity_thres             = 7000
start_index_value           = 7 
end_index_value             = 5
minimum_channel_segments    = 11 

thresholdStArea             = 150 # km2
thresholdChArea             = 150 # km2
floodPlainDemInvThresArea   = 150 # km2

thresholdSt                 = int((thresholdStArea * 1000000) / (data_resolution**2)) # cells (calculated automatically)
thresholdCh                 = int((thresholdChArea * 1000000) / (data_resolution**2)) # cells (calculated automatically)
floodPlainDemInvThres       = int((floodPlainDemInvThresArea * 1000000) / (data_resolution**2)) # cells (calculated automatically)

burnInDepth                 = 1000 # m

# objects
run_flood_plains            = True
prepareDemTopo              = False

executable_path             =  '/CoSWAT-Global-Model/data-preparation/resources/rev60.5.7_64rel_linux' #'/CoSWAT-Global-Model/data-preparation/resources/swatplus-61.0.1-lin-x86_64'  #"/CoSWAT-Global-Model/data-preparation/resources/rev60.5.7_64rel_linux"

continental_mass            = './resources/CoSWAT-GM-world-land-masses-{auth}-{code}.gpkg'
cutline                     = './resources/regions/{region}/land_mass-{auth}-{code}.gpkg'

final_proj_auth             = "ESRI"
final_proj_code             = 54003

aster_download_tiles_dir    = './dem-ws/aster/downloaded-tiles'
aster_remote_tiles_dir      = './non-existing-path'

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

esa_final_raster            = "../model-data/{region}/raster/landuse-esa-{year_model}-{auth}-{code}.tif"
esa_base_url                = "https://dap.ceda.ac.uk"
esa_base_path               = "neodc/esacci/land_cover/data/land_cover_maps/v2.0.7/ESACCI-LC-L4-LCCS-Map-300m-P1Y-{year}-v2.0.7.tif"
esa_landuse_year            = 2007


# lakes & reservoirs
include_reservoirs          = True
hydro_lakes_path            = "./resources/hydro-lakes/HydroLAKES_v10.shp"
grand_res_path              = "./resources/hydro-lakes/GRanD_reservoirs_v1_3.shp"
globathy_path               = "./resources/GLOBathy/GLOBathy_hAV_relationships.nc"

new_res_methods             = False   

grand_final_shp             = "../model-data/{region}/shapes/lakes-grand-{auth}-{code}.shp"
grand_final_gpkg            = "../model-data/{region}/shapes/lakes-grand-{auth}-{code}.gpkg"
grand_lake_final_shp        = "../model-setup/CoSWATv{version}/{region}/Watershed/Shapes/lakes-grand-{auth}-{code}.shp"
resolved_snaps              = "../model-setup/CoSWATv{version}/{region}/Watershed/Shapes/resolved-lakes-grand-snap-{auth}-{code}.shp"
grand_lake_thres            = 40    # Km2
lake_buffer_thres           = 1500  # m
lakeMinGap                  = 2500  # m
lake_buffer_step            = 100   # m
simplify_geometry           = False
simplify_method             = 'VW'  # DP: Douglass Pecker / VW:Visvalingam–Whyatt / ConV: Convex Hull / ConC: COncave Hull

grdc_final_gpkg             = "../model-data/{region}/shapes/grdc_stations-{auth}-{code}.gpkg"

# weather parameters
weather_points_all          = './weather-ws/global-points.gpkg'
weather_resolution          = 0.5  
prepare_weather             = True
redo_weather                = True
weather_redownload          = False
use_netcdf                  = False

# run settings
run_period                  = '1980-2024'
historical_period           = '1980-2010'
future_period               = '2071-2100'

# output processing
individual_maps             = True      # create map pieces for each region
remerge_maps                = True      # (re)merge all maps into one file

# weather d111
available_scenarios        = ['observed', ]# 'historical', 'ssp126', 'ssp370', 'ssp585'] #'picontrol',
available_models           = ['20crv3-era5', 'gswp3-w5e5', 'gswp3-ewembi', 'mpi-esm1-2-hr', 'ukesm1-0-ll', 'gfdl-esm4', 'ipsl-cm6a-lr',] # 'mri-esm2-0']


weather_pr_links_list       = {}
weather_hurs_links_list     = {}
weather_tasmin_links_list   = {}
weather_tasmax_links_list   = {}
weather_wind_links_list     = {}
weather_rlds_links_list     = {}

scenariosData = {
    'observed'  : ['20crv3-era5',], # 'gswp3-ewembi',], # 'gswp3-w5e5'],
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
