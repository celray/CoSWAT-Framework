# Model Initialization

## Overview
The initialization process sets up the basic SWAT+ project structure and prepares input files.

## Process Steps
1. Detect subregions (if `subregions.gpkg` exists in model-data)
2. Delete existing model directory for the region
3. Generate `schema.json` connectivity file (subregions only)
4. Run topology preparation (`prepare-topo-parallel.py`)
5. For each subregion (or once for non-subregioned regions):
   - Create project directory structure
   - Copy DEM, landuse, soils rasters
   - Extract template shapefiles from `shapes.dat`
   - Copy burn shape and lakes (clipped by subregion mask)
   - Generate QGIS project file (.qgs)

## Project Structure

**Standard region:**
```
model-setup/CoSWATv{version}/
└── {region}/
    ├── {region}.qgs
    ├── {region}.sqlite
    ├── Watershed/
    │   ├── Rasters/DEM/, Landuse/, Soil/, Landscape/
    │   └── Shapes/
    └── Scenarios/Default/TxtInOut/
```

**With subregions:**
```
model-setup/CoSWATv{version}/
└── {region}/
    ├── schema.json
    ├── regionHRUs.gpkg
    ├── {sub}/
    │   ├── {region}-{sub}.qgs
    │   ├── {region}-{sub}.sqlite
    │   ├── Watershed/
    │   └── Scenarios/
    └── ...
```

The `.qgs` filename uses `{region}-{sub}` (e.g., `africa-save-01-upper-save.qgs`) to ensure valid XML tag names (XML tags cannot start with a digit).

## Subregion-Specific Handling
- **Lakes:** Clipped by subregion mask so only reservoirs within the subregion boundary are included. This prevents QSWAT+ routing errors from cross-boundary reservoirs.
- **Shapefiles:** Burn shape and template shapes are shared (identical DEM), but lakes differ per subregion.
- **schema.json:** Describes which subregions connect to which, with routing point coordinates.

## Key Files
- Project file (.qgs)
- SWAT+ database (.sqlite)
- Configuration files
- Input rasters and shapefiles
- `schema.json` (subregions only)

## Configuration
Key initialization parameters in `datavariables.py`:
```python
final_proj_auth = "ESRI"
final_proj_code = 54003
data_resolution = 500
```

## Related Steps
- [Data Collection](data-collection.md)
- [QSWAT+ Processing](qswat-processing.md)
