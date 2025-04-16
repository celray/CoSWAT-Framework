# CoSWAT Model Setup Script Documentation

## Overview
The setup model script coordinates the setup of the COmmunity SWAT+ Model (CoSWAT-Global). This project provides a community-contributed global SWAT+ model, initiated and led by Celray James CHAWANDA.

## Author Information
- **Author**: Celray James CHAWANDA
- **Contact**: celray@chawanda.com
- **Website**: celray.chawanda.com
- **License**: MIT 2022
- **GitHub**: github.com/celray

## Usage
```bash
python set-up-model.py <version> <get_data> <processes> [regions...]
```

### Parameters
- `version`: Model version (e.g., "0.4.0")
- `get_data`: Download data flag ("y" or "n")
- `processes`: Number of parallel processes
- `regions`: Optional list of specific regions (defaults to all regions in resources)

### Example
```bash
python set-up-model.py 0.4.0 y 10 africa-madagascar
```

## Detailed Process Documentation
Each step of the setup process is documented in detail:

1. [Data Collection](data-collection.md)
   - Input data acquisition
   - Data preprocessing
   - Data validation

2. [Model Initialization](initialization.md)
   - Project structure setup
   - Configuration
   - Database initialization

3. [QSWAT+ Processing](qswat-processing.md)
   - Watershed delineation
   - HRU definition
   - Parameter setup

4. [Model Editing](model-editing.md)
   - Weather data setup
   - Parameter adjustment
   - Model configuration

5. [Model Execution](model-execution.md)
   - Running simulations
   - Progress monitoring
   - Error handling

6. [Model Evaluation](model-evaluation.md)
   - Performance metrics
   - Calibration
   - Validation

7. [Output Mapping](output-mapping.md)
   - Results processing
   - Map generation
   - Visualization

8. [Server Generation](server-generation.md)
   - Web interface files
   - API endpoints
   - Data services

## Configuration
Additional configuration options are available in:
- `./data-preparation/resources/datavariables.py`

## Dependencies
- Python 3.x
- cjfx library
- multiprocessing
- SWAT+ related dependencies

## Error Handling
The script includes progress alerts and error handling for each stage of the setup process. Failed processes will be reported with appropriate error messages.
