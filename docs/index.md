# _SieveComP_: Automated Seismic Catalog Evaluation

**_SieveComP_** is a robust Python package designed to streamline, automate, and standardize the querying, processing, and filtering of seismic catalog data from SeisComP systems.

By leveraging human-readable TOML configuration files, _SieveComP_ decouples complex filtering logic from source code. This empowers seismological networks, researchers, and data analysts to build strict, reproducible quality-control pipelines without needing to write hardcoded SQL queries or complex Python evaluation scripts.

## Why _SieveComP_?

Integrating SeisComP relational databases into custom Python workflows typically presents a significant bottleneck. Researchers and network operators often resort to manually extracting data, writing complex SQL queries, and building inflexible scripts to validate event parameters.

_SieveComP_ bridges this gap. It provides a list of intuitive rules engine where users define database connections, queries, spatial polygons, duplicate detection windows, and complex boolean quality-control rules entirely within a TOML file. Whether you are running an automated cron job or conducting an interactive review, _SieveComP_ ensures your data validation is consistent, scalable, and easy to maintain.

## Core Features

- **No-Code Rules Engine:** Define complex logical trees (AND, OR, XOR) using a simple TOML schema to evaluate numeric thresholds, categories, temporal bounds, and column-to-column relations.
- **Spatial Polygon Filtering:** Automatically check if events fall inside or outside defined geographic regions using standard polygon files (BNA or GeoJSON).
- **Advanced Duplicate Detection:** Identify duplicate seismic events across catalogs using adjacent event tracking or a Sorted Slicing Window Approach (SSWA) based on time and distance thresholds.
- **Database Abstraction Layer:** Seamlessly connect to and query single or multiple SeisComP databases (e.g., handling transitions between SeisComP versions) using secure environment variables.
- **Flexible Interfaces:** Run and connect your evaluations through a command-line interface (CLI), Python API, or Jupyter Notebook for interactive analysis.

## Documentation Overview

The _SieveComP_ documentation is structured to provide a comprehensive understanding of the package's capabilities, installation procedures, and usage examples. The following sections are included:

- **Installation Guide:** Step-by-step instructions for setting up your environment, installing the core library, and adding optional dependencies for the UI and CLI examples.
- **TOML Configuration Guide:** The comprehensive manual on how to structure your TOML files, define databases, set up spatial polygons, and build your quality-control rules.
- **Tutorials:** Applied examples showing how to use SieveComP across its different interfaces:
    - **Command-Line Interface (CLI):** Learn how to run evaluations directly from the terminal.
    - **Python API:** Explore how to integrate SieveComP into your Python scripts for programmatic access.
    - **Jupyter Notebook:** Interactive tutorials demonstrating real-world use cases and data analysis workflows.
- **Reference Documentation:** Detailed descriptions of all classes, methods, and functions available in the _SieveComP_ package.

## Getting Help & Contributing

SieveComP is an open-source project. If you encounter bugs, have feature requests, or want to contribute, please visit our [GitHub repository](https://github.com/KenethGarcia/SieveComP) to submit issues or pull requests. We welcome contributions from the community to enhance the functionality and usability of the package.