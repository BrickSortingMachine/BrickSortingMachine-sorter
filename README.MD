<div align="center">

# Brick Sorting Machine

A machine to automatically sort your LEGO® collection

<img src="doc/Logo.jpeg" width="100" />

</div>

This project is heavily inspired by numerous preceding LEGO® sorting machines, I'd like to give credit [in this post](https://medium.com/@bricksortingmachine/lego-sorting-machine-overview-d390645759f9). For background information visit our [blog](https://medium.com/@bricksortingmachine)
or [YouTube channel](https://www.youtube.com/@BrickSortingMachine).

[![GitHub Workflow Status]( https://img.shields.io/github/actions/workflow/status/BrickSortingMachine/BrickSortingMachine-sorter/build.yaml?branch=main&label=build%20status&logo=github&logoColor=%23dddddd)](https://github.com/BrickSortingMachine/BrickSortingMachine-sorter/actions)
[![GitHub release](https://img.shields.io/github/v/release/BrickSortingMachine/BrickSortingMachine-sorter?include_prereleases)](https://github.com/BrickSortingMachine/BrickSortingMachine-sorter/releases)
[![Code style: black](https://img.shields.io/badge/code%20style-black-black)](https://github.com/psf/black)
[![Imports: isort](https://img.shields.io/badge/%20imports-isort-%231674b1)](https://pycqa.github.io/isort/)
[![GitHub](https://img.shields.io/badge/license-GPLv3-blue)](https://github.com/BrickSortingMachine/BrickSortingMachine-sorter/blob/main/LICENSE)

## Getting Started

If you want to build a LEGO® sorting machine yourself, I suggest to start with the [DIY build instructions](https://github.com/BrickSortingMachine). This repository maintains the sources to operate the LEGO® sorting machine. If you want to work on the machine learning components, the training scripts for the part classifier are maintained [here](https://github.com/BrickSortingMachine/BrickSortingMachine-training).

## Installation
With prerequisites [Python 3.11](https://www.python.org) and [Conda](https://docs.conda.io/projects/miniconda) installed, setup conda environment:
```
./update_environment.sh     # Linux
update_environment_win.bat  # Windows
```

## Usage
Machine controller (on raspberry pi, connected to motor drivers):
```
python sorter.py controller [--disable_machine]
```
Vision service (on alternative PC):
```
python sorter.py vision --host=RASPBERRY_PI_IP_ADDRESS --collect_class=None
```
Classification service (on alternative PC):
```
python sorter.py classification --host=RASPBERRY_PI_IP_ADDRESS --model=models/CLASSIFIER_MODEL.h5
```
Notification service (on alternative PC):
```
python sorter.py notification --host=RASPBERRY_PI_IP_ADDRESS
```


## Development
Install git pre-commit hooks for `flake8`, `black` and `isort` usage:
```
pre-commit install
```

Run unit tests:
```
python -m unittest discover -s test -p "test_*.py"
```

Run static type checking via `mypy` (type hints are still pretty sparse in the code so mypy support is currently limited):
```
python -m mypy sorter.py
```
