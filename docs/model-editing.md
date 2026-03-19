# Model Editing Process

## Overview
The model editing step configures and prepares the SWAT+ model files, including weather data setup, parameter adjustments, and final TxtInOut directory preparation.

## Process Steps
1. Database Setup
   - Initialize SQLite database
   - Configure project tables
   - Set up weather generator
   - Link to `swatplus_datasets.sqlite`

2. Weather Data Configuration
   - Import weather generator data
   - Process observed weather data
   - Setup climate stations
   - Configure weather lookup tables

3. Model Parameters
   - Land use parameters
   - Soil parameters
   - Channel parameters
   - Basin parameters
   - Management operations

4. Subregion Routing Setup (subregioned models only)
   - **Upstream subregions (outlet role):** inserts `object_prt` record to capture daily channel outflow
   - **Downstream subregions (inlet role):** inserts `recall_rec`, `recall_dat`, `recall_con`, `recall_con_out` records to receive upstream flow as a point source
   - GIS channel numbers from `schema.json` are resolved to internal `chandeg_con.id`
   - Placeholder recall data (2 days, zeroes) is written; replaced with real data at runtime

5. TxtInOut Generation
   - Write model input files (via SWAT+ Editor `write_files`)
   - Configure file.cio
   - For upstream subregions: generates `object.prt` requesting daily outlet channel output
   - For downstream subregions: generates `recall.rec`, `recall.con`, and placeholder `inlet_from_{srId}.rec` data files
   - Setup output variables
   - Validate file structure

## Subregion Support
```bash
edit-model.py africa-save              # loops all subregions automatically
edit-model.py africa-save --sr 01      # specific subregion only
edit-model.py africa-madagascar        # no subregions, runs as before
```

Paths resolve via `schema.json` to `model-setup/CoSWATv{version}/{region}/{subDir}/` with the database at `{region}-{subDir}.sqlite`. Simulation output directory uses an extra `../` to account for the subregion nesting.

## File Structure
```
# Standard region:
model-setup/CoSWATv{version}/{region}/
├── Scenarios/Default/TxtInOut/
└── {region}.sqlite

# With subregions:
model-setup/CoSWATv{version}/{region}/{subDir}/
├── Scenarios/Default/TxtInOut/
└── {region}-{subDir}.sqlite
```

## Weather Files
The following weather files are processed:
- Precipitation (.pcp)
- Temperature (.tmp)
- Relative Humidity (.hmd)
- Solar Radiation (.slr)
- Wind Speed (.wnd)

## Configuration Requirements
```python
# Weather database settings
weather_wgn_db = '../data-preparation/resources/swatplus_wgn.sqlite'
datasets_db = '../data-preparation/resources/swatplus_datasets.sqlite'
weather_dir = '../model-data/{region}/weather/swatplus/observed'
```

## Subregion Routing Details

For subregioned models, `edit-model.py` configures inter-subregion water routing via the SWAT+ recall (point source) system:

**Upstream subregions** (where `channelMappings` role = `outlet`):
- `object_prt` table: entry added for the outlet channel so SWAT+ writes daily hydrograph output (e.g., `01_to_05_ch111.txt`)

**Downstream subregions** (where `channelMappings` role = `inlet`):

| Table | What's inserted |
|---|---|
| `recall_rec` | Daily recall record (e.g., `inlet_from_01`, `rec_typ=1`) |
| `recall_dat` | 2-day placeholder (zeroes) — replaced at runtime by `run-model.py` |
| `recall_con` | Connectivity: links recall to weather station and location |
| `recall_con_out` | Routes recall to inlet channel using internal `chandeg_con.id` (not GIS channel number) |

The SWAT+ Editor's `write_files` then generates `recall.rec`, `recall.con`, and individual `.rec` data files.

## Database Tables Updated
- project_config
- weather_stations
- weather_file_paths
- parameters
- calibration
- climate
- object_prt (upstream subregions)
- recall_rec, recall_dat, recall_con, recall_con_out (downstream subregions)

## Related Documentation
- [Data Collection](data-collection.md) - Input data preparation
- [Model Initialization](initialization.md) - Project setup
- [QSWAT+ Processing](qswat-processing.md) - Watershed processing
- [Model Execution](model-execution.md) - Running the model
- [Model Evaluation](model-evaluation.md) - Performance assessment

## Error Handling
- Weather file validation
- Database integrity checks
- Parameter range validation
- File permission checks

## Output Validation
Before proceeding to model execution:
- Check TxtInOut completeness
- Validate weather data coverage
- Verify parameter ranges
- Test database connections
