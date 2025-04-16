import re, geopandas, os, sys, pandas
from ccfx import createPath, getFileBaseName, writeFile
from datetime import datetime, timedelta

def isYearInFileRange(fileName, yearToCheck):
    # match all sequences of 4 digits (potential years)
    possibleYears = re.findall(r'(?<!\d)(\d{4})(?!\d)', fileName)
    
    if len(possibleYears) < 2:
        raise ValueError("Could not find two years in the file name.")

    # convert to integers and sort
    possibleYears = sorted([int(year) for year in possibleYears])
    startYear, endYear = possibleYears[0], possibleYears[-1]

    return startYear <= int(yearToCheck) <= endYear


def shouldKeep(baseFn, runPeriod):
    """Determines if a file should be downloaded based on year ranges."""

    def yearInRange(year_range, baseFn):
        start_year, end_year = map(int, year_range.split('-'))
        return isYearInFileRange(baseFn, start_year) or isYearInFileRange(baseFn, end_year)

    if yearInRange(runPeriod, baseFn):
        return True

    return False 


def clipFeatures(inputFeaturePath:str, boundaryFeature:str, outputFeature:str, keepOnlyTypes = None, v = False) -> geopandas.GeoDataFrame:
    '''
    keepOnlyTypes = ['MultiPolygon', 'Polygon', 'Point', etc]
    
    '''
    mask_gdf = geopandas.read_file(boundaryFeature)
    input_gdf = geopandas.read_file(inputFeaturePath)

    outDir = os.path.dirname(outputFeature)

    createPath(f"{outDir}/")
    out_gdf = input_gdf.clip(mask_gdf.to_crs(input_gdf.crs))

    if not keepOnlyTypes is None:
        out_gdf = out_gdf[out_gdf.geometry.apply(lambda x : x.type in keepOnlyTypes)]

    out_gdf.to_file(outputFeature)

    if v:
        print("\t  - clipped feature to " + outputFeature)
    return out_gdf


def mergeTsDataframes(dfList, startYear, endYear):
    """
    Merges a list of time series dataframes into a single dataframe with continuous dates.

    Args:
        dfList (list): A list of pandas DataFrames, each with 'date' and 'value' columns.
        startYear (int): The starting year for the complete time series.
        endYear (int): The ending year for the complete time series.

    Returns:
        pandas.DataFrame: A single DataFrame with continuous dates and merged values,
                          or -99 for missing dates.
    """

    # Generate the complete date range
    startDate = pandas.to_datetime(f'{startYear}-01-01')
    endDate = pandas.to_datetime(f'{endYear}-12-31')
    completeDateRange = pandas.date_range(start=startDate, end=endDate, freq='D')
    completeDf = pandas.DataFrame({'date': completeDateRange})
    completeDf['value'] = -99  # Initialize all values to -99

    # Merge the input dataframes
    for df in dfList:
        if not df.empty: #check if the dataframe is empty
            mergedDf = pandas.merge(completeDf, df, on='date', how='left', suffixes=('', '_y'))
            completeDf['value'] = mergedDf['value_y'].fillna(completeDf['value'])
            completeDf = completeDf[['date', 'value']] #ensure only date and value columns remain

    return completeDf


def filterAndCompleteDataframe(dataframe, coordinates, startYr_, endYr_, variableName):
    # Parse coordinates
    x, y, elev = coordinates.split(',')
    x, y = float(x), float(y)
    
    # Filter dataframe to keep only rows matching the coordinates
    filteredDataframe = dataframe[(dataframe['lon'] == x) & (dataframe['lat'] == y)].copy()
    
    # Convert time column to datetime if it's not already
    if not pandas.api.types.is_datetime64_any_dtype(filteredDataframe['time']):
        filteredDataframe['time'] = pandas.to_datetime(filteredDataframe['time'])
    
    # Create a complete date range from January 1 of startYr_ to December 31 of endYr_
    startDate = pandas.Timestamp(f"{startYr_}-01-01")
    endDate = pandas.Timestamp(f"{endYr_}-12-31")
    
    # Create a new dataframe with all dates in the range
    dateRange = pandas.date_range(start=startDate, end=endDate, freq='D')
    completeDataframe = pandas.DataFrame({'time': dateRange})
    
    # Merge with the filtered data
    resultDataframe = pandas.merge(completeDataframe, filteredDataframe, on='time', how='left')
    
    # Fill missing values with -99
    resultDataframe = resultDataframe.fillna(-99)
    
    # If the filter results in no data (coordinates not found), create default columns
    if 'lon' not in resultDataframe.columns:
        resultDataframe['lon'] = x
        resultDataframe['lat'] = y
        resultDataframe[variableName] = -99
        resultDataframe['points'] = -99
    
    return resultDataframe


