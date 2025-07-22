<div align="center">

# Brick Sorting Machine

A machine to automatically sort your LEGO® collection

<img src="https://github.com/BrickSortingMachine/BrickSortingMachine-sorter/releases/download/v1.1.0/Overview.jpg" width="600" />

</div>

This project is heavily inspired by numerous preceding LEGO® sorting machines, I'd like to give credit [in this post](https://medium.com/@bricksortingmachine/lego-sorting-machine-overview-d390645759f9). For background information visit the [new blog](https://bricksortingmachine.com), [old blog](https://medium.com/@bricksortingmachine)
or [YouTube channel](https://www.youtube.com/@BrickSortingMachine).

[![GitHub Workflow Status](https://img.shields.io/github/actions/workflow/status/BrickSortingMachine/BrickSortingMachine-sorter/.github/workflows/UnitTest.yml?branch=main&logo=github)](https://github.com/BrickSortingMachine/BrickSortingMachine-sorter/actions)
![Test Statement Coverage](https://gist.githubusercontent.com/BrickSortingMachine/73e31dd0b213908488aa6c4eb07aa92b/raw/8eb6cd341ddd4a77834bb1e51dd76659676dad30/coverage-badge.svg)
[![GitHub release](https://img.shields.io/github/v/release/BrickSortingMachine/BrickSortingMachine-sorter)](https://github.com/BrickSortingMachine/BrickSortingMachine-sorter/releases)
[![GitHub](https://img.shields.io/badge/license-GPLv3-blue)](https://github.com/BrickSortingMachine/BrickSortingMachine-sorter/blob/main/LICENSE)
[![Imports: isort](https://img.shields.io/badge/%20imports-isort-%231674b1)](https://pycqa.github.io/isort/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-black)](https://github.com/psf/black)

## Important Security Note

This software does not do any validation, sanitization or authentication on the network communication. For example in MQTT mode, it fully trusts the broker and all other connected clients to not have any malicious intend. As a result, do not connect this software to a broker or network which you do not fully trust / have under full control. Especially do not connect it to any public MQTT broker. A malicious client connected to the same broker can exploit security vulnerabilities. If this message is not clear please do not use this software.

## Getting Started

If you want to build a LEGO® sorting machine yourself, I suggest to start with the [DIY build instructions](https://github.com/BrickSortingMachine). This repository maintains the sources to operate the LEGO® sorting machine. If you want to work on the machine learning components, the training scripts for the part classifier are maintained [here](https://github.com/BrickSortingMachine/BrickSortingMachine-training).

## Installation
With prerequisites [Python 3.11](https://www.python.org) installed, setup environment:
```
# linux
python -m venv .venv
source .venv/bin/activate
pip install -r requirements_311_linux.txt

# windows
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements_311_win.txt
```
Adapt local config (currently no adaptions needed):
```
cp config.json.example config.json
```
**Work in Progress:** The network communication layer is currently ported to mqtt replacing the previous text based socket communication. As a prerequisite the [mosquitto mqtt broker](https://mosquitto.org/) is needed to be installed.

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
