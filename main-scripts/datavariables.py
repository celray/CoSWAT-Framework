'''
# aster tiles are at 30.95308688535040176 m in EPSG 3395 (30.91819138974098635 in ESRI 54003) we want 2000 m
# that is 65 * 30.95308688535040176 which is 2011.950647577761144 m
history: 110, 128,
'''

import platform

# general
data_resolution             = 30.91819138974098635 * 30     # 65
processes                   = 50
no_data_value               = -999

# dem variables
re_resample                 = False
remerge_dem                 = False
redownload_dem              = False

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
esa_base_path               = "CCI/LandCover/byYear/ESACCI-LC-L4-LCCS-Map-300m-P1Y-{year}-v2.0.7.tif"
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

weather_pr_links_list       = {}
weather_hurs_links_list     = {}
weather_tasmin_links_list   = {}
weather_tasmax_links_list   = {}
weather_wind_links_list     = {}
weather_rlds_links_list     = {}

weather_pr_links_list['observed']         = './resources/weather-lists/observed/pr_gswp3-ewembi.txt' 
weather_hurs_links_list['observed']       = './resources/weather-lists/observed/rhs_gswp3-ewembi.txt' 
weather_tasmin_links_list['observed']     = './resources/weather-lists/observed/tasmin_gswp3-ewembi.txt' 
weather_tasmax_links_list['observed']     = './resources/weather-lists/observed/tasmax_gswp3-ewembi.txt' 
weather_wind_links_list['observed']       = './resources/weather-lists/observed/wind_gswp3-ewembi.txt' 
weather_rlds_links_list['observed']       = './resources/weather-lists/observed/rlds_gswp3-ewembi.txt' 

# weather_pr_links_list['historical-mpi-esm1-2-hr']       = './resources/weather-lists/historical/mpi-esm1-2-hr/pr.txt'
# weather_tasmax_links_list['historical-mpi-esm1-2-hr']   = './resources/weather-lists/historical/mpi-esm1-2-hr/tasmax.txt'
# weather_tasmin_links_list['historical-mpi-esm1-2-hr']   = './resources/weather-lists/historical/mpi-esm1-2-hr/tasmin.txt'
# weather_wind_links_list['historical-mpi-esm1-2-hr']     = './resources/weather-lists/historical/mpi-esm1-2-hr/sfcwind.txt'
# weather_rlds_links_list['historical-mpi-esm1-2-hr']     = './resources/weather-lists/historical/mpi-esm1-2-hr/rlds.txt'
# weather_hurs_links_list['historical-mpi-esm1-2-hr']     = './resources/weather-lists/historical/mpi-esm1-2-hr/hurs.txt'
														
# weather_pr_links_list['historical-ukesm1-0-ll']         = './resources/weather-lists/historical/ukesm1-0-ll/pr.txt'
# weather_tasmax_links_list['historical-ukesm1-0-ll']     = './resources/weather-lists/historical/ukesm1-0-ll/tasmax.txt'
# weather_tasmin_links_list['historical-ukesm1-0-ll']     = './resources/weather-lists/historical/ukesm1-0-ll/tasmin.txt'
# weather_wind_links_list['historical-ukesm1-0-ll']    = './resources/weather-lists/historical/ukesm1-0-ll/sfcwind.txt'
# weather_rlds_links_list['historical-ukesm1-0-ll']       = './resources/weather-lists/historical/ukesm1-0-ll/rlds.txt'
# weather_hurs_links_list['historical-ukesm1-0-ll']       = './resources/weather-lists/historical/ukesm1-0-ll/hurs.txt'
														
# weather_pr_links_list['historical-gfdl-esm4']           = './resources/weather-lists/historical/gfdl-esm4/pr.txt'
# weather_tasmax_links_list['historical-gfdl-esm4']       = './resources/weather-lists/historical/gfdl-esm4/tasmax.txt'
# weather_tasmin_links_list['historical-gfdl-esm4']       = './resources/weather-lists/historical/gfdl-esm4/tasmin.txt'
# weather_wind_links_list['historical-gfdl-esm4']      = './resources/weather-lists/historical/gfdl-esm4/sfcwind.txt'
# weather_rlds_links_list['historical-gfdl-esm4']         = './resources/weather-lists/historical/gfdl-esm4/rlds.txt'
# weather_hurs_links_list['historical-gfdl-esm4']         = './resources/weather-lists/historical/gfdl-esm4/hurs.txt'
														
