#!/usr/bin/env python3

import os, sys
from ccfx import *
import datavariables as variables
from coswatFX import shouldKeep, writeSWATPlusWeather
import xarray
import time

regionPointsDir = "./regionPoints"
weatherDir = './weather-ws'

details         = {
    'auth': variables.final_proj_auth,
    'code': variables.final_proj_code,
}

extTypes         = ["tem", "pcp", "slr", "hmd", "wnd", ]

varNames         = {'pcp': ['pr',],
                    'tem': ['tasmax', 'tasmin'],
                    'wnd': ['wnd', 'sfcwind', 'sfcWind', 'wind'],
                    'hmd': ['hurs', 'rhs'],
                    'slr': ['rlds',]}

fullVarNames     = {'pcp': "precipitation",
                    'tem': "temperature",
                    'wnd': "wind speed",
                    'hmd': "relative humidity",
                    'slr': "solar radiation"}

varFactors       = {'pcp': 86400.0000,
                    'tem':  -273.1500,
                    'slr':     0.0864,
                    'hmd':     0.0100,
                    'wnd':     1.0000}


# change working directory
me = os.path.realpath(__file__)
os.chdir(os.path.dirname(me))

regions = []

if len(sys.argv) < 2:
    regions = listFolders('./resources/regions/')
    print(f"! preparing for all regions because no option was set from: {', '.join(listFolders('./resources/regions/'))}\n")
else:
    regions = sys.argv[1:]

print('\n# preparing climate data...\n')


