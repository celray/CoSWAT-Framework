#!/bin/python3

'''
This script prepares the lake data for the whole world filtered by areal threshold.
It is part of the data preparation scripts for the  COmmunity SWAT+ Model (CoSWAT-Global)
development. A project aimed at providing a community contributed global SWAT+ model
initiated and led by Celray James CHAWANDA.

This was modified by Jose Teran: 

- To include HydroLakes and GranD v1.3 Datasets in the CoSWAT GHM
- It determines the properties of the lake based on the aformentioned and the GLOBathy dataset

Author  : Celray James CHAWANDA
Date    : 10/04/2025
Contact : celray@chawanda.com - jose.pablo.teran.orsini@vub.be
Licence : MIT
GitHub  : github.com/celray - github.com/jopator
'''

# imports
import time, sys, os
import datavariables as variables
from cjfx import clip_features, create_path, list_folders, ignore_warnings
from ccfx import exists, createPath, downloadFile, uncompress, deleteFile
import geopandas as gpd
import numpy as np

from shapely.geometry import Polygon, MultiPolygon
import xarray as xr

ignore_warnings()

# functions
# def remove_holes(geometry):
#     if geometry.geom_type == 'Polygon':
#         return Polygon(geometry.exterior)
#     elif geometry.geom_type == 'MultiPolygon':
#         return MultiPolygon([Polygon(part.exterior) for part in geometry])
#     else:
#         return geometry

def remove_holes(geometry):
    if geometry.geom_type == 'Polygon':
        return Polygon(geometry.exterior)
    elif geometry.geom_type == 'MultiPolygon':
        return MultiPolygon([Polygon(part.exterior) for part in geometry.geoms])
    else:
        return geometry
    
def get_globathy(dframe,ds):

    '''
    Function to get GLOBathy parameters into a lake specified in a (Geo)DataFrame
    
    The parameters are to define h-A-V relationships
    
    A = a*h^b
    V = c*h^d
    h = (V/c)^(1/d)
    h = (A/a)^(1/b)
    
    '''
    df = dframe.copy() # To avoid the infamous Setting With Copy Warning >:(
    df.loc[:, 'a'] = None
    df.loc[:, 'b'] = None
    df.loc[:, 'c'] = None
    df.loc[:, 'd'] = None
    df.loc[:, 'maxDepth']   = None
    df.loc[:, 'meanDepth']  = None
    df.loc[:, 'surfArea']   = None
    df.loc[:, 'totVol']     = None

    for index,row in df.iterrows():
        hydro_id = row["Hylak_id"]
        ds_lake = ds.where(ds["lake_id"]==hydro_id,drop=True)
        df.at[index, "a"] , df.at[index, "b"] = ds_lake["f_hA"].values[0][0] , ds_lake["f_hA"].values[0][1]
        df.at[index, "c"] , df.at[index, "d"] = ds_lake["f_hV"].values[0][0] , ds_lake["f_hV"].values[0][1]
        df.at[index, "maxDepth"]        = ds_lake["lake_attributes"].values[0][0] #m
        df.at[index, "meanDepth"]       = ds_lake["lake_attributes"].values[0][1] #m
        df.at[index, "MaxArea_km2"]     = ds_lake["lake_attributes"].values[0][2] #km^2
        df.at[index, "MaxVol_km3"]      = ds_lake["lake_attributes"].values[0][3] #km^3
    
    return df

# change working directory
me = os.path.realpath(__file__)
os.chdir(os.path.dirname(me))

if len(sys.argv) < 2:
    print(f"! select a region for which to prepare the dataset. options are: {', '.join(list_folders('./resources/regions/'))}\n")
    sys.exit()
regions = sys.argv[1:]


print('# preparing lakes data\n')

details = {
    'auth': variables.final_proj_auth,
    'code': variables.final_proj_code,
}

hydro_lakes_path    = variables.hydro_lakes_path
grand_res_path      = variables.grand_res_path
globathy_path       = variables.globathy_path