# weather_pr_links_list['historical-ipsl-cm6a-lr']        = './resources/weather-lists/historical/ipsl-cm6a-lr/pr.txt'
# weather_tasmax_links_list['historical-ipsl-cm6a-lr']    = './resources/weather-lists/historical/ipsl-cm6a-lr/tasmax.txt'
# weather_tasmin_links_list['historical-ipsl-cm6a-lr']    = './resources/weather-lists/historical/ipsl-cm6a-lr/tasmin.txt'
# weather_wind_links_list['historical-ipsl-cm6a-lr']   = './resources/weather-lists/historical/ipsl-cm6a-lr/sfcwind.txt'
# weather_rlds_links_list['historical-ipsl-cm6a-lr']      = './resources/weather-lists/historical/ipsl-cm6a-lr/rlds.txt'
# weather_hurs_links_list['historical-ipsl-cm6a-lr']      = './resources/weather-lists/historical/ipsl-cm6a-lr/hurs.txt'
														
# weather_pr_links_list['historical-mri-esm2-0']          = './resources/weather-lists/historical/mri-esm2-0/pr.txt'
# weather_tasmax_links_list['historical-mri-esm2-0']      = './resources/weather-lists/historical/mri-esm2-0/tasmax.txt'
# weather_tasmin_links_list['historical-mri-esm2-0']      = './resources/weather-lists/historical/mri-esm2-0/tasmin.txt'
# weather_wind_links_list['historical-mri-esm2-0']     = './resources/weather-lists/historical/mri-esm2-0/sfcwind.txt'
# weather_rlds_links_list['historical-mri-esm2-0']        = './resources/weather-lists/historical/mri-esm2-0/rlds.txt'
# weather_hurs_links_list['historical-mri-esm2-0']        = './resources/weather-lists/historical/mri-esm2-0/hurs.txt'
														
# weather_pr_links_list['picontrol-mpi-esm1-2-hr']        = './resources/weather-lists/picontrol/mpi-esm1-2-hr/pr.txt'
# weather_tasmax_links_list['picontrol-mpi-esm1-2-hr']    = './resources/weather-lists/picontrol/mpi-esm1-2-hr/tasmax.txt'
# weather_tasmin_links_list['picontrol-mpi-esm1-2-hr']    = './resources/weather-lists/picontrol/mpi-esm1-2-hr/tasmin.txt'
# weather_wind_links_list['picontrol-mpi-esm1-2-hr']   = './resources/weather-lists/picontrol/mpi-esm1-2-hr/sfcwind.txt'
# weather_rlds_links_list['picontrol-mpi-esm1-2-hr']      = './resources/weather-lists/picontrol/mpi-esm1-2-hr/rlds.txt'
# weather_hurs_links_list['picontrol-mpi-esm1-2-hr']      = './resources/weather-lists/picontrol/mpi-esm1-2-hr/hurs.txt'
														
# weather_pr_links_list['picontrol-ukesm1-0-ll']          = './resources/weather-lists/picontrol/ukesm1-0-ll/pr.txt'
# weather_tasmax_links_list['picontrol-ukesm1-0-ll']      = './resources/weather-lists/picontrol/ukesm1-0-ll/tasmax.txt'
# weather_tasmin_links_list['picontrol-ukesm1-0-ll']      = './resources/weather-lists/picontrol/ukesm1-0-ll/tasmin.txt'
# weather_wind_links_list['picontrol-ukesm1-0-ll']     = './resources/weather-lists/picontrol/ukesm1-0-ll/sfcwind.txt'
# weather_rlds_links_list['picontrol-ukesm1-0-ll']        = './resources/weather-lists/picontrol/ukesm1-0-ll/rlds.txt'
# weather_hurs_links_list['picontrol-ukesm1-0-ll']        = './resources/weather-lists/picontrol/ukesm1-0-ll/hurs.txt'
														