if __name__ == "__main__":

    currentVariables = {}

    counter = 0
    while exists(f'{weatherDir}/download/downloadLock'):
        print("  > waiting for download lock to be released...")
        time.sleep(5)
        counter += 1
        if counter > 120:
            print("  > download lock not released after 10 minutes, exiting...")
            sys.exit(1)

    writeFile(f'{weatherDir}/download/downloadLock', 'locked')

    if variables.prepare_weather:
        data = []
        for latitude in numpy.arange(-85.25, 86.25, variables.weather_resolution):
            for longitude in numpy.arange(-179.25,180.25, variables.weather_resolution):
                data.append([latitude, longitude])

        cols = ['longitude', 'latitude']
        if exists(variables.weather_points_all):deleteFile(variables.weather_points_all)
        pointsToGeodataframe(data, out_shape=variables.weather_points_all, columns=cols)

        print(f"  > created points file: {variables.weather_points_all}")

    # loop through scenarios
    for scenario in variables.available_scenarios:
        print(f"processing scenario: {scenario}")

        runPeriod = [int(yr) for yr in variables.run_period.split('-')]
        gcms = variables.weather_pr_links_list[scenario]

        for gcm in gcms:
            print(f"  > processing gcm: {gcm}")

            if not exists(f"./resources/weather-lists/"):
                os.system(f"unzip ./resources/weather-lists.zip -d ./resources")
            lines = []
            lines += readFile(variables.weather_pr_links_list[scenario][gcm])
            lines += readFile(variables.weather_hurs_links_list[scenario][gcm])
            lines += readFile(variables.weather_tasmin_links_list[scenario][gcm])
            lines += readFile(variables.weather_tasmax_links_list[scenario][gcm])
            lines += readFile(variables.weather_wind_links_list[scenario][gcm])
            lines += readFile(variables.weather_rlds_links_list[scenario][gcm])

            # filter lines
            downloadList = []
            downloadString = 'this file is created automatically so the user can see which files are downloaded\n\n'
            
            for line in lines:
                line = line.strip()
                baseFn = getFileBaseName(line)

                downloadPeriod = variables.run_period
                if scenario == 'observed':
                    downloadPeriod = variables.run_period
                elif scenario == 'historical':
                    downloadPeriod = variables.historical_period
                else:
                    downloadPeriod = variables.future_period
            
                cannotDownload = not shouldKeep(baseFn, downloadPeriod)

                if cannotDownload:
                    # print(f'! skipping {line} - not in range ({downloadPeriod})')
                    continue
                        
                if variables.weather_redownload:
                    downloadList.append([f'{line}', f'{weatherDir}/download/{scenario}/{gcm}/', "resume", 1])
                    downloadString += f'{line}\n'
                elif not exists(f'{weatherDir}/download/{scenario}/{gcm}/{getFileBaseName(line, extension = True)}'):
                    downloadList.append([f'{line}', f'{weatherDir}/download/{scenario}/{gcm}/', "resume", 1])
                    downloadString += f'{line}\n'

                downloadList.append([f'{line}', f'{weatherDir}/download/{scenario}/{gcm}/', "resume", 1])
                createPath(f'{weatherDir}/download/{scenario}/{gcm}/')

            writeFile(f"{weatherDir}/download_links.txt", downloadString)
            
            # download weather
            createPath(f'{weatherDir}/download/{scenario}/')
            pool = multiprocessing.Pool(variables.processes)

            results = pool.starmap_async(downloadFile, downloadList)
            results.get()

            pool.close()
            print()

            if exists(f'{weatherDir}/download/downloadLock'):
                deleteFile(f'{weatherDir}/download/downloadLock')


            for region in regions:
                print(f"    - region: {region}")

                details['region']   = region
                details['scenario'] = scenario
                details['gcm']      = gcm

                ds_f_names  = listFiles(f'{weatherDir}/download/{scenario}/{gcm}/', 'nc')
                ds_f_names  += listFiles(f'{weatherDir}/download/{scenario}/{gcm}/', 'nc4')

                keptFileNames = []

                for f in ds_f_names:
                    if scenario == 'observed':
                        if shouldKeep(f, variables.run_period): keptFileNames.append(f)
                    elif scenario == 'historical':
                        runPeriod = [variables.historical_period.split('-')[0], variables.historical_period.split('-')[1]]
                        if shouldKeep(f, variables.historical_period): keptFileNames.append(f)
                    else:
                        runPeriod = [variables.future_period.split('-')[0], variables.future_period.split('-')[1]]
                        if shouldKeep(f, variables.future_period): keptFileNames.append(f)

                # get region extents
                regionPoints = clipFeatures(
                    variables.weather_points_all,
                    variables.cutline.format(**details),
                    f'../model-data/{region}/weather/swatplus/{region}-weatherPoints.gpkg')
                
                regionPoints = regionPoints.to_crs(epsg=4326)
                regionExtents =regionPoints.total_bounds
                regionBox = [str(float(coord)) for coord in [regionExtents[0], regionExtents[2], regionExtents[1], regionExtents[3]]]

                # do sellatlon
                dstDirCropped = f"{weatherDir}/cropped/{region}/{scenario}/{gcm}"
                createPath(f"{dstDirCropped}/")
                jobsCrop = []
                for fname in keptFileNames:
                    if exists(f"{dstDirCropped}/{getFileBaseName(fname)}"):
                        deleteFile(f"{dstDirCropped}/{getFileBaseName(fname)}")
                        try: os.remove(f"{dstDirCropped}/{getFileBaseName(fname)}")
                        except: pass
                    command = f"cdo -O sellonlatbox,{','.join(regionBox)} {fname} {dstDirCropped}/{getFileBaseName(fname)} > /dev/null"
                    jobsCrop.append([command,])
  
                pool = multiprocessing.Pool(processes=variables.processes)
                pool.starmap_async(os.system, jobsCrop)
                pool.close()
                pool.join()

                croppedRegionFiles = listFiles(dstDirCropped, 'nc')
                croppedRegionFiles += listFiles(dstDirCropped, 'nc4')

                dstDirMerged = f"{weatherDir}/merged/{region}"
                dstDirTxt = f"{weatherDir}/text/{region}"

                jobsMerge = []
                for extType in extTypes:
                    
                    mergeTimeFiles = []
                    mergeTimeFilesMin = []
                    
                    # set the variable name
                    for fname in croppedRegionFiles:
                        if not extType in currentVariables:
                            for varName in varNames[extType]:
                                if varName in fname:
                                    currentVariables[extType] = varName
                                    break
                        
                    for fname in croppedRegionFiles:
                        if currentVariables[extType] in fname:
                            mergeTimeFiles.append(fname)
                        if extType == "tem" and "tasmin" in fname:
                            mergeTimeFilesMin.append(fname)

                    if len(mergeTimeFiles) == 0: continue
                    
                    createPath(f"{dstDirMerged}/")

                    # merge files
                    mergedFileName = f"{dstDirMerged}/{scenario}_{gcm}_{currentVariables[extType]}.nc4"

                    if extType == "tem":
                        mergedFileNameMin = mergedFileName.replace("tasmax", "tasmin")
                    
                    deleteFile(mergedFileName)
                    deleteFile(mergedFileNameMin)

                    try: os.remove(mergedFileName)
                    except: pass
                    try: os.remove(mergedFileNameMin)
                    except: pass

                    command = f"cdo -O mergetime {' '.join(mergeTimeFiles)} {mergedFileName} > /dev/null"
                    jobsMerge.append([command,])

                    if extType == "tem":
                        commandMin = f"cdo -O mergetime {' '.join(mergeTimeFilesMin)} {mergedFileNameMin} > /dev/null"
                        jobsMerge.append([commandMin,])

                pool = multiprocessing.Pool(processes=variables.processes)
                pool.starmap_async(os.system, jobsMerge)
                pool.close()
                pool.join()

                selectedCoordinates = []
                for index, row in regionPoints.iterrows():
                    selectedCoordinates.append(f"{row['geometry'].x},{row['geometry'].y},{extractRasterValue(variables.aster_tmp_tif, row['geometry'].y, row['geometry'].x)}")
                
                for extType in extTypes:
                    if not extType in currentVariables:
                        print(f"  > no variable found for {extType}")
                        continue

                    mergedFileName = f"{dstDirMerged}/{scenario}_{gcm}_{currentVariables[extType]}.nc4"
                    if not exists(mergedFileName):
                        print(f"  > file not found: {mergedFileName}")
                        continue
                    
                    # extract data
                    lonList, latList = zip(*[(float(s.split(',')[0]), float(s.split(',')[1])) for s in selectedCoordinates])
                    # Convert to NumPy arrays with shape (points,)
                    lonArray = numpy.array(lonList)
                    latArray = numpy.array(latList)
                    
                    print(f"  > getting {currentVariables[extType]} from {mergedFileName} using xarray")
                    dataset = xarray.open_dataset(mergedFileName, chunks={})

                    print(f"    - extracting points data")
                    pointsData = dataset[currentVariables[extType]].sel(
                        lon=xarray.DataArray(lonArray, dims="points"),
                        lat=xarray.DataArray(latArray, dims="points"),
                        method="nearest"
                    )

                    pointsDataFrameMin = None

                    if extType == "tem":
                        print(f"    - getting minimum temperature")
                        datasetTemMin = xarray.open_dataset(mergedFileName.replace("tasmax", "tasmin"), chunks={})
                        pointsDataTemMin = datasetTemMin["tasmin"].sel(
                            lon=xarray.DataArray(lonArray, dims="points"),
                            lat=xarray.DataArray(latArray, dims="points"),
                            method="nearest"
                        )

                        pointsDataFrameMin = pointsDataTemMin.to_dataframe().reset_index()

                    pointsDataFrame = pointsData.to_dataframe().reset_index()

                    pointsDataFrame[currentVariables[extType]] = pointsDataFrame[currentVariables[extType]].astype(float)

                    if extType == "tem":
                        pointsDataFrame[currentVariables[extType]]  = pointsDataFrame[currentVariables[extType]] + varFactors[extType]
                        
                        pointsDataFrameMin['tasmin']                = pointsDataFrameMin['tasmin'].astype(float)
                        pointsDataFrameMin['tasmin']                = pointsDataFrameMin['tasmin'] + varFactors[extType]
                    else:
                        pointsDataFrame[currentVariables[extType]]  = pointsDataFrame[currentVariables[extType]] * varFactors[extType]
                    
                    jobs = []
                    for coordinates in selectedCoordinates:
                        jobs.append([
                            coordinates, pointsDataFrame, pointsDataFrameMin, extType, runPeriod, scenario, gcm, region, currentVariables, fullVarNames
                        ])

                    pool = multiprocessing.Pool(processes=variables.processes)
                    pool.starmap_async(writeSWATPlusWeather, jobs)
                    pool.close()
                    pool.join()

                    filesList = listFiles(f"../model-data/{region}/weather/swatplus/{scenario}/{gcm}/", extType)

                    cliString = f"""{extType}.cli: {fullVarNames[extType]} file names - file written by Celray James CHAWANDA\nfilename\n""" + \
                        "\n".join([f"{getFileBaseName(f)}" for f in filesList]) + "\n"
                    
                    writeFile(f"../model-data/{region}/weather/swatplus/{scenario}/{gcm}/{extType}.cli", cliString)
                    print("\n\n")