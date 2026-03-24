import re, geopandas, os, sys, pandas, platform, math, shutil, sqlite3, zipfile, gzip
import random, string
from ccfx import (createPath, getFileBaseName, writeFile, readFile, formatTimedelta,
                   ignoreWarnings, listFolders, listFiles, listAllFiles, readFrom,
                   writeTo, deleteFile, deletePath, downloadFile, copyFile, exists,
                   alert as ccfx_alert, clipFeatures, resampleRaster, unzipFile, pandas, geopandas)

# snake_case aliases for ccfx functions (backward compat with cjfx callers)
ignore_warnings  = ignoreWarnings
list_folders     = listFolders
list_all_files   = listAllFiles
read_from        = readFrom
delete_file      = deleteFile
delete_path      = deletePath
format_timedelta = formatTimedelta

# these differ from ccfx in defaults or behavior — keep cjfx-compatible versions
def download_file(url, save_path, exists_action='resume', num_connections=5, v=True):
    return downloadFile(url, save_path, exists_action=exists_action, num_connections=num_connections, v=v)

def file_name(path_, extension=True):
    if extension: return os.path.basename(path_)
    return os.path.basename(path_).split(".")[0]

def rand_apha_num(length=8):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))
from datetime import datetime, timedelta
from glob import glob
from shutil import copyfile
import subprocess
try:
    from osgeo import gdal
except: pass
try:
    from shapely.geometry import Polygon
except: pass
try:
    import numpy
except: pass

