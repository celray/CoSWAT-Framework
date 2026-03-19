# Data Collection Process

## Overview
The data collection step gathers required input data for the SWAT+ model setup process.

## Required Data Types
- Digital Elevation Model (DEM)
- Land Use Data
- Soil Data
- Weather Data
- GRDC Station Data
- Lake and Reservoir Data

## Data Sources
- DEM: ASTER Global DEM
- Land Use: ESA Land Cover
- Soil: FAO Soil Database
- Weather: GSWP3-EWEMBI Dataset
- Hydrology: GRDC Database
- Lakes: GRAND Database

## Configuration
Data collection settings are controlled in `datavariables.py`:
```python
redownload_dem = False
esa_landuse_year = 2011
weather_redownload = False
```

## Process Flow (orchestrated by `get-data.py`)
1. Create bounding boxes and land-mass masks (`make-bounding-boxes.py`)
2. Prepare DEM data (`prepare-dem-aster.py`)
3. Prepare soil data (`prepare-soils.py`)
4. Prepare landuse data (`prepare-landuse.py`)
5. Prepare lake/reservoir data (`prepare-lakes-data.py`) — HydroLAKES v10 + GRanD v1.3 + GLOBathy
6. Prepare weather data (`prepare-weather.py`)
7. Extract GRDC stations (`get-grdc-stations.py`)
8. Copy subregion data if available (`get-subregions.py`)

## Output Structure
```
model-data/
├── {region}/
│   ├── raster/         # DEM, soils, landuse rasters
│   ├── shapes/         # lakes, burn shape, subregions.gpkg (if applicable)
│   ├── tables/         # soil/landuse lookup CSVs
│   └── weather/        # climate data by scenario/model
```

## Subregion Data
If a `subregions.gpkg` file exists in `data-preparation/resources/regions/{region}/`, it is automatically copied to `model-data/{region}/shapes/` during data collection. This file defines how the region is split into subregions for parallel processing. It can be created manually or auto-generated using `partition-region.py`.

## Related Steps
- [Model Initialization](initialization.md)
- [QSWAT+ Processing](qswat-processing.md)
