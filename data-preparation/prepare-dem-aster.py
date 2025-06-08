#!/bin/python3

import multiprocessing

import requests, sys
from cjfx import *
from osgeo_utils import gdal_merge
import time

ignore_warnings()


# change working directory
me = os.path.realpath(__file__)
os.chdir(os.path.dirname(me))

import datavariables as variables
from resources import login  # a python file with variables
                             # usename (string) and password
                             # (string) for authentication


url = variables.aster_url
base_url = variables.aster_base_url


def download(sess, url_, dst):
    print(f'\ndownloading {url_}' )
    response = sess.get(url_)

    file_data = open(dst, 'wb')
    print(f"\tsaved to {dst}")
    file_data.write(response.content)
    file_data.close()

def progressCallback(complete, message, unknown):
    """Callback function to show gdal.<function> progress."""
    print(f"\r\t> progress: {complete * 100:.1f}%", end='')
    sys.stdout.flush()
    return 1

if __name__ == "__main__":
    if not exists("./resources/regions/"):
        print('! no regions found, creating')
        unzip_file('./resources/regions.zip', './resources/')
    if len(sys.argv) < 2:
        print(f"! select a region for which to prepare the dataset. options are: {', '.join(list_folders('./resources/regions/'))}\n")
        sys.exit()

    regions = sys.argv[1:]
    
    
    print('# preparing dem...')
    download_links = read_from(variables.aster_download_links)
    download_links.sort()
    jobs = []
    # get details

    details = {
        'auth': variables.final_proj_auth,
        'code': variables.final_proj_code,
    }

    create_path(f"{variables.aster_download_tiles_dir}/")

    if variables.redownload_dem:
        with requests.Session() as session:
            session.auth = (login.username, login.password)
            r1 = session.request('get', url)
            r = session.get(r1.url, auth=(login.username, login.password))
            
            if r.ok:
                print('\t> preparing jobs')
                for flink in download_links:
                    flink = flink.strip()
                    if not exists(f'{variables.aster_download_tiles_dir}/{file_name(flink, extension=True)}'):
                        if not exists(f'{variables.aster_remote_tiles_dir}/{file_name(flink, extension=True)}'):
                            jobs.append([session, flink, f'{variables.aster_download_tiles_dir}/{file_name(flink, extension=True)}'])

                pool = multiprocessing.Pool(variables.processes)

                results = pool.starmap_async(download, jobs)
                results.get()
                pool.close()
                pool.join()
            else:
                print('! failed to download data')
                print(f"provide your login data in the 'login.py' file")
                sys.exit()

    # we list all the tiles, conditionally
    local_tiles, remote_tiles = [], []

    local_tiles = list_files(f'{variables.aster_download_tiles_dir}', 'tif')
    remote_tiles = list_files(f'{variables.aster_remote_tiles_dir}', 'tif')

    allTiles = [os.path.abspath(fn) for fn in (local_tiles + remote_tiles)]

    # now we will build a virtual raster file
    if len(allTiles) == 0:
        print('! no tiles found, exiting')
        sys.exit()

    # we then create a vrt
    vrt_output_path = f"{variables.aster_download_tiles_dir}/../global-aster.vrt"
    if not exists(vrt_output_path):
        print(f'\t> creating vrt from tiles')
        vrt = gdal.BuildVRT(vrt_output_path, allTiles, callback=progressCallback, callback_data=None)
        if vrt is None:
            raise RuntimeError("Failed to create VRT")
        vrt = None

    # re-resample
    if variables.re_resample:
        print(f'\n\t> resampling tiles to {variables.data_resolution} m')
        try:
            gdal.Warp(
                variables.aster_tmp_tif, 
                vrt_output_path, 
                dstSRS=f'{variables.final_proj_auth}:{variables.final_proj_code}', 
                xRes=variables.data_resolution, 
                yRes=variables.data_resolution, 
                resampleAlg='bilinear', 
                creationOptions=['COMPRESS=LZW'],
                callback=progressCallback,  
                callback_data=None
            )
        except Exception as e:
            print(f"\t> Error during gdal.Warp: {e}")
            raise

    
    print('\t> subseting raster data')
    for region in regions:
        print(f'\t - processing {region}')
        details['region'] = region
        create_path('../model-data/{region}/raster/'.format(**details))
        ds = gdal.Warp(
                variables.aster_final_raster.format(**details), variables.aster_tmp_tif,
                cropToCutline = True,
                srcNodata=-999, dstNodata=-999, outputType=gdal.GDT_Int16,
                targetAlignedPixels=True,
                dstSRS='{auth}:{code}'.format(**details), 
                xRes=variables.data_resolution, yRes=variables.data_resolution,
                cutlineDSName = variables.cutline.format(**details),
            )
        print(f'\t - {region} done\n')

    ds = None