if not exists(hydro_lakes_path):
    print(f"\t! hydroLakes dataset not found at {hydro_lakes_path}")
    print(f"\t> attempting to retrieve : 'https://celray.chawanda.com/assets/downloads/HydroLAKES_v10.7z'")

    createPath(os.path.dirname(hydro_lakes_path))
    downloadFile('https://celray.chawanda.com/assets/downloads/HydroLAKES_v10.7z', f"{os.path.dirname(hydro_lakes_path)}/", num_connections=1)
    print(f"\t> uncompressing")
    src = f"{os.path.dirname(hydro_lakes_path)}/HydroLAKES_v10.7z"
    dst = f"{os.path.dirname(hydro_lakes_path)}/"
    uncompress(src, dst)
    deleteFile(src)

if not exists(grand_res_path):
    print(f"\t! GranD dataset not found at {grand_res_path}")
    print(f"\t> attempting to retrieve : 'https://celray.chawanda.com/assets/downloads/GRanD_reservoirs_v1_3.7z'")

    createPath(os.path.dirname(grand_res_path))
    downloadFile('https://celray.chawanda.com/assets/downloads/GRanD_reservoirs_v1_3.7z', f"{os.path.dirname(grand_res_path)}/", num_connections=1)
    print(f"\t> uncompressing")
    src = f"{os.path.dirname(grand_res_path)}/GRanD_reservoirs_v1_3.7z"
    dst = f"{os.path.dirname(grand_res_path)}/"
    uncompress(src, dst)
    deleteFile(src)

if not exists(globathy_path):
    print(f"\t! GLOBathy dataset not found at {globathy_path}")
    print(f"\t> attempting to retrieve : 'https://celray.chawanda.com/assets/downloads/GLOBathy.7z'")

    createPath(os.path.dirname(globathy_path))
    downloadFile('https://celray.chawanda.com/assets/downloads/GLOBathy.7z', f"{os.path.dirname(globathy_path)}/", num_connections=1)
    print(f"\t> uncompressing")
    src = f"{os.path.dirname(globathy_path)}/GLOBathy.7z"
    dst = f"{os.path.dirname(globathy_path)}/"
    uncompress(src, dst)
    deleteFile(src)

globathy_ds         = xr.open_dataset(globathy_path)            # Read globathy DataSet
hydro_lakes_gdf     = gpd.read_file(hydro_lakes_path)           # Read HydroLakes Dataset
grand_res_gdf       = gpd.read_file(grand_res_path)             # Read GranD Dataset



