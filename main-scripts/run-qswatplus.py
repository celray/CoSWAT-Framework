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

import os, sys, platform
from cjfx import list_folders, exists, ignore_warnings, write_to, ignore_warnings, sqlite_connection, list_files, file_name, copy_file, show_progress, goto_dir, pandas, sqlite3
import sqlalchemy
import geopandas

import os.path
import shutil
import sys
import platform
import warnings

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

    # get model setup version
    version = sys.argv[1]

    if not exists(f"../model-setup/CoSWATv{version}"):
        print(f'\t! the version CoSWATv{version} does not exist')
        sys.exit(1)

    # get regions 
    if len(sys.argv) >= 3: regions = sys.argv[2:]
    else: regions = list_folders("../data-preparation/resources/regions/")

    for region in regions:

        iface   = DummyInterface()
        plugin  = QSWATPlus(iface)
        dlg     = plugin._odlg  # useful shorthand for later
        
        projDir = f'../model-setup/CoSWATv{version}/{region}'
        data_dir= f'../model-data/{region}'

        if not os.path.exists(projDir):
            QSWATUtils.error('Project directory {0} not found'.format(projDir), True)
            sys.exit(1)

        projFile = f"{projDir}/{region}.qgs"

        proj = QgsProject.instance()
        
        proj.read(projFile)

        plugin.setupProject(proj, True)

        # make connection and load tables
        landuse_table   = f"{data_dir}/tables/worldLanduseLookup.csv"
        soil_table      = f"{data_dir}/tables/worldSoilsLookup.csv"
        user_soil_table = f"{data_dir}/tables/worldSoilsUsersoil.csv"

        landuse_df      = pandas.read_csv(landuse_table, names=["LANDUSE_ID", "SWAT_CODE"], skiprows=1)
        soil_df         = pandas.read_csv(soil_table, names=["SOIL_ID", "NAME"], skiprows=1)
        user_soil_df    = pandas.read_csv(user_soil_table)

        user_soil_df            = user_soil_df.fillna("")
        user_soil_df['SEQN']    = user_soil_df['SEQN'].astype(str)

        db = sqlalchemy.create_engine(f'sqlite:///{projDir}/{region}.sqlite')

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
        delin._dlg.numProcesses.setValue(1)

        QSWATUtils.information('DEM: {0}'.format(os.path.split(plugin._gv.demFile)[1]), True)
        delin.addHillshade(plugin._gv.demFile, None, None, None)
        QSWATUtils.information('Inlets/outlets file: {0}'.format(os.path.split(plugin._gv.outletFile)[1]), True)

        outlets_buffer_gpd  = geopandas.read_file(f"../data-preparation/resources/regions/{region}/outlets-buffer.gpkg").to_crs('{auth}:{code}'.format(**details))
        
        delin.runTauDEM2(ver = version, reg = region,
            in_outlet_path = os.path.abspath(f'../model-setup/CoSWATv{version}/{region}/Watershed/Shapes/outlets.shp'),
            Mask_gpd    = outlets_buffer_gpd,
            sel_file    = os.path.abspath(f'../model-setup/CoSWATv{version}/{region}/Watershed/Shapes/outlets_sel.shp')
        )

        lakesShapefn    = os.path.abspath(f'../model-setup/CoSWATv{version}/{region}/Watershed/Shapes/lakes-grand-{variables.final_proj_auth}-{variables.final_proj_code}.shp')
        rivsShapefn     = os.path.abspath(f'../model-setup/CoSWATv{version}/{region}/Watershed/Shapes/dem-aster-{variables.final_proj_auth}-{variables.final_proj_code}channel.shp')

        print("Running floodplain...")
        fxObj           = outFX('Running floodplain...')
        floodPlain      = Floodplain(plugin._gv, fxObj, 1)
        landScape       = Landscape(plugin._gv, fxObj, 1, fxObj)

        landScape.clipperFile = plugin._gv.subbasinsFile
        landScape.calcHillslopes(variables.thresholdCh, landScape.clipperFile, proj.layerTreeRoot())

        landScape.calcFloodplain(True, proj.layerTreeRoot())
        plugin._gv.floodFile = os.path.abspath(f'../model-setup/CoSWATv{version}/{region}/Watershed/Rasters/Landscape/Flood/invflood0_00.tif')

        print("Filtering reservoirs...")
        try:
            clippedReservoirs = geopandas.read_file(lakesShapefn)
            streams = geopandas.read_file(rivsShapefn)

            # save a copy of the original reservoirs
            clippedReservoirs.to_file(os.path.abspath(f'../model-setup/CoSWATv{version}/{region}/Watershed/Shapes/lakesOriginal.shp'))
            streams.to_file(os.path.abspath(f'../model-setup/CoSWATv{version}/{region}/Watershed/Shapes/rivsOriginal.shp'))

            # Ensure both datasets are in the same CRS
            if clippedReservoirs.crs != streams.crs:
                streams = streams.to_crs(clippedReservoirs.crs)

            # Perform spatial join to find polygons that intersect with any line in streams
            intersecting = geopandas.sjoin(clippedReservoirs, streams, how="inner", predicate="intersects")

            # Get the indices of intersecting polygons
            intersecting_indices = intersecting.index.unique()

            # Remove the intersecting polygons from clippedReservoirs
            clippedReservoirs = clippedReservoirs[clippedReservoirs.index.isin(intersecting_indices)]

            lakesGDF = clippedReservoirs
            lakes_to_remove = []

            for index, stream in streams.iterrows():
                start_point = Point(stream['geometry'].coords[0])
                end_point = Point(stream['geometry'].coords[-1])
                line = stream['geometry']
                
                for lake_index, lake in lakesGDF.iterrows():
                    if lake.geometry.contains(end_point) and not lake.geometry.contains(start_point):
                        
                        intersections = count_intersections(line, lake.geometry)
                        if intersections >= 2: lakes_to_remove.append(lake_index)

            # Remove the identified lakes
            lakesGDF = lakesGDF.drop(lakes_to_remove)
            lakesGDF.to_file(lakesShapefn)
        except:
            print("Error filtering reservoirs - will not be used in the model")
            raise
            
        delin.finishDelineation()

        if not dlg.hrusButton.isEnabled():
            QSWATUtils.error('\t ! HRUs button not enabled', True)
            sys.exit(1)

        hrus = HRUs(plugin._gv, dlg.reportsBox)
        hrus.init()
        hrus._gv.useLandscapes = True
        hrus._dlg.generateFullHRUs.setEnabled(True)
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
        print(f'done with running qswat+ for region {region}', '\nQSWAT+ run complete')