# weather_pr_links_list['picontrol-gfdl-esm4']            = './resources/weather-lists/picontrol/gfdl-esm4/pr.txt'
# weather_tasmax_links_list['picontrol-gfdl-esm4']        = './resources/weather-lists/picontrol/gfdl-esm4/tasmax.txt'
# weather_tasmin_links_list['picontrol-gfdl-esm4']        = './resources/weather-lists/picontrol/gfdl-esm4/tasmin.txt'
# weather_wind_links_list['picontrol-gfdl-esm4']       = './resources/weather-lists/picontrol/gfdl-esm4/sfcwind.txt'
# weather_rlds_links_list['picontrol-gfdl-esm4']          = './resources/weather-lists/picontrol/gfdl-esm4/rlds.txt'
# weather_hurs_links_list['picontrol-gfdl-esm4']          = './resources/weather-lists/picontrol/gfdl-esm4/hurs.txt'
														
# weather_pr_links_list['picontrol-ipsl-cm6a-lr']         = './resources/weather-lists/picontrol/ipsl-cm6a-lr/pr.txt'
# weather_tasmax_links_list['picontrol-ipsl-cm6a-lr']     = './resources/weather-lists/picontrol/ipsl-cm6a-lr/tasmax.txt'
# weather_tasmin_links_list['picontrol-ipsl-cm6a-lr']     = './resources/weather-lists/picontrol/ipsl-cm6a-lr/tasmin.txt'
# weather_wind_links_list['picontrol-ipsl-cm6a-lr']    = './resources/weather-lists/picontrol/ipsl-cm6a-lr/sfcwind.txt'
# weather_rlds_links_list['picontrol-ipsl-cm6a-lr']       = './resources/weather-lists/picontrol/ipsl-cm6a-lr/rlds.txt'
# weather_hurs_links_list['picontrol-ipsl-cm6a-lr']       = './resources/weather-lists/picontrol/ipsl-cm6a-lr/hurs.txt'
														
# weather_pr_links_list['picontrol-mri-esm2-0']           = './resources/weather-lists/picontrol/mri-esm2-0/pr.txt'
# weather_tasmax_links_list['picontrol-mri-esm2-0']       = './resources/weather-lists/picontrol/mri-esm2-0/tasmax.txt'
# weather_tasmin_links_list['picontrol-mri-esm2-0']       = './resources/weather-lists/picontrol/mri-esm2-0/tasmin.txt'
# weather_wind_links_list['picontrol-mri-esm2-0']      = './resources/weather-lists/picontrol/mri-esm2-0/sfcwind.txt'
# weather_rlds_links_list['picontrol-mri-esm2-0']         = './resources/weather-lists/picontrol/mri-esm2-0/rlds.txt'
# weather_hurs_links_list['picontrol-mri-esm2-0']         = './resources/weather-lists/picontrol/mri-esm2-0/hurs.txt'
														
# weather_pr_links_list['ssp126-mpi-esm1-2-hr']           = './resources/weather-lists/ssp126/mpi-esm1-2-hr/pr.txt'
# weather_tasmax_links_list['ssp126-mpi-esm1-2-hr']       = './resources/weather-lists/ssp126/mpi-esm1-2-hr/tasmax.txt'
# weather_tasmin_links_list['ssp126-mpi-esm1-2-hr']       = './resources/weather-lists/ssp126/mpi-esm1-2-hr/tasmin.txt'
# weather_wind_links_list['ssp126-mpi-esm1-2-hr']      = './resources/weather-lists/ssp126/mpi-esm1-2-hr/sfcwind.txt'
# weather_rlds_links_list['ssp126-mpi-esm1-2-hr']         = './resources/weather-lists/ssp126/mpi-esm1-2-hr/rlds.txt'
# weather_hurs_links_list['ssp126-mpi-esm1-2-hr']         = './resources/weather-lists/ssp126/mpi-esm1-2-hr/hurs.txt'
														
# weather_pr_links_list['ssp126-ukesm1-0-ll']             = './resources/weather-lists/ssp126/ukesm1-0-ll/pr.txt'
# weather_tasmax_links_list['ssp126-ukesm1-0-ll']         = './resources/weather-lists/ssp126/ukesm1-0-ll/tasmax.txt'
# weather_tasmin_links_list['ssp126-ukesm1-0-ll']         = './resources/weather-lists/ssp126/ukesm1-0-ll/tasmin.txt'
# weather_wind_links_list['ssp126-ukesm1-0-ll']        = './resources/weather-lists/ssp126/ukesm1-0-ll/sfcwind.txt'
# weather_rlds_links_list['ssp126-ukesm1-0-ll']           = './resources/weather-lists/ssp126/ukesm1-0-ll/rlds.txt'
# weather_hurs_links_list['ssp126-ukesm1-0-ll']           = './resources/weather-lists/ssp126/ukesm1-0-ll/hurs.txt'
														