for region in regions:
    details['region'] = region
    print(f"\t> preparing lakes data for {region} region")
    
    create_path(variables.grand_final_shp.format(**details))

    bboxfn                  = "./resources/regions/{region}/bounding-box-{auth}-{code}.gpkg".format(**details) #Changed name from regionfn to bboxgfn
    regionfn                = "./resources/regions/{region}/outlets-buffer.gpkg".format(**details)

    mask_gdf                = gpd.read_file(bboxfn)
    clipped_hydro_lakes     = hydro_lakes_gdf.clip(mask_gdf.to_crs(hydro_lakes_gdf.crs))
    clipped_grand           = grand_res_gdf.clip(mask_gdf.to_crs(grand_res_gdf.crs))
    
    # clipped_hydro_lakes.to_file("../model-data/{region}/shapes/clipped_lakes.shp".format(**details))
    # clipped_hydro_lakes.to_file("../model-data/{region}/shapes/clipped_grand.shp".format(**details))
    
    hydro_lakes_columns     = [ 'Hylak_id', 'Lake_name', 'Country', 'Continent',                                 # Columns of interest from HydroLakes Dataset
                                'Lake_type', 'Grand_id', 'Lake_area', 'Shore_len', 'Shore_dev',
                                'Vol_total', 'Vol_res', 'Vol_src', 'Depth_avg', 'Dis_avg', 'Res_time',
                                'Elevation','geometry']
    
    grand_columns           = [ 'GRAND_ID', 'RES_NAME', 'DAM_NAME', 'RIVER', 'CAP_MCM', 'CAP_MAX',               # Columns of interest from GranD Dataset
                                'MAIN_BASIN', 'SUB_BASIN', 'NEAR_CITY', 'YEAR', 'REM_YEAR',
                                'DAM_HGT_M', 'DAM_LEN_M', 'AREA_SKM', 'AREA_REP', 'AREA_MAX', 'AREA_MIN',
                                'CAP_REP', 'CAP_MIN', 'DEPTH_M', 'DIS_AVG_LS', 'DOR_PC', 'ELEV_MASL', 
                                'MAIN_USE', 'LAKE_CTRL','TIMELINE']
    
    # filter our masked lakes and reservoirs
    from resources import maskedReservoirs
    clipped_hydro_lakes    = clipped_hydro_lakes[~clipped_hydro_lakes['Hylak_id'].isin(maskedReservoirs.Hylak_Id)]
    clipped_grand          = clipped_grand[~clipped_grand['GRAND_ID'].isin(maskedReservoirs.GRAND_ID)]


    # Filtering out small lakes and reservoirs

    clipped_hydro_lakes         = clipped_hydro_lakes.to_crs("{auth}:{code}".format(**details))          # Setting CRS of project
    clipped_grand               = clipped_grand.to_crs("{auth}:{code}".format(**details))                # Setting CRS of project
        
    clipped_hydro_lakes         = clipped_hydro_lakes[hydro_lakes_columns]
    clipped_grand               = clipped_grand[grand_columns]
    
    clipped_grand                = clipped_grand.rename(columns={"GRAND_ID":"Grand_id"})
    clippedReservoirs            = clipped_hydro_lakes.merge(clipped_grand,on="Grand_id",how="left")
    
    
    print(f"\t - removing islands from lake and reservoir geometries")
    print(f"\t - filtering lakes and reservoirs smaller than {variables.grand_lake_thres} km2") 
    clippedReservoirs            = clippedReservoirs[clippedReservoirs["Lake_area"] > variables.grand_lake_thres]

    if clippedReservoirs.empty:    
        print(f"\t ! empty lakes and reservoirs after filtering for this region, will not consider lakes/reservoirs")
        continue
    
    clippedReservoirs["calcAreas"]  = clippedReservoirs.Lake_area                                                # Value in squared km
    clippedReservoirs["calcVol"]    = clippedReservoirs.Vol_total*1000000                                        # Value in cubic meters
    clippedReservoirs["RES"]        = 1
    
    # Implement GLOBAthy h-A-V relation coefficients
    clippedReservoirs = get_globathy(clippedReservoirs,globathy_ds)
    clippedReservoirs['geometry'] = clippedReservoirs['geometry'].apply(remove_holes)
    
    
    # Clean up to get key variables from all Datasets
    # Declaring key variables
    clippedReservoirsFinal                      = clippedReservoirs.copy()
    clippedReservoirsFinal                      = clippedReservoirsFinal.reset_index(drop=True)
    clippedReservoirsFinal.loc[:,"smax"]        = None                                                                   # Maximum storage in cubic meters --> Particularly useful for Outflow simulation methods
    clippedReservoirsFinal.loc[:,"pvol"]        = None                                                                   # Principal Volume for SWAT+ in 10^4 cubic meters 
    clippedReservoirsFinal.loc[:,"evol"]        = None                                                                   # Emergency Volume for SWAT+ in 10^4 cubic meters
    clippedReservoirsFinal.loc[:,"parea"]       = None                                                                   # Surface Area corresponding to Principal Volume in hectares
    clippedReservoirsFinal.loc[:,"earea"]       = None                                                                   # Surface Area corresponding to Emergency Volume in hectares
    clippedReservoirsFinal.loc[:,"elev_masl"]   = None 
    clippedReservoirsFinal.loc[:,"dis_avg"]     = None                                                                   # Will be in m3/s
    
    for index, row in clippedReservoirsFinal.iterrows():
        
        # Get Globathy Coefficients
        a = row["a"]
        b = row["b"]
        c = row["c"]
        d = row["d"]
        
        if row["Grand_id"] == 0:                                                                                    # This means it is not registered in GranD, we extract from HydroLakes   
            
            lake_area = row['Lake_area']                                                                            # Get lake area in km2
                                
            if row["Lake_type"] == 1:                                                                               # This means it is an unreagulated lake
                smax = row["Vol_total"]
                
            if row["Lake_type"] == 2 or row["Lake_type"] == 3:                                                      # This means it is an regulated lake or reservoir that is not registered on GranD
                vol_res = row["Vol_res"]                                                                            # Initial approach: Read reservoir volume
                
                if vol_res == 0:                                                                                    # Means there is no registered data so we assign Vol_total as Smax     
                    smax = row["Vol_total"]
                else:
                    smax = vol_res

            # Smax
            clippedReservoirsFinal.loc[index,"smax"]  = round(smax*1000000,2)                                       # Value from hydrolakes is in mcm --> We convert to m3
            
            # Proceed to calculate other parameters            
            clippedReservoirsFinal.loc[index,"pvol"]  = round(smax*100,4)                                           # Value from hydrolakes is in mcm --> We convert to 10^4 m3
            clippedReservoirsFinal.loc[index,"evol"]  = round(smax*100,4)                                           # As there is no more info, we assume evol equals pvol
            
            clippedReservoirsFinal.loc[index,"parea"] = round(lake_area*100,4)                                      # Value from hydrolakes is in km2 --> We convert to ha
            clippedReservoirsFinal.loc[index,"earea"] = round(lake_area*100,4)                                      # As there is no more info, we assume earea equals parea
            
            # Homogenize to one elevation
            clippedReservoirsFinal.loc[index,"elev_masl"] = round(row["Elevation"],2)
            clippedReservoirsFinal.loc[index,"dis_avg"] = round(row["Dis_avg"],2)
        
        else:                                                                                                       # This means the reservoir is stored in the GranD dabase, we will extract data from there
            area_skm, area_rep, area_max = row["AREA_SKM"],row["AREA_REP"],row["AREA_MAX"]
            cap_mcm, cap_max, cap_rep    = row["CAP_MCM"],row["CAP_MAX"],row["CAP_REP"]
            
            smax = max(cap_mcm,cap_max,cap_rep)                                                                     # Will get the maximum storage out of all of them, if there is no data the value is -99 so we ignore it --> Values in mcm
            amax = max(area_skm,area_rep,area_max)                                                                  # Same as above but for max area --> Values in km2
            
            clippedReservoirsFinal.loc[index,"evol"]   = round(smax*100,4)                                          # We assume Smax as the emergency volume --> We convert to m3
            clippedReservoirsFinal.loc[index,"earea"]  = round(amax*100,4)                                          # We assume Amax as the area for emergency volume --> We convert to ha
            
            # Derivation of principal volume and corresponding area
            if cap_rep > 0:                                                                                         # If there is a value reported for Representative capacity, we assign it to pvol
                pvol = cap_rep
                
            else:                                                                                                   # Otherwise, we assign cap_mcm which is the representative maximum storage
                pvol = cap_mcm
            
            if pvol < smax:
                depth_pvol = (pvol*0.001/c)**(1/d)                                                                   # Getting depth corresponding to this volume
                p_area     = a*(depth_pvol**b)                                                                       # Getting corresponding area
            
            else:
                p_area     = amax
                
            clippedReservoirsFinal.loc[index,"smax"] = round(smax*1000000,2)    
            clippedReservoirsFinal.loc[index,"pvol"] = round(pvol*100,4)
            clippedReservoirsFinal.loc[index,"parea"] = round(p_area*100,4)
            
            # Homogenize to one elevation and average discharge
            clippedReservoirsFinal.loc[index,"elev_masl"] = round(row["ELEV_MASL"],2)
            clippedReservoirsFinal.loc[index,"dis_avg"] = round(row["DIS_AVG_LS"]/1000,2)
        
                # Getting SWAT+ Reservoir shape parameters based on Globathy coefficients
        '''
        br1 = a*(1/c)^b/d
        br2 = b/d
        
        This comes from:
        h = (A/a)^(1/b) and h = (V/c)^(1/d)
        So, we can derive:
        (A/a)^(1/b) = (V/c)^(1/d)
        
        Solving for A:
        A = a*(1/c)^b/d * V^(b/d)
        
        
        We do this because...
        
        On routine res_control.f90, the following is done:
        
                !! update surface area
            if (res(jres)%flo > 0.) then
            res_wat_d(jres)%area_ha = res_ob(jres)%br1 * res(jres)%flo ** res_ob(jres)%br2 
            else
            res_wat_d(jres)%area_ha = 0.
            end if
            
        Which is basically updating the area based on br1 and br2 coefficients... Which are taken from shp_co1 and shp_co2...
        
        This can be chekced at routinte res_init.f90, where they are read from the reservoir object res_hyd (from reservoir_data_module.f90)
        '''    
            
        br1 = a*(1/c)**(b/d)
        br2 = b/d
        
        clippedReservoirsFinal.loc[index,"br1"] = round(br1,5)                                                                 # This is the coefficient for the area calculation in SWAT+
        clippedReservoirsFinal.loc[index,"br2"] = round(br2,5)                                                                 # This is the coefficient for the area calculation in SWAT+
            
    # Give a lake id for SWAT+ gis_id
    clippedReservoirsFinal.loc[:,"LakeId"] = np.arange(1,len(clippedReservoirsFinal)+1,1,dtype=int)
    clippedReservoirsFinal = clippedReservoirsFinal[clippedReservoirsFinal['Hylak_id'].notna()]
    
    # for index,row in clippedReservoirsFinal.iterrows():
    #     print(f"Index {row['LakeId']} | Grand_id = {row['Grand_id']} | Lake_type = {row['Lake_type']} | Vol_total = {row['Vol_total']} | Vol_res = {row['Vol_res']} | CAP_MCM = {row['CAP_MCM']} | CAP_MAX = {row['CAP_MAX']} | CAP_REP = {row['CAP_REP']} | smax = {row['smax']}")
    
    # Select columns of interest and export
    clippedReservoirsFinal = clippedReservoirsFinal[[   'LakeId','Hylak_id','smax','pvol','evol','parea','earea','br1','br2',
                                                        "RES","calcAreas","calcVol","elev_masl","dis_avg",                  # Columns of interest for SWAT+
                                                        'Lake_name', 'Country', 'Continent','Lake_type',                                
                                                        'Depth_avg', 'Res_time',                                            # Columns of interest from HydroLakes Dataset
                                                        'Grand_id',                                               
                                                        'RES_NAME', 'DAM_NAME', 'RIVER','MAIN_BASIN', 'SUB_BASIN',             
                                                        'YEAR', 'REM_YEAR','DAM_HGT_M', 'DAM_LEN_M','DEPTH_M',
                                                        'DOR_PC','MAIN_USE', 'LAKE_CTRL','TIMELINE',                        # Columns of interest from GranD Dataset 
                                                        'a','b','c','d','maxDepth','meanDepth','MaxArea_km2',               # Columns of interest from GLOBathy Dataset	
                                                        "geometry"]]

               
    
    clippedReservoirsFinal.to_file(variables.grand_final_shp.format(**details))
    clippedReservoirsFinal.to_file(variables.grand_final_gpkg.format(**details), driver = 'GPKG')

    print(f"\t - finished preparing lakes data for {region} region\n")
