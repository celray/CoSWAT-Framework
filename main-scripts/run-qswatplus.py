#!/bin/python3

'''
This script runs the COmmunity SWAT+ Model
(CoSWAT-Global) one by one.

Author  : Celray James CHAWANDA
Date    : 14/07/2022
Contact : celray@chawanda.com
Licence : MIT
GitHub  : github.com/celray
'''

import os, sys, platform, math

import shapely
from ccfx import listFolders as list_folders, exists, ignoreWarnings as ignore_warnings, pandas, createPath, deleteFile, writeFile, unzipFile
from coswatFX import goto_dir
from coswatFX import resolveRegions
import sqlalchemy
import geopandas

import os.path
import shutil
import sys
import platform
import warnings
import argparse

ignore_warnings()

if platform.system() == "Linux":
    import pyximport  # importing cython needs this on linux
    pyximport.install()
    ignore_warnings()

# skip deprecation warnings when importing PyQt5
with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    from qgis.core import *
    from qgis.utils import iface
    from PyQt5.QtGui import *
    from PyQt5.QtCore import *

# QgsApplication.setPrefixPath('C:/Program Files/QGIS 3.10/apps/qgis', True)
qgs = QgsApplication([], True)
qgs.initQgis()

goto_dir(__file__)

# Prepare processing framework
if platform.system() == "Windows":
    sys.path.append('{QGIS_Dir}/apps/qgis/python/plugins'.format(
        QGIS_Dir = os.environ['QGIS_Dir'])) # Folder where Processing is located
else:
    sys.path.append('/usr/share/qgis/python/plugins') # Folder where Processing is located

sys.path.append('../data-preparation')
sys.path.append('../main-scripts')

# extract QSWAT+
if not os.path.exists('../data-preparation/resources/QSWATPlus'):
    shutil.unpack_archive('../data-preparation/resources/QSWATPlus.zip', '../data-preparation/resources/')

# skip syntax warnings on linux

with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    from processing.core.Processing import Processing
    Processing.initialize()

    import processing


from shapely.geometry import Point, LineString, MultiLineString

def count_intersections(line, polygon):
    intersection = line.intersection(polygon)
    if isinstance(intersection, Point):
        return 1
    elif isinstance(intersection, (LineString, MultiLineString)):
        return len(intersection.geoms) if hasattr(intersection, 'geoms') else 1
    return 0


class outFX:
    """
    Class to handle output messages. currently dummy
    """
    def __init__(self, message:str, v = False):
        self.message = message
        self.v = v
        self.messageBank = []
        self.write(message)

    def write(self, message: str) -> None:
        """
        Write message to console and log file.
        """
        
        if self.v: print(message)
        self.messageBank.append(message)
    
    def append(self, message: str) -> None:
        """
        Append message to console and log file.
        """
        if self.v: self.write(message)
        self.messageBank.append(message)

    def moveCursor(self, cursor) -> None:
        """
        Move the cursor to a new position in the output.
        """
        pass

    def __call__(self, message: str) -> None:
        """
        Allow the object to be called like a function.
        """
        self.append(message)

    def textColor(self) -> None:
        """
        Set the text color.
        """
        pass

    def setTextColor(self, color) -> None:
        """
        Set the text color.
        """
        pass


import atexit


from resources.QSWATPlus.QSWATPlusMain import QSWATPlus
from resources.QSWATPlus.delineation import Delineation
from resources.QSWATPlus.floodplain import Floodplain
from resources.QSWATPlus.landscape import Landscape
from resources.QSWATPlus.raster import Raster
from resources.QSWATPlus.hrus import HRUs
from resources.QSWATPlus.QSWATUtils import QSWATUtils
from resources.QSWATPlus.parameters import Parameters

import datavariables as variables

from glob import glob

atexit.register(QgsApplication.exitQgis)


details = {
    'auth': variables.final_proj_auth,
    'code': variables.final_proj_code,
}


class DummyInterface(object):
    """Dummy iface to give access to layers."""

    def __getattr__(self, *args, **kwargs):
        """Dummy function."""
        def dummy(*args, **kwargs):
            return self
        return dummy

    def __iter__(self):
        """Dummy function."""
        return self

    def __next__(self):
        """Dummy function."""
        raise StopIteration

    def layers(self):
        """Simulate iface.legendInterface().layers()."""
        return list(QgsProject.instance().mapLayers().values())