# weather_pr_links_list['ssp126-gfdl-esm4']               = './resources/weather-lists/ssp126/gfdl-esm4/pr.txt'
# weather_tasmax_links_list['ssp126-gfdl-esm4']           = './resources/weather-lists/ssp126/gfdl-esm4/tasmax.txt'
# weather_tasmin_links_list['ssp126-gfdl-esm4']           = './resources/weather-lists/ssp126/gfdl-esm4/tasmin.txt'
# weather_wind_links_list['ssp126-gfdl-esm4']          = './resources/weather-lists/ssp126/gfdl-esm4/sfcwind.txt'
# weather_rlds_links_list['ssp126-gfdl-esm4']             = './resources/weather-lists/ssp126/gfdl-esm4/rlds.txt'
# weather_hurs_links_list['ssp126-gfdl-esm4']             = './resources/weather-lists/ssp126/gfdl-esm4/hurs.txt'
														
# weather_pr_links_list['ssp126-ipsl-cm6a-lr']            = './resources/weather-lists/ssp126/ipsl-cm6a-lr/pr.txt'
# weather_tasmax_links_list['ssp126-ipsl-cm6a-lr']        = './resources/weather-lists/ssp126/ipsl-cm6a-lr/tasmax.txt'
# weather_tasmin_links_list['ssp126-ipsl-cm6a-lr']        = './resources/weather-lists/ssp126/ipsl-cm6a-lr/tasmin.txt'
# weather_wind_links_list['ssp126-ipsl-cm6a-lr']       = './resources/weather-lists/ssp126/ipsl-cm6a-lr/sfcwind.txt'
# weather_rlds_links_list['ssp126-ipsl-cm6a-lr']          = './resources/weather-lists/ssp126/ipsl-cm6a-lr/rlds.txt'
# weather_hurs_links_list['ssp126-ipsl-cm6a-lr']          = './resources/weather-lists/ssp126/ipsl-cm6a-lr/hurs.txt'
														
# weather_pr_links_list['ssp126-mri-esm2-0']              = './resources/weather-lists/ssp126/mri-esm2-0/pr.txt'
# weather_tasmax_links_list['ssp126-mri-esm2-0']          = './resources/weather-lists/ssp126/mri-esm2-0/tasmax.txt'
# weather_tasmin_links_list['ssp126-mri-esm2-0']          = './resources/weather-lists/ssp126/mri-esm2-0/tasmin.txt'
# weather_wind_links_list['ssp126-mri-esm2-0']         = './resources/weather-lists/ssp126/mri-esm2-0/sfcwind.txt'
# weather_rlds_links_list['ssp126-mri-esm2-0']            = './resources/weather-lists/ssp126/mri-esm2-0/rlds.txt'
# weather_hurs_links_list['ssp126-mri-esm2-0']            = './resources/weather-lists/ssp126/mri-esm2-0/hurs.txt'
														
# weather_pr_links_list['ssp370-mpi-esm1-2-hr']           = './resources/weather-lists/ssp370/mpi-esm1-2-hr/pr.txt'
# weather_tasmax_links_list['ssp370-mpi-esm1-2-hr']       = './resources/weather-lists/ssp370/mpi-esm1-2-hr/tasmax.txt'
# weather_tasmin_links_list['ssp370-mpi-esm1-2-hr']       = './resources/weather-lists/ssp370/mpi-esm1-2-hr/tasmin.txt'
# weather_wind_links_list['ssp370-mpi-esm1-2-hr']      = './resources/weather-lists/ssp370/mpi-esm1-2-hr/sfcwind.txt'
# weather_rlds_links_list['ssp370-mpi-esm1-2-hr']         = './resources/weather-lists/ssp370/mpi-esm1-2-hr/rlds.txt'
# weather_hurs_links_list['ssp370-mpi-esm1-2-hr']         = './resources/weather-lists/ssp370/mpi-esm1-2-hr/hurs.txt'
														
