![Logo](examples/frontend/SGC_logo.png)

**_SieveComP_** is a Python package designed to streamline, automate, and standardize the querying, processing, and filtering of seismic catalog data from SeisComP systems. By leveraging human-readable TOML configuration files, it allows seismological networks to build complex evaluation pipelines without hardcoding logic into scripts. It is distributed under the GNU General Public License Version 3. Please read the complete description of the method and its application in the **publication**.

# Statement of Need

SeisComP is a standard software architecture used by seismological observatories worldwide for real-time earthquake data acquisition and processing. However, integrating SeisComP databases into custom Python workflows often presents a significant bottleneck. Researchers and network operators typically have to manually extract data, write complex, hardcoded SQL queries, and build inflexible scripts to validate event parameters. While robust tools like ObsPy excel at waveform processing and standard FDSN web service interactions, they are not tailored for the complex, relational database-level event filtering and routine quality control checks required by operational networks.

**_SieveComP_** addresses this gap by decoupling the logic from the code. It provides an intuitive engine where users define database connections, SQL queries, spatial polygons, duplicate detection windows, and complex boolean quality-control rules entirely within a TOML file. This allows non-programmers to create strict, reproducible data revision workflows. The package features a robust execution engine capable of dynamically evaluating numeric thresholds, temporal bounds, category matches, and spatial polygon intersections. 

Furthermore, in an AI-accelerated world, this TOML-based approach offers a direct pathway to integrate Artificial Intelligence into SeisComP operations. By abstracting the pipeline into configuration files, it is remarkably easy to build chatbots or agentic AI systems that interact with seismic data. An AI agent can simply read, generate, or modify these human-readable TOML files to execute complex catalog searches and quality control evaluations, all without needing to touch the underlying databases, raw SQL, or Python source code.

Whether running via its high-level Python API or through complex command-line interfaces or frontend applications, **_SieveComP_** significantly reduces the time and programming expertise required to implement rigorous, automated Python workflows in seismological observatories.

# Attribution

