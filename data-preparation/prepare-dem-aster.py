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



if __name__ == "__main__":

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
    create_path(f"{variables.aster_resampled_dir}/")

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
    if variables.re_resample:
        local_tiles = list_files(f'{variables.aster_download_tiles_dir}', 'tif')
        remote_tiles = list_files(f'{variables.aster_remote_tiles_dir}', 'tif')
    if variables.remerge_dem:
        local_tiles = list_files(f'{variables.aster_download_tiles_dir}', 'tif') if not variables.re_resample else []
        remote_tiles = list_files(f'{variables.aster_remote_tiles_dir}', 'tif') if not variables.re_resample else []


    # create a pool of workers
    pool = multiprocessing.Pool(variables.processes)

    # make jobs
    jobs = []
    
    # re-resample
    if variables.re_resample:
        [delete_file(fn) for fn in list_files(f'{variables.aster_resampled_dir}/')]
        [jobs.append([fn, f"{variables.aster_resampled_dir}/{file_name(fn, extension=True)}", variables.data_resolution]) for fn in local_tiles]
        [jobs.append([fn, f"{variables.aster_resampled_dir}/{file_name(fn, extension=True)}", variables.data_resolution]) for fn in remote_tiles]
    else:
        [jobs.append([fn, f"{variables.aster_resampled_dir}/{file_name(fn, extension=True)}", variables.data_resolution]) for fn in local_tiles if not exists(f"{variables.aster_resampled_dir}/{file_name(fn, extension=True)}")]
        [jobs.append([fn, f"{variables.aster_resampled_dir}/{file_name(fn, extension=True)}", variables.data_resolution]) for fn in remote_tiles if not exists(f"{variables.aster_resampled_dir}/{file_name(fn, extension=True)}")]

    if variables.remerge_dem:
        print(f"\t> resampling {len(jobs)} files"); time.sleep(2)
        results = pool.starmap_async(resample_raster, jobs)
        results.get()

    resampled_dem_files = list_files(f"{variables.aster_resampled_dir}", "tif")   # list files that have been resampled

    pool.close()
    pool.join()

    print('\n\n\t> merging rasters')
    
    if variables.remerge_dem:
        args_ = ['', '-init', '-999', '-o', variables.aster_tmp_tif]
        [args_.append(tif_file) for tif_file in resampled_dem_files]
        gdal_merge.main(args_)
    
    ds = None
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

