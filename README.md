![Logo](examples/frontend/SGC_logo.png)

--Package name-- is a Python package designed to streamline, automate, and standardize the querying, processing, and filtering of seismic catalog data from SeisComP systems. By leveraging human-readable TOML configuration files, it allows seismological networks to build complex evaluation pipelines without hardcoding logic into scripts. It is distributed under the GNU General Public License Version 3. Please read the complete description of the method and its application in the **publication**.

# Statement of Need

SeisComP is a standard software architecture used by seismological observatories worldwide for real-time earthquake data acquisition and processing. However, integrating SeisComP databases into custom Python workflows often presents a significant bottleneck. Researchers and network operators typically have to manually extract data, write complex, hardcoded SQL queries, and build inflexible scripts to validate event parameters. While robust tools like ObsPy excel at waveform processing and standard FDSN web service interactions, they are not tailored for the complex, relational database-level event filtering and routine quality control checks required by operational networks.

--Package name-- addresses this gap by decoupling the logic from the code. It provides an intuitive engine where users define database connections, SQL queries, spatial polygons, duplicate detection windows, and complex boolean quality-control rules entirely within a TOML file. This allows non-programmers to create strict, reproducible data revision workflows. The package features a robust execution engine capable of dynamically evaluating numeric thresholds, temporal bounds, category matches, and spatial polygon intersections. 

Furthermore, in an AI-accelerated world, this TOML-based approach offers a direct pathway to integrate Artificial Intelligence into SeisComP operations. By abstracting the pipeline into configuration files, it is remarkably easy to build chatbots or agentic AI systems that interact with seismic data. An AI agent can simply read, generate, or modify these human-readable TOML files to execute complex catalog searches and quality control evaluations, all without needing to touch the underlying databases, raw SQL, or Python source code.

Whether running via its high-level Python API or through complex command-line interfaces or frontend applications, --Package name-- significantly reduces the time and programming expertise required to implement rigorous, automated Python workflows in seismological observatories.

# Attribution

If you use this code in a publication, please refer to the package by its name and cite the corresponding JOSS publication (Citation details to be updated upon publication). For any questions, please email Keneth Garcia-Cifuentes (stivengarcia7113@gmail.com) or contact the RSNC team at [radicacioncorrespondencia@sgc.gov.co](https://www.sgc.gov.co/).

# Dependencies and Installation

This repository requires Python 3.12 or higher and depends on core data processing libraries such as `pandas` and `numpy`. , and spatial libraries for polygon evaluation. UI frameworks like `click` and `streamlit` are only required if you intend to run the provided examples.

>[!IMPORTANT]
> We strongly recommend installing --Package name-- within an isolated virtual environment (using `conda`, `mamba`, or `venv`) to prevent dependency conflicts with system-level packages, especially considering the specific database drivers (e.g., `pymysql`) required.

## Using Mamba/Conda

You can create a new environment and install the package along with its dependencies using the following commands:

```bash
$ mamba create -n package_env -c conda-forge python=3.10 pandas numpy pymysql shapely pytest
$ mamba activate package_env
```

## Installation

The package is structured following modern Python packaging standards, allowing for easy installation via `pip`. To install the package, clone the repository and run the following command from the root directory:

```bash
$ git clone https://github.com/KenethGarcia/Revision_Sismicidad_SGC
$ cd Revision_Sismicidad_SGC
$ pip install .
```

# Testing

If you have cloned the complete source code from the GitHub repository, you can verify the installation by running the test suite located in the `tests/` directory. The testing framework for this package is built around `pytest`.

```bash
$ cd Revision_Sismicidad_SGC
$ pytest tests/ -v
```