If you use this code in a publication, please refer to the package by its name and cite the corresponding JOSS publication (Citation details to be updated upon publication). For any questions, please email Keneth Garcia-Cifuentes ([stivengarcia7113@gmail.com](mailto:stivengarcia7113@gmail.com)) or contact the RSNC team at [radicacioncorrespondencia@sgc.gov.co](https://www.sgc.gov.co/).

# Dependencies and Installation

This repository requires Python 3.12 or higher and depends on core data processing libraries such as `pandas` and `numpy`, and spatial libraries for polygon evaluation. UI frameworks like `click` and `streamlit` are only required if you intend to run the provided examples.

>[!IMPORTANT]
> We strongly recommend installing _SieveComP_ within an isolated virtual environment (using `conda`, `mamba`, or `venv`) to prevent dependency conflicts with system-level packages, especially considering the specific database drivers (e.g., `pymysql`) required.

## Using Mamba/Conda

You can create a new environment and install the package along with its dependencies using the following commands:

```bash
$ mamba create -n sievecomp_env -c conda-forge python=3.10 pandas numpy pymysql shapely pytest
$ mamba activate sievecomp_env
```

## Installation

The package is structured following modern Python packaging standards, allowing for easy installation via `pip`. To install the package, clone the repository and run the following command from the root directory:

```bash
$ git clone https://github.com/KenethGarcia/SieveComP
$ cd SieveComP
$ pip install .
```

# Testing

If you have cloned the complete source code from the GitHub repository, you can verify the installation by running the test suite located in the `tests/` directory. The testing framework for this package is built around `pytest`.

```bash
$ cd SieveComP
$ PYTHONPATH=. pytest tests/ -v
```

You can remove the `PYTHONPATH` variable if you have installed the package in your environment. The tests will validate the core functionality of the package, including database connections, rule evaluations, and output generation.

# Features and Usage

**_SieveComP_**'s core functionality is accessed through its Python API. To demonstrate its flexibility and real-world applicability, the repository also includes advanced integration examples based on the operational workflows at the Colombian Seismological Network (Servicio Geológico Colombiano - RSNC SGC).

## 1. High-Level Python API (Core Package Functionality)

You can integrate the evaluation engine directly into your custom scripts using the `Runner` class. This orchestrates database connections, fetches events, runs spatial/duplicate checks, and outputs a refined DataFrame:

```python
from pathlib import Path
from sievecomp.core.runner import Runner

# 1. Initialize the runner with the example TOML configuration
config_path = Path("examples/data/configs/seismic_revision_routine.toml")
runner = Runner(config_path)

# 2. Execute the pipeline
results = runner.run()

# 3. Access the flagged and filtered events
filtered_events = results.output
print(filtered_events.head())
```

## 2. SGC Real-World Example: Command Line Interface (CLI)

While not part of the core library, the `examples/cli/` directory provides a fully featured CLI script demonstrating how to wrap the package for automated cron jobs or rapid terminal evaluations. Modeled after SGC workflows, it filters events by date or author directly from the command line:

```bash
$ python -m examples.cli.revision_cli \
    --config examples/data/configs/seismic_revision_routine.toml \
    --start "2026-01-01" \
    --end "2026-01-31" \
    --author "gerard" \
    --output
```

This example automatically parses time windows, routes the queries to the correct databases (e.g., splitting between SeisComP3 and SeisComP6), and saves a cleaned CSV. For more details on the CLI usage, refer to the `examples/cli/README.md` file.

## 3. SGC Real-World Example: Streamlit Frontend Application

For analysts and network reviewers, the `examples/frontend/` directory contains a user-friendly web interface built with Streamlit. This demonstrates a high-level customized frontend for operational environments.

```bash
$ pip install streamlit click  # Use this command to install Streamlit if you haven't already
$ streamlit run examples/frontend/app.py
```

From the GUI example, users can visually configure parameters, dynamically toggle active quality checks, interact with the data in Spanish or English, and append reviewed records to a historical log. For more details on the frontend usage, refer to the `examples/frontend/README.md` file.

# Defining Rules in TOML Configuration Files

The core power of the package lies in the TOML schema. You can define logic trees to flag specific seismic conditions without altering any Python code. For example, to flag earthquakes with high RMS and specific depth ranges you can define a rule in the TOML file like this:

```toml
[[checks]]
name = "High RMS Shallow Event"
logic = "and"
event_type = "earthquake"

  [[checks.conditions]]
  rule_type = "numeric"
  column = "quality_standardError"
  mode = "gt"
  threshold = 1.51

  [[checks.conditions]]
  rule_type = "numeric"
  column = "depth_value"
  mode = "between"
  lower = 0.0
  upper = 30.0
```

Please review the [TOML_schema.md](https://github.com/KenethGarcia/SieveComP/blob/bc43d21615a4da4924bb17c22535bfcc576ab08c/docs/TOML_schema.md) and the provided Jupyter Notebooks for comprehensive tutorials on configuring databases, spatial polygons, duplicate tracking, and complex rule evaluation.

# Enhancement and Support

**_SieveComP_** is an open-source package, and community contributions are highly encouraged. Whether you are a seismologist wanting to add new rule types or a developer improving the engine, your input is welcome.

- **Report a bug:** Open an issue on the GitHub repository.
- **Request a feature:** Open an issue or submit a pull request. Submit proposals for new validation rules or UI enhancements via GitHub.
- **Contribute code:** Fork the repository, implement your changes, and submit a pull request. Please follow the existing code style and include tests for new features.

For direct inquiries or academic collaboration, please do not hesitate to contact [Keneth Garcia-Cifuentes](mailto:stivengarcia7113@gmail.com).

# AI Usage Disclosure

In accordance with standard open-source and JOSS transparency guidelines, generative AI tools (including Gemini, Claude, and GPT models) were utilized during the development of this package. AI assistance was scoped to code translation, test scaffolding (`pytest`), CI/CD workflow enhancements, and docstring generation. All core logic, system architecture, and technical tutorials were authored by humans. All AI-assisted outputs were rigorously reviewed and validated by the primary author. For a detailed breakdown of AI usage, please see the [`AI_usage_disclosure.md`](https://github.com/KenethGarcia/SieveComP/blob/d28c453e072ef5dce3791475fd06f69a29790d1e/AI_DISCLOSURE.md) file in the repository.