# weather_pr_links_list['ssp370-ukesm1-0-ll']             = './resources/weather-lists/ssp370/ukesm1-0-ll/pr.txt'
# weather_tasmax_links_list['ssp370-ukesm1-0-ll']         = './resources/weather-lists/ssp370/ukesm1-0-ll/tasmax.txt'
# weather_tasmin_links_list['ssp370-ukesm1-0-ll']         = './resources/weather-lists/ssp370/ukesm1-0-ll/tasmin.txt'
# weather_wind_links_list['ssp370-ukesm1-0-ll']        = './resources/weather-lists/ssp370/ukesm1-0-ll/sfcwind.txt'
# weather_rlds_links_list['ssp370-ukesm1-0-ll']           = './resources/weather-lists/ssp370/ukesm1-0-ll/rlds.txt'
# weather_hurs_links_list['ssp370-ukesm1-0-ll']           = './resources/weather-lists/ssp370/ukesm1-0-ll/hurs.txt'
														
# weather_pr_links_list['ssp370-gfdl-esm4']               = './resources/weather-lists/ssp370/gfdl-esm4/pr.txt'
# weather_tasmax_links_list['ssp370-gfdl-esm4']           = './resources/weather-lists/ssp370/gfdl-esm4/tasmax.txt'
# weather_tasmin_links_list['ssp370-gfdl-esm4']           = './resources/weather-lists/ssp370/gfdl-esm4/tasmin.txt'
# weather_wind_links_list['ssp370-gfdl-esm4']          = './resources/weather-lists/ssp370/gfdl-esm4/sfcwind.txt'
# weather_rlds_links_list['ssp370-gfdl-esm4']             = './resources/weather-lists/ssp370/gfdl-esm4/rlds.txt'
# weather_hurs_links_list['ssp370-gfdl-esm4']             = './resources/weather-lists/ssp370/gfdl-esm4/hurs.txt'
														
# weather_pr_links_list['ssp370-ipsl-cm6a-lr']            = './resources/weather-lists/ssp370/ipsl-cm6a-lr/pr.txt'
# weather_tasmax_links_list['ssp370-ipsl-cm6a-lr']        = './resources/weather-lists/ssp370/ipsl-cm6a-lr/tasmax.txt'
# weather_tasmin_links_list['ssp370-ipsl-cm6a-lr']        = './resources/weather-lists/ssp370/ipsl-cm6a-lr/tasmin.txt'
# weather_wind_links_list['ssp370-ipsl-cm6a-lr']       = './resources/weather-lists/ssp370/ipsl-cm6a-lr/sfcwind.txt'
# weather_rlds_links_list['ssp370-ipsl-cm6a-lr']          = './resources/weather-lists/ssp370/ipsl-cm6a-lr/rlds.txt'
# weather_hurs_links_list['ssp370-ipsl-cm6a-lr']          = './resources/weather-lists/ssp370/ipsl-cm6a-lr/hurs.txt'
														
# weather_pr_links_list['ssp370-mri-esm2-0']              = './resources/weather-lists/ssp370/mri-esm2-0/pr.txt'
# weather_tasmax_links_list['ssp370-mri-esm2-0']          = './resources/weather-lists/ssp370/mri-esm2-0/tasmax.txt'
# weather_tasmin_links_list['ssp370-mri-esm2-0']          = './resources/weather-lists/ssp370/mri-esm2-0/tasmin.txt'
# weather_wind_links_list['ssp370-mri-esm2-0']         = './resources/weather-lists/ssp370/mri-esm2-0/sfcwind.txt'
# weather_rlds_links_list['ssp370-mri-esm2-0']            = './resources/weather-lists/ssp370/mri-esm2-0/rlds.txt'
# weather_hurs_links_list['ssp370-mri-esm2-0']            = './resources/weather-lists/ssp370/mri-esm2-0/hurs.txt'
														
# weather_pr_links_list['ssp585-mpi-esm1-2-hr']           = './resources/weather-lists/ssp585/mpi-esm1-2-hr/pr.txt'
# weather_tasmax_links_list['ssp585-mpi-esm1-2-hr']       = './resources/weather-lists/ssp585/mpi-esm1-2-hr/tasmax.txt'
# weather_tasmin_links_list['ssp585-mpi-esm1-2-hr']       = './resources/weather-lists/ssp585/mpi-esm1-2-hr/tasmin.txt'
# weather_wind_links_list['ssp585-mpi-esm1-2-hr']      = './resources/weather-lists/ssp585/mpi-esm1-2-hr/sfcwind.txt'
# weather_rlds_links_list['ssp585-mpi-esm1-2-hr']         = './resources/weather-lists/ssp585/mpi-esm1-2-hr/rlds.txt'
# weather_hurs_links_list['ssp585-mpi-esm1-2-hr']         = './resources/weather-lists/ssp585/mpi-esm1-2-hr/hurs.txt'
														
