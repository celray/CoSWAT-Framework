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

import os, sys, platform, shutil
import sqlite3
from ccfx import listFolders as list_folders, exists, readFrom as read_from, getFileBaseName as file_name, ignoreWarnings as ignore_warnings, pandas, downloadFile as download_file
from coswatFX import write_to, sqlite_connection, list_files, copy_file, show_progress, goto_dir
from coswatFX import resolveRegions
import datavariables as variables
import argparse

ignore_warnings()


def activate_paddy(db_sqlite, paddy_crops):
    if not paddy_crops:
        return

    cursor = db_sqlite.cursor

    # find rice HRUs whose landuse_lum name starts with any paddy crop prefix
    placeholders = " OR ".join([f"l.name LIKE '{crop}%'" for crop in paddy_crops])
    cursor.execute(f"""
        SELECT h.id, h.name, h.hydro_id, l.name as lum_name
        FROM hru_data_hru h
        JOIN landuse_lum l ON h.lu_mgt_id = l.id
        WHERE {placeholders}
    """)
    paddy_hrus = cursor.fetchall()

    if not paddy_hrus:
        print(f'\t> no HRUs found matching paddy crops {paddy_crops}, skipping paddy activation')
        return

    print(f'\t> activating paddy for {len(paddy_hrus)} HRUs matching {paddy_crops}')

    # 1. add paddy irr_ops if they don't exist
    cursor.execute("SELECT COALESCE(MAX(id), 0) FROM irr_ops")
    next_irr_id = cursor.fetchone()[0] + 1

    cursor.execute("SELECT id FROM irr_ops WHERE name = 'ponding90'")
    if cursor.fetchone() is None:
        cursor.execute(
            "INSERT INTO irr_ops (id, name, amt_mm, eff_frac, sumq_frac, dep_sub, salt_ppm, no3_ppm, po4_ppm) VALUES (?, 'ponding90', 90.0, 1.0, 0.0, 60.0, 0.0, 0.0, 0.0)",
            (next_irr_id,))
        next_irr_id += 1

    cursor.execute("SELECT id FROM irr_ops WHERE name = 'ponding_off'")
    if cursor.fetchone() is None:
        cursor.execute(
            "INSERT INTO irr_ops (id, name, amt_mm, eff_frac, sumq_frac, dep_sub, salt_ppm, no3_ppm, po4_ppm) VALUES (?, 'ponding_off', 0.0, 1.0, 0.1, 0.0, 0.0, 0.0, 0.0)",
            (next_irr_id,))

    # 2. add paddy initial condition if it doesn't exist
    cursor.execute("SELECT id FROM initial_res WHERE name = 'initwet2'")
    row = cursor.fetchone()
    if row is None:
        cursor.execute("SELECT id FROM om_water_ini WHERE name = 'no_init'")
        om_row = cursor.fetchone()
        om_id  = om_row[0] if om_row else None

        cursor.execute("SELECT COALESCE(MAX(id), 0) FROM initial_res")
        init_id = cursor.fetchone()[0] + 1
        cursor.execute(
            "INSERT INTO initial_res (id, name, org_min_id) VALUES (?, 'initwet2', ?)",
            (init_id, om_id))
        paddy_init_id = init_id
    else:
        paddy_init_id = row[0]

    # 3. add paddy hydrology_wet entry
    cursor.execute("SELECT id FROM hydrology_wet WHERE name = 'paddy'")
    row = cursor.fetchone()
    if row is None:
        cursor.execute("SELECT COALESCE(MAX(id), 0) FROM hydrology_wet")
        hyd_wet_id = cursor.fetchone()[0] + 1
        cursor.execute("""
            INSERT INTO hydrology_wet (id, name, hru_ps, dp_ps, hru_es, dp_es, k, evap, vol_area_co, vol_dp_a, vol_dp_b, hru_frac)
            VALUES (?, 'paddy', 1.0, 150.0, 1.0, 150.0, 0.5, 0.75, 1.0, 1.0, 1.0, 1.0)
        """, (hyd_wet_id,))
        paddy_hyd_wet_id = hyd_wet_id
    else:
        paddy_hyd_wet_id = row[0]

    # 4. add paddy wetland entry
    cursor.execute("SELECT id FROM wetland_wet WHERE name = 'paddy_wet'")
    row = cursor.fetchone()
    if row is None:
        cursor.execute("SELECT id FROM d_table_dtl WHERE name = 'wetland'")
        rel_row = cursor.fetchone()
        rel_id  = rel_row[0] if rel_row else None

        cursor.execute("SELECT id FROM sediment_res LIMIT 1")
        sed_row = cursor.fetchone()
        sed_id  = sed_row[0] if sed_row else None

        cursor.execute("SELECT id FROM nutrients_res LIMIT 1")
        nut_row = cursor.fetchone()
        nut_id  = nut_row[0] if nut_row else None

        cursor.execute("SELECT COALESCE(MAX(id), 0) FROM wetland_wet")
        wet_id = cursor.fetchone()[0] + 1
        cursor.execute(
            "INSERT INTO wetland_wet (id, name, init_id, hyd_id, rel_id, sed_id, nut_id) VALUES (?, 'paddy_wet', ?, ?, ?, ?, ?)",
            (wet_id, paddy_init_id, paddy_hyd_wet_id, rel_id, sed_id, nut_id))
        paddy_wet_id = wet_id
    else:
        paddy_wet_id = row[0]

    # 5. create paddy landuse_lum entries (one per crop)
    paddy_lum_ids = {}
    for crop in paddy_crops:
        paddy_lum_name = f"{crop}_paddy_lum"
        cursor.execute("SELECT id FROM landuse_lum WHERE name = ?", (paddy_lum_name,))
        row = cursor.fetchone()
        if row is not None:
            paddy_lum_ids[crop] = row[0]
            continue

        # clone from the existing crop's landuse_lum
        cursor.execute("SELECT * FROM landuse_lum WHERE name = ?", (f"{crop}_lum",))
        source = cursor.fetchone()
        if source is None:
            print(f'\t! landuse_lum "{crop}_lum" not found, skipping paddy lum for {crop}')
            continue

        cursor.execute("SELECT COALESCE(MAX(id), 0) FROM landuse_lum")
        new_lum_id = cursor.fetchone()[0] + 1
        cursor.execute("""
            INSERT INTO landuse_lum (id, name, cal_group, plnt_com_id, mgt_id, cn2_id, cons_prac_id, urban_id, urb_ro, ov_mann_id, tile_id, sep_id, vfs_id, grww_id, bmp_id, description)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (new_lum_id, paddy_lum_name, source[2], source[3], source[4], source[5], source[6], source[7], source[8], source[9], source[10], source[11], source[12], source[13], source[14], source[15]))
        paddy_lum_ids[crop] = new_lum_id

    # 6. update HRUs: assign paddy landuse and link to paddy wetland
    for hru_id, hru_name, hydro_id, lum_name in paddy_hrus:
        matched_crop = None
        for crop in paddy_crops:
            if lum_name.startswith(crop):
                matched_crop = crop
                break

        if matched_crop is None or matched_crop not in paddy_lum_ids:
            continue

        cursor.execute(
            "UPDATE hru_data_hru SET lu_mgt_id = ?, surf_stor_id = ? WHERE id = ?",
            (paddy_lum_ids[matched_crop], paddy_wet_id, hru_id))

    # 7. reduce percolation for paddy HRUs
    hydro_ids = [str(h[2]) for h in paddy_hrus]
    if hydro_ids:
        for i in range(0, len(hydro_ids), 500):
            batch = hydro_ids[i:i+500]
            cursor.execute(f"UPDATE hydrology_hyd SET perco = 0.0001 WHERE id IN ({','.join(batch)})")

    db_sqlite.commit_changes()
    print(f'\t> paddy activation complete: {len(paddy_hrus)} HRUs updated')


if __name__ == '__main__':

    # change working directory
    goto_dir(__file__)

    # get model setup version
    parser = argparse.ArgumentParser(description="a terminal script for running the model setup and delineation.")

    parser.add_argument("r", help="the name of the region to run the model for. If not specified, all regions will be processed.", nargs='*', default=[])
    parser.add_argument("--v", help="the version of the model setup to use. If not specified, the datavariables value will be used.", nargs='?', default=None)
    parser.add_argument("--sr", help="subregion directory name", nargs='?', default=None)
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

    for region in regions:

        schemaFn = f'../model-setup/CoSWATv{version}/{region}/schema.json'

        # resolve subregion path from schema.json
        if args.sr is not None and exists(schemaFn):
            import json as jsonmod
            with open(schemaFn, 'r') as f:
                schemaData = jsonmod.load(f)
            subDir   = next((s for s in schemaData['subregions'] if s.split('-')[0] == args.sr), None)
            if subDir is None:
                print(f"\t! subregion {args.sr} not found in schema for {region}")
                continue
            projBase = f'../model-setup/CoSWATv{version}/{region}/{subDir}'
            qgsName  = f'{region}-{subDir}'
        elif exists(schemaFn):
            import json as jsonmod
            with open(schemaFn, 'r') as f:
                schemaData = jsonmod.load(f)
            allSubs = schemaData['subregions']
            print(f"\t> running edit-model for all subregions: {', '.join(allSubs)}")
            for subDir in allSubs:
                srId = subDir.split('-')[0]
                os.system(f'edit-model.py {region} --v {version} --sr {srId}')
            continue
        else:
            projBase = f'../model-setup/CoSWATv{version}/{region}'
            qgsName  = region

        # get observed scenario and gcm, if many, take first hits
        obsScenario = None
        obsDataset  = None

        otherScenarios = {}
        for scenario in variables.weather_pr_links_list:

            if scenario == 'observed':
                obsScenario = scenario
                for gcm in variables.scenariosData[scenario]:
                    if gcm in variables.available_models:
                        obsDataset = gcm
                        break
            else:
                otherScenarios[scenario] = []

                for gcm in variables.scenariosData[scenario]:
                    if gcm in variables.available_models:
                        otherScenarios[scenario].append(gcm)
            

        if obsScenario is None:
            print(f"\t! observed scenario not found for {region}, skipping")
            continue

        if obsDataset is None:
            print(f"\t! observed dataset not found for {region}, skipping")
            continue
        
        # set up api and project variables
        # download weatherGen if it does not exist
        if not exists('../data-preparation/resources/swatplus_wgn.sqlite'):
            
            if not exists('../data-preparation/resources/swatplus_wgn.zip'):
                print('\n\t> downloading weather generator database because it does not exist in your system')
                download_file("https://plus.swat.tamu.edu/downloads/swatplus_wgn.zip", '../data-preparation/resources/swatplus_wgn.zip')

            shutil.unpack_archive('../data-preparation/resources/swatplus_wgn.zip', '../data-preparation/resources/')

        api              = f'../data-preparation/resources/swatplus_api' if platform.system() == "Linux" else None
        project_db       = f'{projBase}/{qgsName}.sqlite'
        datasets_db_file = f'../data-preparation/resources/swatplus_datasets.sqlite'
        weather_dir      = f'../model-data/{region}/weather/swatplus/{obsScenario}/{obsDataset}'
        txtinout_dir     = f'{projBase}/Scenarios/Default/TxtInOut'
        weather_wgn_db   = f'../data-preparation/resources/swatplus_wgn.sqlite'; weather_wgn_db = os.path.abspath(weather_wgn_db)
        editor_version   = f'3.0.8'
        db_sqlite        = sqlite_connection(project_db) 
        db_sqlite.connect()

        print('')

        if not exists(project_db):
            print(f'\t! {region} does not exist in CoSWATv{version}, skipping')
            continue
        
        try:
            cnx = sqlite3.connect(project_db)
            project_info = pandas.read_sql_query("SELECT * FROM project_config", cnx).iloc[0].to_dict()
        except:
            print(f'\t! {region} from CoSWATv{version} cannot be processed, skipping')
            continue
        
        if not project_info['hrus_done'] == 1: 
            print(f'\t! HRUs for {region} (CoSWATv{version}) have not been created, skipping')
            continue
        
        if api is None:
            raise ValueError('API cannot be of type "None", please add api location for SWAT Editor')


        db_sqlite    = sqlite_connection(project_db) 
        db_sqlite.connect()


        db_sqlite.cursor.execute(f"UPDATE project_config SET editor_version = '{editor_version}' WHERE id='1';")

        # update project_config tables based on csv.
        # this is a workaround
        """
        I have patched the swatplus_api's import_gis.py in the function insert_landuse with this:


		# start cjames edit
		import os
		os.system(f'python3 ../data-preparation/swatplus_api_patch.py "{self.project_db_file}"')
		# end cjames edit

        """

        db_sqlite.commit_changes()

        # add column 'netcdf_data_file' to project_config if it does not exist
        try:
            # db_sqlite.cursor.execute("ALTER TABLE project_config ADD COLUMN netcdf_data_file TEXT;")
            db_sqlite.insert_field(table_name='project_config', field_name='netcdf_data_file', data_type='text')
            db_sqlite.connection.commit()
            print(f"\t> added 'netcdf_data_file' column to project_config")
        except Exception as e:
            if "duplicate column" in str(e).lower():
                pass  # Column already exists
            else:
                print(f"\t! warning: could not add netcdf_data_file column: {e}")


        # set up project
        command  = f'setup_project '
        command += f"--project_db_file {project_db} "
        command += f"--delete_existing n "
        command += f"--project_name {region} "

        command += f"--datasets_db_file {datasets_db_file} "
        command += f"--constant_ps n "
        command += f"--is_lte n "
        command += f"--update_project_values n "
        command += f"--reimport_gis n "
        command += f"--editor_version {editor_version} "
        
        os.system(command = f'{api} {command}')

        db_sqlite.cursor.execute(f"UPDATE project_config SET editor_version = '{editor_version}' WHERE id='1';")
        db_sqlite.commit_changes()

        # activate paddy wetlands for rice HRUs
        if hasattr(variables, 'paddy_crop') and variables.paddy_crop:
            activate_paddy(db_sqlite, variables.paddy_crop)

        # import weather
        weather_files_list = list_files(f"{weather_dir}/")
        counter = 0; all = len(weather_files_list)

        if not variables.use_netcdf:
            print(f'\n\t> copying observed weather files')
            for fn in weather_files_list:
                counter += 1; show_progress(counter, all)
                copy_file(fn, f"{txtinout_dir}/{file_name(fn)}", replace=False)
        
        if exists(f"{txtinout_dir}/tmp.cli"):
            os.remove(f"{txtinout_dir}/tmp.cli")
            copy_file(f"{txtinout_dir}/tem.cli", f"{txtinout_dir}/tmp.cli", replace=True)

        db_sqlite.cursor.execute("UPDATE project_config SET weather_data_dir = 'Scenarios/Default/TxtInOut' WHERE id='1';")
        db_sqlite.cursor.execute("UPDATE project_config SET input_files_dir = 'Scenarios/Default/TxtInOut' WHERE id='1';")
        db_sqlite.cursor.execute("UPDATE project_config SET wgn_table_name = 'wgn_cfsr_world' WHERE id='1';")
        db_sqlite.cursor.execute("UPDATE file_cio SET file_name = 'tmp.cli' WHERE id='12';")
        db_sqlite.cursor.execute(f"UPDATE project_config SET wgn_db = '{weather_wgn_db}' WHERE id='1';")
        db_sqlite.commit_changes()

        command  = f'import_weather '

        command += f"--project_db_file {project_db} "
        command += f"--delete_existing y "
        command += f"--create_stations n "
        command += f"--import_type wgn "
        command += f"--editor_version {editor_version} "
        command += f"--import_method database "
        command += f"--wgn_db {weather_wgn_db} "
        command += f"--file1 {weather_wgn_db} "
        command += f"--wgn_table wgn_cfsr_world "

        '''import_weather --project_db_file ../model-setup/CoSWATv2.0.0/RegionName/RegionName.sqlite --delete_existing y --create_stations n --import_type wgn --editor_version 3.0.8 --import_method database --wgn_db ../data-preparation/resources/swatplus_wgn.sqlite --file1 ../data-preparation/resources/swatplus_wgn.sqlite --wgn_table wgn_cfsr_world'''
        os.system(command = f'{api} {command}')


        if not variables.use_netcdf:
            command  = f'import_weather '

            command += f"--project_db_file {project_db} "
            command += f"--delete_existing y "
            command += f"--create_stations y "
            command += f"--import_type observed "
            command += f"--editor_version {editor_version} "
            command += f"--weather_import_format plus "
            command += f"--weather_dir {weather_dir} "

            '''import_weather --project_db_file ../model-setup/CoSWATv2.0.0/RegionName/RegionName.sqlite --delete_existing y --create_stations y --import_type observed --editor_version 3.0.8 --weather_import_format plus --weather_dir ../model-data/RegionName/weather/swatplus/observed/dataset_name'''
            os.system(command = f'{api} {command}')
        else:

            os.system(f"/CoSWAT-Global-Model/data-preparation/resources/nc2stations --hmd 0.01 -i {weather_dir}.nc4 -o {weather_dir}.csv")

            command = f'import_weather '


            command += f"--project_db_file {project_db} "
            command += f"--delete_existing y "
            command += f"--create_stations y "
            command += f"--import_type netcdf "
            command += f"--editor_version {editor_version} "
            command += f"--nc_stations_list {weather_dir}.csv "
            command += f"--nc_file {weather_dir}.nc4 "

            '''import_weather --project_db_file /repositories/ncFiles/africa-save/africa-save.sqlite --delete_existing y --create_stations y --import_type netcdf --editor_version 3.0.8 --nc_stations_list ./stations.csv --nc_file /repositories/ncFiles/africa-save/Scenarios/Default/netcdf/africa-save.nc4'''
            os.system(command = f'{api} {command}')

        # insert object.prt records for subregion outlet channels
        if args.sr is not None and exists(schemaFn) and 'channelMappings' in schemaData:
            db_sqlite.cursor.execute("DELETE FROM object_prt")
            objPrtId = 1
            for connKey, mapping in schemaData['channelMappings'].items():
                if subDir in mapping and mapping[subDir]['role'] == 'outlet':
                    channelNum = mapping[subDir]['channel']
                    toSub      = connKey.split('->')[1]
                    filename   = f'{args.sr}_to_{toSub}_ch{channelNum}.txt'
                    db_sqlite.cursor.execute(
                        "INSERT INTO object_prt (id, ob_typ, ob_typ_no, hyd_typ, filename) VALUES (?, ?, ?, ?, ?)",
                        (objPrtId, 'out', channelNum, 'tot', filename)
                    )
                    objPrtId += 1
                    print(f'\t> object.prt: out {channelNum} -> {filename}')
            db_sqlite.commit_changes()

        # insert recall records for subregion inlet channels (downstream receives upstream flow)
        if args.sr is not None and exists(schemaFn) and 'channelMappings' in schemaData:
            inletRecalls = []
            for connKey, mapping in schemaData['channelMappings'].items():
                if subDir in mapping and mapping[subDir]['role'] == 'inlet':
                    fromSub    = connKey.split('->')[0]
                    channelNum = mapping[subDir]['channel']
                    recName    = f'inlet_from_{fromSub}'
                    inletRecalls.append((recName, channelNum, fromSub))

            if inletRecalls:
                # clean existing inlet recalls for re-run safety
                for recName, _, _ in inletRecalls:
                    db_sqlite.cursor.execute("DELETE FROM recall_con_out WHERE recall_con_id IN (SELECT id FROM recall_con WHERE name = ?)", (recName,))
                    db_sqlite.cursor.execute("DELETE FROM recall_con WHERE name = ?", (recName,))
                    db_sqlite.cursor.execute("DELETE FROM recall_dat WHERE recall_rec_id IN (SELECT id FROM recall_rec WHERE name = ?)", (recName,))
                    db_sqlite.cursor.execute("DELETE FROM recall_rec WHERE name = ?", (recName,))

                # next available IDs
                db_sqlite.cursor.execute("SELECT COALESCE(MAX(id),0) FROM recall_rec");    nextRecId    = db_sqlite.cursor.fetchone()[0] + 1
                db_sqlite.cursor.execute("SELECT COALESCE(MAX(id),0) FROM recall_con");    nextConId    = db_sqlite.cursor.fetchone()[0] + 1
                db_sqlite.cursor.execute("SELECT COALESCE(MAX(id),0) FROM recall_con_out");nextConOutId = db_sqlite.cursor.fetchone()[0] + 1
                db_sqlite.cursor.execute("SELECT COALESCE(MAX(id),0) FROM recall_dat");    nextDatId    = db_sqlite.cursor.fetchone()[0] + 1
                db_sqlite.cursor.execute("SELECT id FROM weather_sta_cli LIMIT 1");        wstId        = db_sqlite.cursor.fetchone()[0]

                for recName, channelNum, fromSub in inletRecalls:
                    # resolve GIS channel number to internal chandeg_con.id
                    db_sqlite.cursor.execute("SELECT id FROM chandeg_con WHERE gis_id = ?", (channelNum,))
                    chaRow = db_sqlite.cursor.fetchone()
                    if chaRow is None:
                        print(f'\t! channel gis_id {channelNum} not found in chandeg_con, skipping {recName}')
                        continue
                    internalChaId = chaRow[0]

                    # recall_rec: daily timestep
                    db_sqlite.cursor.execute(
                        "INSERT INTO recall_rec (id, name, rec_typ) VALUES (?, ?, ?)",
                        (nextRecId, recName, 1)
                    )

                    # recall_dat: sample placeholder (2 days, zeroes) — replaced at runtime
                    for d in range(1, 3):
                        db_sqlite.cursor.execute(
                            """INSERT INTO recall_dat (id, recall_rec_id, jday, mo, day_mo, yr, ob_typ, ob_name,
                               flo, sed, orgn, sedp, no3, solp, chla, nh3, no2, cbod, dox,
                               sand, silt, clay, sag, lag, gravel, tmp)
                               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                            (nextDatId, nextRecId, d, 1, d, 1980, 'pt_day', recName,
                             0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
                             0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
                        )
                        nextDatId += 1

                    # recall_con: connectivity
                    db_sqlite.cursor.execute(
                        "INSERT INTO recall_con (id, name, gis_id, area, lat, lon, elev, wst_id, cst_id, ovfl, rule, rec_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                        (nextConId, recName, channelNum, 0.0, 0.0, 0.0, 0.0, wstId, None, 0, 0, nextRecId)
                    )

                    # recall_con_out: route into inlet channel (uses internal chandeg_con.id, not GIS number)
                    db_sqlite.cursor.execute(
                        'INSERT INTO recall_con_out (id, "order", obj_typ, obj_id, hyd_typ, frac, recall_con_id) VALUES (?, ?, ?, ?, ?, ?, ?)',
                        (nextConOutId, 1, 'sdc', internalChaId, 'tot', 1.0, nextConId)
                    )

                    print(f'\t> recall: {recName} -> sdc {channelNum}')
                    nextRecId    += 1
                    nextConId    += 1
                    nextConOutId += 1

                db_sqlite.commit_changes()

        # write files
        db_sqlite.cursor.execute("UPDATE file_cio SET file_name = 'tem.cli' WHERE id='12';")
        db_sqlite.cursor.execute("UPDATE file_cio SET file_name = 'tem.cli' WHERE id='12';")
        db_sqlite.close_connection()

        command  = f'write_files '
        command += f"--project_db_file {project_db} "

        if exists(f"{txtinout_dir}/tmp.cli"):
            os.remove(f"{txtinout_dir}/tmp.cli")
        
        os.system(command = f'{api} {command}')

        for scen in otherScenarios:
            for gcm in otherScenarios[scen]:
                if not exists(f'../model-data/{region}/weather/swatplus/{scen}/{gcm}'):
                    print(f'\t! {scen} weather data for {gcm} not found, skipping')
                    continue
                f_list = list_files(f'../model-data/{region}/weather/swatplus/{scen}/{gcm}/')

                print(f'\n\t> copying {scen}:{gcm} weather files')
                if not variables.use_netcdf:
                    for fn in f_list:
                        copy_file(fn, f"{txtinout_dir}/{scen}/{gcm}/{file_name(fn)}", replace=True)
                else:
                    # copy the netcdf file
                    copy_file(f'../model-data/{region}/weather/swatplus/{scen}/{gcm}.nc4', f"{txtinout_dir}/{scen}/{gcm}.nc4", replace=True)

        # patch file.cio temperature file name
        cioFile         = f"{txtinout_dir}/file.cio"
        cioFileContents = read_from(cioFile,)

        # modify weather path in file.cio
        # pending

        if args.sr is not None:
            simulationDirectory = f"../../../../../../../simulations/CoSWATv{version}/{region}/{subDir}"
        else:
            simulationDirectory = f"../../../../../../simulations/CoSWATv{version}/{region}"


        cioFileString   = "".join(cioFileContents)

        cioLines = cioFileString.split('\n')
        for i, line in enumerate(cioLines):
            if line.strip().startswith('out_path'):
                cioLines[i] = f'out_path           {simulationDirectory}'
                break
        cioFileString = '\n'.join(cioLines)

        cioFileString = cioFileString.replace('pcp.cli           null', 'pcp.cli           tem.cli')
        write_to(cioFile, cioFileString.replace('tmp.cli', 'tem.cli'))

        print(f'done with editor in {region}', 'SWAT+ Editor run complete')

        print()

        if args.m:
            answer = input("run SWAT+ Model for this region? (Y/n): ")
            if answer.lower() in ['y', 'yes', '']:
                os.system(f'run-model.py {region} --y 1981-1982')
