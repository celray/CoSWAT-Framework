# CoSWAT Global Model (CoSWAT-GM)

A Community SWATplus Global Model that provides a comprehensive hydrological modeling framework.

## Overview
CoSWAT-GM is a community-contributed global SWAT+ model, initiated and led by Celray James CHAWANDA. The framework provides tools for setting up, running, and analyzing SWAT+ models at various scales.

## Quick Start

You will need to install docker. Build the docker using 

```bash
./dockerBuild.sh
```

Then run it
```bash
./dockerRun.sh
```
Now you can set up a model region using this command within the docker. this will set up for specific region(s)

```bash
set-up-model.py <version> <get_data> <processes> [regions...]
```

Example:
```bash
set-up-model.py 0.4.0 y 10 africa-madagascar
```

If you want to set up all global model regions:
```bash
set-up-model.py
```
This will use options defined in the datavariables.py file.

## Documentation
Detailed documentation is available in the `docs` directory:

1. [Model Setup Overview](docs/setup-model.md) - Complete setup process
2. [Data Collection](docs/data-collection.md) - Input data requirements and sources
3. [Model Initialization](docs/initialization.md) - Project structure setup
4. [QSWAT+ Processing](docs/qswat-processing.md) - Watershed and HRU processing
5. [Model Editing](docs/model-editing.md) - Parameter configuration
6. [Output Mapping](docs/output-mapping.md) - Results visualization

## Author
- **Celray James CHAWANDA**
- Email: celray@chawanda.com
- Website: celray.chawanda.com
- GitHub: github.com/celray

## License
MIT License 2022