# weather_pr_links_list['ssp585-ukesm1-0-ll']             = './resources/weather-lists/ssp585/ukesm1-0-ll/pr.txt'
# weather_tasmax_links_list['ssp585-ukesm1-0-ll']         = './resources/weather-lists/ssp585/ukesm1-0-ll/tasmax.txt'
# weather_tasmin_links_list['ssp585-ukesm1-0-ll']         = './resources/weather-lists/ssp585/ukesm1-0-ll/tasmin.txt'
# weather_wind_links_list['ssp585-ukesm1-0-ll']        = './resources/weather-lists/ssp585/ukesm1-0-ll/sfcwind.txt'
# weather_rlds_links_list['ssp585-ukesm1-0-ll']           = './resources/weather-lists/ssp585/ukesm1-0-ll/rlds.txt'
# weather_hurs_links_list['ssp585-ukesm1-0-ll']           = './resources/weather-lists/ssp585/ukesm1-0-ll/hurs.txt'
														
# weather_pr_links_list['ssp585-gfdl-esm4']               = './resources/weather-lists/ssp585/gfdl-esm4/pr.txt'
# weather_tasmax_links_list['ssp585-gfdl-esm4']           = './resources/weather-lists/ssp585/gfdl-esm4/tasmax.txt'
# weather_tasmin_links_list['ssp585-gfdl-esm4']           = './resources/weather-lists/ssp585/gfdl-esm4/tasmin.txt'
# weather_wind_links_list['ssp585-gfdl-esm4']          = './resources/weather-lists/ssp585/gfdl-esm4/sfcwind.txt'
# weather_rlds_links_list['ssp585-gfdl-esm4']             = './resources/weather-lists/ssp585/gfdl-esm4/rlds.txt'
# weather_hurs_links_list['ssp585-gfdl-esm4']             = './resources/weather-lists/ssp585/gfdl-esm4/hurs.txt'
														
# weather_pr_links_list['ssp585-ipsl-cm6a-lr']            = './resources/weather-lists/ssp585/ipsl-cm6a-lr/pr.txt'
# weather_tasmax_links_list['ssp585-ipsl-cm6a-lr']        = './resources/weather-lists/ssp585/ipsl-cm6a-lr/tasmax.txt'
# weather_tasmin_links_list['ssp585-ipsl-cm6a-lr']        = './resources/weather-lists/ssp585/ipsl-cm6a-lr/tasmin.txt'
# weather_wind_links_list['ssp585-ipsl-cm6a-lr']       = './resources/weather-lists/ssp585/ipsl-cm6a-lr/sfcwind.txt'
# weather_rlds_links_list['ssp585-ipsl-cm6a-lr']          = './resources/weather-lists/ssp585/ipsl-cm6a-lr/rlds.txt'
# weather_hurs_links_list['ssp585-ipsl-cm6a-lr']          = './resources/weather-lists/ssp585/ipsl-cm6a-lr/hurs.txt'
														
# weather_pr_links_list['ssp585-mri-esm2-0']              = './resources/weather-lists/ssp585/mri-esm2-0/pr.txt'
# weather_tasmax_links_list['ssp585-mri-esm2-0']          = './resources/weather-lists/ssp585/mri-esm2-0/tasmax.txt'
# weather_tasmin_links_list['ssp585-mri-esm2-0']          = './resources/weather-lists/ssp585/mri-esm2-0/tasmin.txt'
# weather_wind_links_list['ssp585-mri-esm2-0']         = './resources/weather-lists/ssp585/mri-esm2-0/sfcwind.txt'
# weather_rlds_links_list['ssp585-mri-esm2-0']            = './resources/weather-lists/ssp585/mri-esm2-0/rlds.txt'
# weather_hurs_links_list['ssp585-mri-esm2-0']            = './resources/weather-lists/ssp585/mri-esm2-0/hurs.txt'
															
weather_resolution          = 4 # decimal degrees was 5

prepare_weather             = True
redo_weather                = True
weather_redownload          = False

# run settings
run_period                  = '1980-1990'

# output processing
output_re_shape             = True