def writeSWATPlusWeather(coordinates_, pointsDataFrame_, pointsDataFrameMin_, extType_, runPeriod_, scenario_, gcm_, region_, currentVariables_, fullVarNames_):

    lat_, lon_, elev_ = coordinates_.split(",")
    lat_ = float(lat_); lon_ = float(lon_); elev_ = float(elev_)

    # print(f"    - filtering and completing data for {coordinates_}")
    pointsDataFrameFiltered = filterAndCompleteDataframe(pointsDataFrame_, coordinates_, runPeriod_[0], runPeriod_[1], currentVariables_[extType_])

    # keep only the date and value columns
    pointsDataFrameFiltered = pointsDataFrameFiltered[['time', currentVariables_[extType_]]]

    if extType_ == "tem":
        pointsDataFrameMinFiltered = filterAndCompleteDataframe(pointsDataFrameMin_, coordinates_, runPeriod_[0], runPeriod_[1], "tasmin")
        pointsDataFrameFiltered['tasmin'] = pointsDataFrameMinFiltered['tasmin']

    pointsDataFrameFiltered['date'] = pandas.to_datetime(pointsDataFrameFiltered['time'])
    pointsDataFrameFiltered['year'] = pointsDataFrameFiltered['date'].dt.year
    pointsDataFrameFiltered['jday'] = pointsDataFrameFiltered['date'].dt.strftime('%j')

    outFileName             = f"../model-data/{region_}/weather/swatplus/{scenario_}/{gcm_}/O{str(coordinates_.split(',')[0]).replace('.','').replace('-','M')}A{str(coordinates_.split(',')[1]).replace('.','').replace('-','M')}.{extType_}"
    uniqueNumberofYears     = len(pointsDataFrameFiltered['date'].dt.year.unique())
    climateHeader           = f"{getFileBaseName(outFileName, extension=True)}: {fullVarNames_[extType_]} climate data for CoSWAT-GM - code by Celray James CHAWANDA\n" + "nbyr     tstep       lat       lon      elev\n"
    
    latStr              = f"{lat_:.2f}"
    lonStr              = f"{lon_:.2f}"
    elevStr             = f"{elev_:.2f}"
    
    climateHeader += f"{str(uniqueNumberofYears).rjust(4)}         0{str(lonStr).rjust(10)}{str(latStr).rjust(10)}{str(elevStr).rjust(10)}\n"

    finalTs = ""
    if extType_ == 'tem':
        df = pointsDataFrameFiltered[['year', 'jday', currentVariables_[extType_], 'tasmin']]
        finalTs = df.to_string(buf=None, columns=None, col_space=[4,6,10, 10], header=False, index=False, na_rep='-99', float_format='%.4f', formatters=None, sparsify=None, index_names=False, justify=None, max_rows=None, max_cols=None, show_dimensions=False, decimal='.', line_width=None, min_rows=None, max_colwidth=None, encoding=None)
    else:
        df = pointsDataFrameFiltered[['year', 'jday', currentVariables_[extType_]]]
        finalTs = df.to_string(buf=None, columns=None, col_space=[4,6,10], header=False, index=False, na_rep='-99', float_format='%.4f', formatters=None, sparsify=None, index_names=False, justify=None, max_rows=None, max_cols=None, show_dimensions=False, decimal='.', line_width=None, min_rows=None, max_colwidth=None, encoding=None)

    climateString = climateHeader + finalTs

    # print(f"\t\t- writing {extType_} data for point {coordinates_}...")
    createPath(os.path.dirname(outFileName))
    writeFile(outFileName, climateString, v = False)
    

    sys.stdout.write("\r\t> wrote {0}\t".format(getFileBaseName(outFileName, extension=True)))
    sys.stdout.flush()