if __name__ == '__main__':

    # change working directory
    goto_dir(__file__)

    # create argument parser
    parser = argparse.ArgumentParser(description="a terminal version of QSWAT+ for running the model setup and delineation.")

    parser.add_argument("r", help="the name of the region to run the model for. If not specified, all regions will be processed.", nargs='*', default=[])
    parser.add_argument("--v", help="the version of the model setup to use. If not specified, the datavariables value will be used.", nargs='?', default=None)
    parser.add_argument("--sr", help="subregion id(s) to run. If not specified, all subregions will be processed.", nargs='*', default=None)
    parser.add_argument("--m", help="indicates this is a mannual run", action='store_true')

    args = parser.parse_args()

    # get model setup version
    if args.v is None: version = variables.version
    else: version = args.v

    # get regions
    if len(args.r) > 0: regions = resolveRegions(args.r)
    else: regions = list_folders(f"../model-setup/CoSWATv{version}/")

    if not exists(f"../model-setup/CoSWATv{version}"):
        print(f'\t! the version, CoSWATv{version}, does not exist, the following versions are available:')
        for v in list_folders('../model-setup/'):
            if v.startswith('CoSWATv'):
                print(f'\t\t- {v}')
        print(f'\t> please specify a valid version using the --v argument')
        sys.exit(1)

    print(f"\nregions to run: {', '.join(regions)}")
    print(f"CoSWAT version: {version}")

    for region in regions:
        details['version'] = version
        details['region']  = region

        dataDir     = f'../model-data/{region}'
        schemaFn    = f'../model-setup/CoSWATv{version}/{region}/schema.json'

        # determine project paths (subregions or single region)
        if exists(schemaFn):
            import json, multiprocessing

            with open(schemaFn, 'r') as f:
                schemaData = json.load(f)

            allSubs = schemaData['subregions']

            # filter by --sr if specified
            if args.sr is not None:
                allSubs = [s for s in allSubs if s.split('-')[0] in args.sr]
                if not allSubs:
                    print(f'\t! no matching subregions found for --sr {args.sr}')
                    sys.exit(1)

            print(f'\t> subregions to run: {", ".join(allSubs)}')

            # run subregions in parallel by spawning separate processes
            def runSubregion(subDirName):
                os.system(f'python3 {os.path.realpath(__file__)} {region} --v {version} --sr {subDirName.split("-")[0]}')

            # if called with a single --sr, run it directly below
            # if multiple subregions, spawn parallel processes
            if args.sr is None or len(args.sr) != 1 or len(allSubs) != 1:
                pool = multiprocessing.Pool(int(variables.subregionProcesses))
                pool.map(runSubregion, allSubs)
                pool.close()
                print(f'\n\t> finished all subregions for {region}')
                continue

            # single subregion — resolve paths and fall through to processing
            subDir      = allSubs[0]
            projDir     = f'../model-setup/CoSWATv{version}/{region}/{subDir}'
            qgsName     = f'{region}-{subDir}'
        else:
            subDir      = None
            copiedFromSibling = False
            projDir     = f'../model-setup/CoSWATv{version}/{region}'
            qgsName     = region

        # if this is a subregion, check if a sibling already has TauDEM outputs we can reuse
        if subDir is not None:
            import shutil, glob as globmod
            demPrefix   = f'dem-aster-{variables.final_proj_auth}-{variables.final_proj_code}'
            felCheck    = f'{projDir}/Watershed/Rasters/DEM/{demPrefix}fel.tif'

            copiedFromSibling = False
            if not os.path.exists(felCheck):
                regionBase  = f'../model-setup/CoSWATv{version}/{region}'
                schemaSubs  = schemaData['subregions']

                for siblingDir in schemaSubs:
                    if siblingDir == subDir: continue
                    siblingDemDir   = f'{regionBase}/{siblingDir}/Watershed/Rasters/DEM'
                    siblingFel      = f'{siblingDemDir}/{demPrefix}fel.tif'
                    if os.path.exists(siblingFel):
                        print(f'\t> copying TauDEM outputs from sibling {siblingDir}')
                        dstDemDir = f'{projDir}/Watershed/Rasters/DEM'
                        if os.path.exists(dstDemDir):
                            shutil.rmtree(dstDemDir)
                        shutil.copytree(siblingDemDir, dstDemDir, copy_function=shutil.copy2)

                        siblingShapesDir = f'{regionBase}/{siblingDir}/Watershed/Shapes'
                        dstShapesDir     = f'{projDir}/Watershed/Shapes'
                        for srcFile in globmod.glob(f'{siblingShapesDir}/{demPrefix}*'):
                            shutil.copy2(srcFile, os.path.join(dstShapesDir, os.path.basename(srcFile)))

                        copiedFromSibling = True
                        print(f'\t  - copied DEM rasters and shapefiles from {siblingDir}')
                        break

        print(f'\n\nrunning QSWAT+ for: {projDir} ({version})')
        iface   = DummyInterface()
        plugin  = QSWATPlus(iface)
        dlg     = plugin._odlg

        if not os.path.exists(projDir):
            QSWATUtils.error('Project directory {0} not found'.format(projDir), True)
            sys.exit(1)

        projFile = f"{projDir}/{qgsName}.qgs"

        proj = QgsProject.instance()

        proj.read(projFile)

        plugin.setupProject(proj, True)

        # make connection and load tables
        landuse_table   = f"{dataDir}/tables/worldLanduseLookup.csv"
        soil_table      = f"{dataDir}/tables/worldSoilsLookup.csv"
        user_soil_table = f"{dataDir}/tables/worldSoilsUsersoil.csv"

        landuse_df      = pandas.read_csv(landuse_table, names=["LANDUSE_ID", "SWAT_CODE"], skiprows=1)
        soil_df         = pandas.read_csv(soil_table, names=["SOIL_ID", "NAME"], skiprows=1)
        user_soil_df    = pandas.read_csv(user_soil_table)

        user_soil_df            = user_soil_df.fillna("")
        user_soil_df['SEQN']    = user_soil_df['SEQN'].astype(str)

        db = sqlalchemy.create_engine(f'sqlite:///{projDir}/{qgsName}.sqlite')

        landuse_df.to_sql('landuse_lookup', db, if_exists="replace", index=False)
        soil_df.to_sql('soil_lookup', db, if_exists="replace", index=False)
        user_soil_df.to_sql('usersoil', db, if_exists="replace", index=False, )

        plugin._gv.db.clearTable('BASINSDATA')
        plugin.setupProject(proj, True)

        if not (os.path.exists(plugin._gv.textDir) and os.path.exists(plugin._gv.landuseDir)):
            QSWATUtils.error('Directories not created', True)
            sys.exit(1)

        if not dlg.delinButton.isEnabled():
            QSWATUtils.error('Delineate button not enabled', True)
            sys.exit(1)

        delin = Delineation(plugin._gv, plugin._demIsProcessed)
        delin.init()
        delin._dlg.numProcesses.setValue(variables.taudemProcesses)

        # if rasters were copied from a sibling, let TauDEM skip via timestamp checks
        if subDir is not None and copiedFromSibling:
            delin.thresholdChanged = False

        QSWATUtils.information('DEM: {0}'.format(os.path.split(plugin._gv.demFile)[1]), True)
        delin.addHillshade(plugin._gv.demFile, None, None, None)
        QSWATUtils.information('Inlets/outlets file: {0}'.format(os.path.split(plugin._gv.outletFile)[1]), True)

        if not exists(f"../data-preparation/resources/regions/"):
            print("Extracting regions resources...")
            unzipFile('../data-preparation/resources/regions.zip', '../data-preparation/resources')

        outlets_buffer_gpd  = geopandas.read_file(f"../data-preparation/resources/regions/{region}/outlets-buffer.gpkg").to_crs('{auth}:{code}'.format(**details))

        delin.runTauDEM2(ver = version, reg = region,
            in_outlet_path = os.path.abspath(f'{projDir}/Watershed/Shapes/outlets.shp'),
            Mask_gpd    = outlets_buffer_gpd,
            sel_file    = os.path.abspath(f'{projDir}/Watershed/Shapes/outlets_sel.shp'),
            subDir      = subDir
        )

        lakesShapefn    = os.path.abspath(f'{projDir}/Watershed/Shapes/lakes-grand-{variables.final_proj_auth}-{variables.final_proj_code}.shp')
        rivsShapefn     = os.path.abspath(f'{projDir}/Watershed/Shapes/dem-aster-{variables.final_proj_auth}-{variables.final_proj_code}channel.shp')

        if subDir is not None:
            os.system(f'python3 dodge-vertices.py {region} --v {version} --sr {subDir}')
        else:
            os.system(f'python3 dodge-vertices.py {region} --v {version}')

        if variables.run_flood_plains:
            floodFile = f'{projDir}/Watershed/Rasters/Landscape/Flood/invflood0_00.tif'
            if os.path.exists(floodFile):
                print(f"Floodplain already exists, skipping [{projDir}]")
                plugin._gv.floodFile = os.path.abspath(floodFile)
            else:
                print(f"Running floodplain... [{projDir}]")
                createPath(f'{projDir}/Watershed/Rasters/Landscape/Flood/')
                writeFile(f'{projDir}/Watershed/Rasters/Landscape/Flood/creatingFloodPlain', 'Creating floodplain...\nThis is just an indicator file\nit will be removed when the floodplain is created')
                fxObj           = outFX('Running floodplain...')
                floodPlain      = Floodplain(plugin._gv, fxObj, 1)
                landScape       = Landscape(plugin._gv, fxObj, 1, fxObj)

                landScape.numProcesses  = variables.taudemProcesses
                landScape.clipperFile   = plugin._gv.subbasinsFile

                print(f"   > calculating hillslopes [{projDir}]")
                landScape.calcHillslopes(variables.floodPlainDemInvThres, landScape.clipperFile, proj.layerTreeRoot())

                print(f"   > calculating floodplain [{projDir}]")
                landScape.calcFloodplainParallel(True, proj.layerTreeRoot(), variables.taudemProcesses)
                plugin._gv.floodFile = os.path.abspath(floodFile)

        else:
            print("Floodplains skipped...")

        # NOTE: resolve-lakes-reservoirs.py call removed - to be replaced with improved algorithm

        delin.finishDelineation()
        deleteFile(f'{projDir}/Watershed/Rasters/Landscape/Flood/creatingFloodPlain')

        if not dlg.hrusButton.isEnabled():
            QSWATUtils.error('\t ! HRUs button not enabled', True)
            sys.exit(1)

        hrus = HRUs(plugin._gv, dlg.reportsBox)
        hrus.init()
        hrus._gv.useLandscapes = True
        hrus._dlg.generateFullHRUs.setEnabled(True)
        # hrus._dlg.channelMergeVal.setText(str(5))
        hrus.fullHRUsWanted = True
        hrus.initFloodplain()
        hrus.readFiles()

        if not os.path.exists(QSWATUtils.join(plugin._gv.textDir, Parameters._TOPOREPORT)):
            QSWATUtils.error('\t ! Elevation report not created \n\n\t   Have you run Delineation?\n', True)
            sys.exit(1)

        if not os.path.exists(QSWATUtils.join(plugin._gv.textDir, Parameters._BASINREPORT)):
            QSWATUtils.error('\t ! Landuse and soil report not created', True)
            sys.exit(1)

        hrus.calcHRUs()
        if not os.path.exists(QSWATUtils.join(plugin._gv.textDir, Parameters._HRUSREPORT)):
            QSWATUtils.error('\t ! HRUs report not created', True)
            sys.exit(1)

        if not os.path.exists(QSWATUtils.join(projDir, r'Watershed/Shapes/rivs1.shp')):
            QSWATUtils.error('\t ! Streams shapefile not created', True)
            sys.exit(1)

        if not os.path.exists(QSWATUtils.join(projDir, r'Watershed/Shapes/subs1.shp')):
            QSWATUtils.error('\t ! Subbasins shapefile not created', True)
            sys.exit(1)

        QSWATUtils.information('\t - finished creating HRUs\n', True)
        print()
        print(f'done with running qswat+ for {projDir}', '\nQSWAT+ run complete')

        # update schema.json with channel mappings for routing points
        if subDir is not None and exists(schemaFn):
            import json as jsonmod
            import sqlite3

            subregionsFn    = f'../model-data/{region}/shapes/subregions.gpkg'
            snapFn      = f'{projDir}/Watershed/Shapes/outlets_sel_snap.shp'
            channelFn   = f'{projDir}/Watershed/Shapes/dem-aster-{variables.final_proj_auth}-{variables.final_proj_code}channel.shp'
            rivsFn      = f'{projDir}/Watershed/Shapes/rivs1.shp'
            dbFn        = f'{projDir}/{qgsName}.sqlite'

            if exists(subregionsFn) and exists(snapFn) and exists(channelFn) and exists(dbFn):
                subId   = subDir.split('-')[0]
                ptsGdf  = geopandas.read_file(subregionsFn, layer='points')
                snapGdf = geopandas.read_file(snapFn)
                chGdf   = geopandas.read_file(channelFn)
                rivsGdf = geopandas.read_file(rivsFn) if exists(rivsFn) else None
                db      = sqlite3.connect(dbFn)

                linkToChannel = {}
                if rivsGdf is not None:
                    for _, r in rivsGdf.iterrows():
                        linkToChannel[int(r['LINKNO'])] = int(r['Channel'])

                with open(schemaFn, 'r') as f:
                    schemaData = jsonmod.load(f)

                if 'channelMappings' not in schemaData:
                    schemaData['channelMappings'] = {}

                for _, rp in ptsGdf.iterrows():
                    if rp['OUTLET_MASK'] != subId and rp['INLET_MASK'] != subId:
                        continue

                    role    = 'outlet' if rp['OUTLET_MASK'] == subId else 'inlet'
                    connKey = f"{rp['OUTLET_MASK']}->{rp['INLET_MASK']}"

                    dists       = snapGdf.geometry.distance(rp.geometry)
                    nearest     = snapGdf.loc[dists.idxmin()]
                    snapId      = int(nearest['ID'])

                    matching    = chGdf[chGdf['DSNODEID'] == snapId]
                    linkno      = int(matching.iloc[0]['LINKNO']) if not matching.empty else None

                    # get SWAT channel: from rivs1 for outlets, from gis_routing for inlets
                    channel = linkToChannel.get(linkno, None)
                    if channel is None and role == 'inlet':
                        cur = db.execute(f"SELECT sinkId FROM gis_routing WHERE sourceId = {snapId} AND sourcecat = 'PT' AND sinkcat = 'CH'")
                        row = cur.fetchone()
                        if row: channel = row[0]

                    if connKey not in schemaData['channelMappings']:
                        schemaData['channelMappings'][connKey] = {}

                    schemaData['channelMappings'][connKey][subDir] = {
                        'role':     role,
                        'snapId':   snapId,
                        'channel':  channel,
                    }

                db.close()

                with open(schemaFn, 'w') as f:
                    jsonmod.dump(schemaData, f, indent=4)

                print(f'\t> updated schema.json with channel mappings for {subDir}')

        # update region-level GeoPackages with this subregion's outputs
        if subDir is not None:
            regionBase = f'../model-setup/CoSWATv{version}/{region}'

            hrusFn = f'{projDir}/Watershed/Shapes/hrus2.shp'
            if exists(hrusFn):
                hrusGdf = geopandas.read_file(hrusFn)
                hrusGdf.to_file(f'{regionBase}/regionHRUs.gpkg', layer=subDir, driver='GPKG')
                print(f'\t> updated regionHRUs.gpkg with layer {subDir} ({len(hrusGdf)} features)')

            rivsFn = f'{projDir}/Watershed/Shapes/rivs1.shp'
            if exists(rivsFn):
                rivsGdf = geopandas.read_file(rivsFn)
                rivsGdf.to_file(f'{regionBase}/regionRivs.gpkg', layer=subDir, driver='GPKG')
                print(f'\t> updated regionRivs.gpkg with layer {subDir} ({len(rivsGdf)} features)')

        if args.m:
            answer = input("run SWAT+ Edit for this region? (Y/n): ")
            if answer.lower() in ['y', 'yes', '']:
                if subDir is not None:
                    os.system(f'edit-model.py {region} --m --sr {subDir}')
                else:
                    os.system(f'edit-model.py {region} --m')