def runSWATPlus(txtinout_dir, final_dir = os.path.abspath(os.getcwd()),
                executable_path = '', v = True, direct = False, modelName = None):
    os.chdir(txtinout_dir)

    # get the directory name without the whole path
    base_dir = os.path.basename(os.path.normpath(txtinout_dir))

    if direct: os.system(f"{executable_path}")
    else:
        if not v:
            # Run the SWAT+ but ignore output and errors
            subprocess.run([executable_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:

            yrs_line = readFile('time.sim')[2].strip().split()

            yr_from = int(yrs_line[1])
            yr_to = int(yrs_line[3])

            delta = datetime(yr_to, 12, 31) - datetime(yr_from, 1, 1)

            process = subprocess.Popen(executable_path, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)

            counter = 0

            current = 0
            number_of_days = delta.days + 1

            day_cycle = []
            previous_time = None

            while True:
                line = process.stdout.readline()
                line_parts = str(line).strip().split()
                if not "Simulation" in line_parts:
                    if "reading" in line_parts:
                        if v: print(f"\r      > {str(line).strip().replace('b', '')}", end="")

                elif 'Simulation' in line_parts:
                    ref_index = str(line).strip().split().index("Simulation")
                    year = line_parts[ref_index + 3]
                    month = line_parts[ref_index + 1]
                    day = line_parts[ref_index + 2]

                    month = f"0{month}" if int(month) < 10 else month
                    day = f"0{day}" if int(day) < 10 else day

                    current += 1

                    if not previous_time is None:
                        day_cycle.append(datetime.now() - previous_time)

                    if len(day_cycle) > 40:
                        if len(day_cycle) > (7 * 365.25):
                            del day_cycle[0]

                        av_cycle_time = sum(day_cycle, timedelta()) / len(day_cycle)
                        eta = av_cycle_time * (number_of_days - current)

                        eta_str = f" ETA-{format_timedelta(eta)}:"

                    else:
                        eta_str = ''
                    modelNameShow = f"[{modelName}]" if not modelName is None else f""
                    show_progress(current, number_of_days, bar_length=15, string_before=f" ", string_after= f' {modelNameShow} >>  {day}/{month}/{year} end-{yr_to} {eta_str}')

                    previous_time = datetime.now()
                elif "ntdll.dll" in line_parts:
                    print("\n! there was an error running SWAT+\n")
                if counter < 10:
                    counter += 1
                    continue

                if len(line_parts) < 2: break

            show_progress(1, 1, bar_length=15, string_before=f"      ", string_after= f'                                                                                             ')
            print("\n    > SWAT+ simulation complete\n")

    os.chdir(final_dir)


def shouldKeep(baseFn, runPeriod):
    """Determines if a file should be downloaded based on year ranges."""

    start_year, end_year = map(int, runPeriod.split('-'))
    possibleYears = re.findall(r'(?<!\d)(\d{4})(?!\d)', baseFn)

    fileStart, fileEnd = sorted([int(year) for year in possibleYears])
    
    shouldKeepFile = False

    if (start_year <= fileStart <= end_year) or (start_year <= fileEnd <= end_year):
        shouldKeepFile = True

    return shouldKeepFile



def resolveRegion(name, searchDirs=None):
    '''resolve a partial region name (e.g. 'save') to full name (e.g. 'africa-save').
    returns the original name if no unique match found.'''
    if searchDirs is None:
        baseDir = os.path.dirname(os.path.realpath(__file__))
        searchDirs = [
            os.path.join(baseDir, '..', 'model-data'),
            os.path.join(baseDir, 'resources', 'regions'),
        ]
    for d in searchDirs:
        if not os.path.isdir(d): continue
        folders = [f for f in os.listdir(d) if os.path.isdir(os.path.join(d, f))]
        if name in folders: return name
        matches = [f for f in folders if f.endswith(f'-{name}')]
        if len(matches) == 1: return matches[0]
    return name

def resolveRegions(names, searchDirs=None):
    '''resolve a list of region names'''
    return [resolveRegion(n, searchDirs) for n in names]


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
    

    sys.stdout.write("\r\t> wrote {0}         \t".format(getFileBaseName(outFileName, extension=True)))
    sys.stdout.flush()


# ── functions migrated from deprecated cjfx ──────────────────────────────────

def report(string, printing=False):
    if printing:
        print(f"\t> {string}")
    else:
        sys.stdout.write("\r" + string)
        sys.stdout.flush()

def show_progress(progress, end, dt=None, string_before="", string_after="", bar_length=100, precision=1, d_count=None, scroll_text=None):
    if platform.system() != "Windows":
        if (os.get_terminal_size(0)[0] - (len(string_after) + 21)) < bar_length:
            bar_length = os.get_terminal_size(0)[0] - (len(string_after) + 21)

    if bar_length < 5: bar_length = 5

    if not scroll_text is None:
        if platform.system() != "Windows":
            sys.stdout.write('\r' + str(scroll_text).ljust(os.get_terminal_size(0)[0]))
        else:
            sys.stdout.write('\r' + str(scroll_text).ljust(max(151, 0)))
        sys.stdout.flush(); print()

    percent = float(progress) / end
    hashes = "█" * int(round(percent * bar_length))
    spaces = '░' * (bar_length - len(hashes))
    eta = 0
    if dt is not None:
        if len(dt) > 5:
            cycle_time = sum(dt, timedelta()) / (len(dt) if d_count is None else d_count)
            cycles_to_go = end - progress
            eta = formatTimedelta((cycle_time * cycles_to_go))
        else:
            dt = None

    sys.stdout.write("\r{str_b}{bar} {sp}{pct}% {str_after}  ".format(
        str_b=string_before, sp="  " if percent < 100 else "",
        bar=hashes + spaces,
        pct='{:06.2f}'.format(percent * 100),
        str_after=string_after if dt is None else string_after + " - " + "eta: " + eta))
    sys.stdout.flush()

def write_to(filename, text_to_write, v=False, mode="overwrite"):
    try:
        if not os.path.isdir(os.path.dirname(filename)):
            os.makedirs(os.path.dirname(filename))
    except: pass

    if (mode == "overwrite") or (mode == "o"):
        g = open(filename, 'w', encoding="utf-8")
    elif (mode == "append") or (mode == "a"):
        g = open(filename, 'a', encoding="utf-8")
    try:
        g.write(text_to_write)
    except PermissionError:
        print("\t> error writing to {0}, make sure the file is not open in another program".format(filename))
        response = input("\t> continue with the error? (Y/N): ")
        if response == "N" or response == "n": sys.exit()
    g.close
    return filename

def copy_file(filename, destination_path, delete_source=False, v=False, replace=True):
    if not replace:
        if os.path.exists(destination_path): return

    if not os.path.exists(filename):
        if v: print(f"\t> The file you want to copy does not exist: {filename}")
        return

    if not os.path.isdir(os.path.dirname(destination_path)):
        try: os.makedirs(os.path.dirname(destination_path))
        except: pass

    copyfile(filename, destination_path)
    if delete_source:
        try: os.remove(filename)
        except: pass

def create_path(path_name, v=False):
    path_name = os.path.dirname(path_name)
    if path_name == '': path_name = './'
    if not os.path.lexists(path_name):
        os.makedirs(path_name)
        if v: print(f"\t> created path: {path_name}")
    return path_name

def list_files(folder, extension="*"):
    if folder.endswith("/"):
        if extension == "*": list_of_files = glob(folder + "*")
        else: list_of_files = glob(folder + "*." + extension if not extension.startswith(".") else f".{extension}")
    else:
        if extension == "*": list_of_files = glob(folder + "/*")
        else: list_of_files = glob(folder + "/*." + extension if not extension.startswith(".") else f".{extension}")
    return list_of_files

def clip_features(mask, input_feature, output_feature, keep_only_types=None, v=False):
    mask_gdf  = geopandas.read_file(mask)
    input_gdf = geopandas.read_file(input_feature)
    create_path(output_feature)
    out_gdf = input_gdf.clip(mask_gdf.to_crs(input_gdf.crs))
    if not keep_only_types is None:
        out_gdf = out_gdf[out_gdf.geometry.apply(lambda x: x.type in keep_only_types)]
    out_gdf.to_file(output_feature)
    if v: print("\t  - clipped feature to " + output_feature)
    return out_gdf

def resample_raster(original_file, destination_file, resolution, authority="ESRI", auth_code='54003', resampleAlg="Bilinear", data_type="Int16", srcNodata=-32768, dstNodata=-999):
    dtt = {"Byte": gdal.GDT_Byte, "UInt16": gdal.GDT_UInt16, "Int16": gdal.GDT_Int16,
           "UInt32": gdal.GDT_UInt32, "Int32": gdal.GDT_Int32, "Float32": gdal.GDT_Float32, "Float64": gdal.GDT_Float64}
    report(f"\rresampling {original_file}                                             ")
    ds = gdal.Warp(destination_file, original_file, dstSRS=f'{authority}:{auth_code}', resampleAlg=f"{resampleAlg}",
                    srcNodata=srcNodata, dstNodata=dstNodata, outputType=dtt.get(data_type, gdal.GDT_Int16), xRes=resolution, yRes=resolution)
    ds = None
    return True

def alert(message, message_title="info", attachment=None, priority=None, tags=[], server="http://ntfy.chawanda.com", print_it=True, topic="pythonAlerts", v=False):
    import requests
    print(message) if print_it else None; header_data = {}
    if not message_title is None: header_data["Title"] = message_title
    if not priority is None: header_data["Priority"] = priority
    if not len(tags) == 0: header_data["Tags"] = ",".join(tags)
    try:
        if v: print(f"sending alert to {server}/{topic}")
        if not attachment is None:
            header_data["Filename"] = getFileBaseName(attachment)
            requests.put(f"{server}/{topic}", data=open(attachment, 'rb'), headers=header_data)
        try: requests.post(f"{server}/{topic}", data=message, headers=header_data)
        except: pass
    except: pass

def goto_dir(obj_):
    me = os.path.realpath(obj_)
    os.chdir(os.path.dirname(me))

def open_tif_as_array(tif_file, big_tif=True, band=1):
    if big_tif:
        dataset = gdal.Open(tif_file, gdal.GA_ReadOnly)
        band = dataset.GetRasterBand(band)
        return band.ReadAsArray()
    else:
        from PIL import Image
        im = Image.open(tif_file)
        return numpy.array(im)

def create_polygon_geodataframe(lat_list, lon_list, auth='EPSG', code=4326):
    geometry_ = Polygon(zip(lon_list, lat_list))
    polygon = geopandas.GeoDataFrame(index=[0], crs=f"{auth}:{code}", geometry=[geometry_])
    return polygon

def distance(coords_a, coords_b):
    return math.sqrt(((coords_b[0] - coords_a[0]) ** 2) + (coords_b[1] - coords_a[1]) ** 2)

def clip_raster(dstDS, srcDS, cutline):
    if not os.path.isdir(os.path.dirname(dstDS)): os.makedirs(os.path.dirname(dstDS))
    options = gdal.WarpOptions(cutlineLayer=f'{cutline}', multithread=True, cropToCutline=True)
    gdal.Warp(dstDS, srcDS, options=options)
    return True

def set_nodata(input_tif, output_tif, nodata=-999):
    command = f"gdal_translate -of GTiff -a_nodata {nodata} {input_tif} {output_tif}"
    os.system(command)

def unzip_file(f_name, destination_of_contents):
    create_path(f'{destination_of_contents}/{getFileBaseName(f_name, extension=True)[:-3]}')
    if f_name.lower().endswith('.gz'):
        with gzip.open(f_name, 'rb') as f_in:
            with open(f'{destination_of_contents}/{getFileBaseName(f_name, extension=True)[:-3]}', 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)
    else:
        try:
            with zipfile.ZipFile(f_name, "r") as zip_ref:
                zip_ref.extractall(destination_of_contents)
        except: print(f"{f_name} is probably a bad zip file")

def make_plot(data_pd, x_col, y1_cols, y1_axis_label, save_path, title=None, y2_axis_label=None, y2_cols=None,
              x_axis_label=None, y1_labels=None, y2_labels=None, x_limits=None, y1_limits=None, y2_limits=None,
              show_plot=False, legend=False, secondary_type='bar', chart_size=(14, 5)):
    import seaborn
    from matplotlib import pyplot as plt
    plt.close(); plt.margins(x=None, y=None, tight=True); plt.tight_layout(pad=0)
    ax1 = seaborn.set_style(style=None, rc=None)
    fig = plt.figure(figsize=chart_size, dpi=300)
    ax1 = fig.add_subplot(1, 1, 1)

    min_ax1_ini =  1e12; max_ax1_ini = -1e12
    for index in range(0, len(y1_cols)):
        ax1.plot(data_pd[x_col].tolist(), data_pd[y1_cols[index]].tolist(), label=y1_labels[index] if not y1_labels is None else y1_cols[index])
        if min(data_pd[y1_cols[index]].tolist()) < min_ax1_ini: min_ax1_ini = min(data_pd[y1_cols[index]].tolist())
        if max(data_pd[y1_cols[index]].tolist()) > max_ax1_ini: max_ax1_ini = max(data_pd[y1_cols[index]].tolist())

    min_ax1 = max(0, min_ax1_ini - (max_ax1_ini - min_ax1_ini)/5)
    max_ax1 = max_ax1_ini + (max_ax1_ini - min_ax1_ini)/1.2
    min_ax1 = round(min_ax1/10)*10 if min_ax1 < 80 else (round(min_ax1/100)*100 if min_ax1 < 800 else round(min_ax1/1000)*1000)
    if min_ax1 > min_ax1_ini:
        difference_ax1 = round(1 + (min_ax1 - min_ax1_ini)/10) * 10 if (min_ax1 - min_ax1_ini) < 80 else (round(1 + (min_ax1 - min_ax1_ini)/100)*100 if (min_ax1 - min_ax1_ini) < 800 else round(1 + (min_ax1 - min_ax1_ini)/1000)*1000)
        min_ax1 = min_ax1 - difference_ax1
    difference_ax1 = round(1 + (max_ax1 - min_ax1)//10) * 10 if (max_ax1 - min_ax1) < 80 else (round(1 + (max_ax1 - min_ax1)//100)*100 if (max_ax1 - min_ax1) < 800 else round(1 + (max_ax1 - min_ax1)/1000)*1000)
    max_ax1 = min_ax1 + difference_ax1

    ax1.set_ylabel(y1_axis_label)
    if not title is None: ax1.set_title(title, fontdict={'fontsize': 18})
    if not x_axis_label is None: ax1.set_xlabel(x_axis_label)
    if y1_limits is None:
        ax1.set_ylim([min_ax1, max_ax1]); ax1.grid(axis='y', which='major', color='lightgrey')
        ax1.set_yticks([min_ax1 + (i * (max_ax1 - min_ax1) / 5) for i in range(1, 6)])
    else: ax1.set_ylim([y1_limits[0], y1_limits[1]])
    if not x_limits is None: ax1.set_xlim([x_limits[0], x_limits[1]])

    if not y2_cols is None:
        ax2 = ax1.twinx()
        min_ax2_ini = 1e12; max_ax2_ini = -1e12
        if secondary_type == 'bar':
            for index in range(0, len(y2_cols)):
                ax2.bar(data_pd[x_col].tolist(), data_pd[y2_cols[index]].tolist(), 0.6, label=y2_labels[index] if not y2_labels is None else y2_cols[index], color='black')
                if min(data_pd[y2_cols[index]].tolist()) < min_ax2_ini: min_ax2_ini = min(data_pd[y2_cols[index]].tolist())
                if max(data_pd[y2_cols[index]].tolist()) > max_ax2_ini: max_ax2_ini = max(data_pd[y2_cols[index]].tolist())
        elif secondary_type == 'line':
            for index in range(0, len(y2_cols)):
                ax2.plot(data_pd[x_col].tolist(), data_pd[y2_cols[index]].tolist(), label=y2_labels[index] if not y2_labels is None else y2_cols[index])
                if min(data_pd[y2_cols[index]].tolist()) < min_ax2_ini: min_ax2_ini = min(data_pd[y2_cols[index]].tolist())
                if max(data_pd[y2_cols[index]].tolist()) > max_ax2_ini: max_ax2_ini = max(data_pd[y2_cols[index]].tolist())
        if not y2_axis_label is None: ax2.set_ylabel(y2_axis_label)
        min_ax2 = max(0, min_ax2_ini - (max_ax2_ini - min_ax2_ini)/5)
        max_ax2 = max_ax2_ini + (max_ax2_ini - min_ax2_ini)/0.9
        min_ax2 = round(min_ax2/10)*10 if min_ax2 < 80 else (round(min_ax2/100)*100 if min_ax2 < 800 else round(min_ax2/1000)*1000)
        if min_ax2 > min_ax2_ini:
            difference_ax2 = round(1 + (min_ax2 - min_ax2_ini)/10) * 10 if (min_ax2 - min_ax2_ini) < 80 else (round(1 + (min_ax2 - min_ax2_ini)/100)*100 if (min_ax2 - min_ax2_ini) < 800 else round(1 + (min_ax2 - min_ax2_ini)/1000)*1000)
            min_ax2 = min_ax2 - difference_ax2
        difference_ax2 = round(1 + (max_ax2 - min_ax2)//10) * 10 if (max_ax2 - min_ax2) < 80 else (round(1 + (max_ax2 - min_ax2)//100)*100 if (max_ax2 - min_ax2) < 800 else round(1 + (max_ax2 - min_ax2)/1000)*1000)
        max_ax2 = min_ax2 + difference_ax2
        if y2_limits is None:
            ax2.set_yticks([i * (max_ax2 - min_ax2) / 5 for i in range(1, 6)])
            ax2.set_ylim([min_ax2, max_ax2][::-1])
        else: ax2.set_ylim([y2_limits[0], y2_limits[1]][::-1])

    handles, labels = [], []
    for ax in fig.axes:
        for h, l in zip(*ax.get_legend_handles_labels()):
            handles.append(h); labels.append(l)
    if legend: plt.legend(handles, labels, loc="center right")
    plt.savefig(save_path)
    if show_plot: plt.show()
    return plt

class sqlite_connection:
    def __init__(self, sqlite_database, connect=False):
        self.db_name   = sqlite_database
        self.connection = None
        self.cursor     = None
        if connect: self.connect()

    def connect(self, v=True):
        self.connection = sqlite3.connect(self.db_name)
        self.cursor     = self.connection.cursor()
        if v: report("\t-> connection to " + self.db_name + " established...")

    def update_value(self, table_name, col_name, new_value, col_where1, val_1, v=False):
        if not new_value is None:
            new_value = str(new_value)
            self.cursor.execute("UPDATE " + table_name + " SET " + col_name + " = '" + new_value + "' WHERE " + col_where1 + " = " + val_1 + ";")
        if new_value is None:
            self.cursor.execute("UPDATE " + table_name + " SET " + col_name + " = ? WHERE " + col_where1 + " = ?", (new_value, val_1))
        if v: report("\t -> updated {1} value in {0}".format(self.db_name.split("/")[-1].split("\\")[-1], table_name))

    def create_table(self, table_name, initial_field_name, data_type):
        try:
            self.cursor.execute('CREATE TABLE ' + table_name + '(' + initial_field_name + ' ' + data_type + ')')
            report("\t-> created table " + table_name + " in " + self.db_name)
        except: report("\t! table exists")

    def rename_table(self, old_table_name, new_table_name, v=False):
        self.cursor.execute("ALTER TABLE " + old_table_name + " RENAME TO " + new_table_name)
        if v: report("\t-> renamed " + old_table_name + " to " + new_table_name)
        self.commit_changes()

    def table_exists(self, table_name):
        self.cursor.execute("SELECT count(name) FROM sqlite_master WHERE type='table' AND name='{table_name}'".format(table_name=table_name))
        return self.cursor.fetchone()[0] == 1

    def delete_rows(self, table_to_clean, col_where=None, col_where_value=None, v=False):
        if (col_where is None) and (col_where_value is None):
            self.connection.execute("DELETE FROM " + table_to_clean)
        elif (not col_where is None) and (not col_where_value is None):
            self.connection.execute("DELETE FROM " + table_to_clean + " WHERE " + col_where + " = " + col_where_value + ";")
        if v: report("\t-> removed all rows from " + table_to_clean)

    def delete_table(self, table_name):
        self.cursor.execute('DROP TABLE ' + table_name)

    def undo_changes(self):
        self.connection.rollback()
        self.commit_changes()

    def read_table_dict(self, table_name, key_column='id'):
        self.cursor = self.connection.execute(f"SELECT * FROM {table_name}")
        rows = [dict(zip([column[0] for column in self.cursor.description], row)) for row in self.cursor.fetchall()]
        return {row[key_column]: row for row in rows}

    def get_columns_with_types(self, table_name):
        self.cursor.execute(f'PRAGMA table_info({table_name})')
        return {row[1]: row[2] for row in self.cursor.fetchall()}

    def insert_dict_partial(self, table_name, data_dict):
        self.cursor.execute(f"PRAGMA table_info({table_name})")
        columns = [row[1] for row in self.cursor.fetchall()]
        filtered_data = {k: v for k, v in data_dict.items() if k in columns}
        fields = ', '.join(filtered_data.keys())
        placeholders = ', '.join('?' for _ in filtered_data)
        self.cursor.execute(f'INSERT INTO {table_name} ({fields}) VALUES ({placeholders})', list(filtered_data.values()))
        self.commit_changes()

    def create_table_from_dict(self, table_name, columns_with_types):
        fields = ', '.join(f'{column} {data_type}' for column, data_type in columns_with_types.items())
        self.connection.execute(f'CREATE TABLE IF NOT EXISTS {table_name} ({fields})')
        self.commit_changes()

    def insert_dict(self, table_name, data):
        for id, row in data.items():
            fields = ', '.join(row.keys())
            placeholders = ', '.join('?' for _ in row)
            self.cursor.execute(f'INSERT INTO {table_name} ({fields}) VALUES ({placeholders})', list(row.values()))
        self.connection.commit()

    def read_table_columns(self, table_name, column_list="all"):
        if column_list == "all":
            self.cursor = self.connection.execute("SELECT * from " + table_name)
        else:
            self.cursor = self.connection.execute("SELECT " + ",".join(column_list) + " from " + table_name)
        list_of_tuples = [row for row in self.cursor]
        self.cursor = self.connection.cursor()
        return list_of_tuples

    def insert_field(self, table_name, field_name, data_type, to_new_line=False, messages=True):
        self.cursor.execute("alter table " + table_name + " add column " + field_name + " " + data_type)
        if messages:
            if to_new_line: report("\t-> inserted into table {0} field {1}".format(table_name, field_name))
            else:
                sys.stdout.write("\r\t-> inserted into table {0} field {1}            ".format(table_name, field_name))
                sys.stdout.flush()

    def insert_row(self, table_name, ordered_content_list=[], dictionary_obj={}, messages=False):
        if len(ordered_content_list) > 0:
            self.cursor.execute("INSERT INTO " + table_name + " VALUES(" + "'" + "','".join(ordered_content_list) + "'" + ')')
        if len(dictionary_obj) > 0:
            question_marks = ','.join(list('?'*len(dictionary_obj)))
            keys = ','.join(dictionary_obj.keys())
            values = tuple(dictionary_obj.values())
            self.cursor.execute('INSERT INTO '+table_name+' ('+keys+') VALUES ('+question_marks+')', values)
        if messages: report("\t-> inserted row into " + table_name)

    def insert_rows(self, table_name, list_of_tuples, messages=False):
        self.cursor.executemany('INSERT INTO ' + table_name + ' VALUES (?{qmarks})'.format(
            qmarks=",?" * (len(list_of_tuples[0]) - 1)), list_of_tuples)
        if messages: report("\t-> inserted rows into " + table_name)

    def dump_csv(self, table_name, file_name, index=False, v=False):
        tmp_conn = sqlite3.connect(self.db_name)
        df = pandas.read_sql_query("SELECT * FROM {tn}".format(tn=table_name), tmp_conn)
        if index: df.to_csv(file_name)
        else: df.to_csv(file_name, index=False)
        if v: report("\t-> dumped table {0} to {1}".format(table_name, file_name))

    def commit_changes(self, v=False):
        self.connection.commit()
        if v: report("\t-> saved {0} changes to ".format(self.connection.total_changes) + self.db_name)

    def close_connection(self, commit=True):
        if commit: self.commit_changes()
        self.connection.close()
        report("\t-> closed connection to " + self.db_name)

def resample_ts_df(df, column_name, t_step="M", resample_type="mean", only_numeric=True):
    df[column_name] = pandas.to_datetime(df[column_name])
    if resample_type == "mean":
        result_df = df.resample(t_step, on=column_name).mean(numeric_only=only_numeric)
    elif resample_type == "sum":
        result_df = df.resample(t_step, on=column_name).sum(numeric_only=only_numeric)
    else:
        print("\t ! please select a resample type: available > mean, sum")
        sys.exit()
    return result_df

