# QSWAT+ Processing

## Overview
QSWAT+ processing handles watershed delineation, HRU creation, and model parameter setup. It supports running individual subregions and optimizes multi-subregion runs by reusing DEM-derived outputs.

## Process Steps
1. DEM Processing (TauDEM)
   - Burn-in streams
   - PitFill, D8FlowDir, DinfFlowDir
   - AreaD8, AreaDinf, GridNet
   - Threshold, StreamNet
2. Outlet Creation (`create-outlets.py`, called from within QSWAT+ delineation)
   - Terminal channel endpoints + GRDC station snapping
   - For subregions: clips by mask, adds routing inlet/outlet points
   - Deduplication within 1m
3. Outlet Snapping and Second StreamNet (with outlets)
4. Floodplain Calculation (hillslopes + parallel floodplain)
5. Reservoir Geometry Correction (`dodge-vertices.py`)
6. HRU Definition
   - Land use, soil, slope overlay
   - Full HRU creation
7. Post-processing
   - For subregions: updates `regionHRUs.gpkg` with subregion's `hrus2.shp`

## Subregion Support

### Running Subregions
```bash
run-qswatplus.py <region> --sr 01 02 03    # specific subregions
run-qswatplus.py <region>                   # all subregions (auto-detected from schema.json)
```

### Delineation Optimization
TauDEM steps only depend on the DEM and are identical across subregions. When running multiple subregions:
1. First subregion runs full TauDEM + floodplain
2. DEM rasters, Landscape rasters, and DEM-derived shapefiles are copied to remaining subregions (preserving timestamps)
3. QSWAT+ detects up-to-date outputs and skips TauDEM (goes straight to outlet snapping)
4. Floodplain is skipped if `invflood0_00.tif` already exists
5. Each subsequent subregion only runs: outlet snapping, StreamNet with outlets, HRU creation

### Outlet Handling
For subregions, `create-outlets.py` receives `--sr {subDir}` and:
- Clips outlets by the subregion mask polygon
- Adds routing points from `subregions.gpkg`:
  - `OUTLET_MASK` matches subregion ID -> added as outlet (INLET=0)
  - `INLET_MASK` matches subregion ID -> added as inlet (INLET=1)
- Deduplicates within 1m after adding routing points

## Key Parameters
```python
thresholdSt = 150           # Stream definition threshold (km²)
thresholdCh = 150           # Channel threshold (km²)
channel_snap_thres = 3500   # Snap threshold for channels (m)
subregionProcesses = 3      # Subregions processed in parallel
```

## Output Files
- Stream network (`rivs1.shp`)
- Subbasin map (`subs1.shp`)
- HRU definition (`hrus2.shp`)
- Channel layout (`dem-aster-*channel.shp`)
- Reservoir locations
- `regionHRUs.gpkg` (subregions: merged HRUs with one layer per subregion)

## Related Steps
- [Model Initialization](initialization.md)
- [Model Editing](model-editing.md)
