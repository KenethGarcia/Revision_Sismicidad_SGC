# Installation

This guide covers the prerequisites and step-by-step instructions to install _PySeisComP_ and its dependencies in an isolated environment.

## Prerequisites

Before installing _PySeisComP_, ensure your system meets the following requirements:

1. **Python:** Version 3.11 or higher. The package relies on the native `tomllib` module introduced in Python 3.11 for parsing configuration files.
2. **Database Access:** Read access to a SeisComP database (MySQL/MariaDB or PostgreSQL) to query event catalogs.
3. **Git:** Required for cloning the repository if you choose to install from source.

## Virtual Environment Setup

We strongly recommend installing _PySeisComP_ inside an isolated virtual environment. This prevents version conflicts with system-level packages, especially regarding database drivers (`PyMySQL`) and spatial libraries (`shapely`).

### Option A: Using `venv` (Standard Library)

Using standard library `venv` is a straightforward way to create a virtual environment. If you prefer to use `venv`, follow these steps:

```bash
# Create the virtual environment
python3 -m venv pyseiscomp_env

# Activate it (Linux/macOS)
source pyseiscomp_env/bin/activate

# Activate it (Windows)
pyseiscomp_env\Scripts\activate
```

### Option B: Using `conda` (Anaconda/Miniconda)

Conda or Mamba handles binary dependencies for spatial libraries seamlessly across operating systems.

```bash
# Create a new environment named 'pyseiscomp_env'
mamba create -n pyseiscomp_env -c conda-forge python=3.11 

# Activate the environment
mamba activate pyseiscomp_env
```

## Installing _PySeisComP_

Currently, _PySeisComP_ is installed directly from the source repository. The package is configured via pyproject.toml to automatically resolve and install all core dependencies (`numpy`, `pandas`, `PyMySQL`, `python-dotenv`, `shapely`, `sqlparse`, and `tqdm`).

1. Clone the repository:

```bash
git clone git@github.com:KenethGarcia/Revision_Sismicidad_SGC.git
cd Revision_Sismicidad_SGC
```

2. Install the core package:

```bash
pip install .
```

## Installing Optional Dependencies

_PySeisComP_ includes advanced examples, such as an interactive Streamlit GUI and a Command Line Interface (CLI), which require additional libraries.

- Install with UI and CLI support:
```bash
pip install .[examples]
```
(This command installs optional dependencies for the examples, including `streamlit` and `click`.)

- Install for Development and Testing:
If you plan to contribute to the code or run the test suite:
```bash
pip install .[dev]
```

- Install Everything (UI, CLI, Development, and Testing):
```bash
pip install .[examples,dev]
```

## Verifying the Installation

To confirm the package and its dependencies are correctly installed and discoverable, run a quick import check from your terminal:

```bash
python -c "import pyseiscomp; print('PySeisComP installed successfully!')"
```

If the command returns the success message without errors, you are ready to set up your configuration files. Proceed to the **TOML Configuration Guide** to learn how to connect your database and define your quality-control rules.