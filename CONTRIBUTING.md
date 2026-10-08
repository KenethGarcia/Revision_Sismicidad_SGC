# Contributing to _SieveComP_

First, thank you for considering contributing to this project! We welcome contributions from seismologists, developers, and network operators. By participating in this project, you agree to abide by our [Code of Conduct](CODE_OF_CONDUCT.md).

## How to Contribute

### 1. Reporting Bugs
If you find a bug, please open an issue on the [GitHub Issues page](https://github.com/KenethGarcia/SieveComP/issues). When reporting a bug, please include:
* Your operating system and Python version.
* The version of the package you are using.
* A detailed description of the issue.
* A minimal, reproducible example (including a snippet of your TOML config and SQL query, if applicable).
* The full traceback of any errors.

### 2. Suggesting Enhancements
If you have an idea for a new feature, a new TOML rule type, or an enhancement to the Streamlit UI, please submit an issue on GitHub. When suggesting an enhancement, please include:

* A clear and descriptive title.
* A description of the problem you are trying to solve.
* A hypothetical example of how the new feature would be configured or used.

### 3. Contributing Code
We actively welcome pull requests. If you plan to make a significant change, please open an issue first to discuss it with the maintainers.

#### Local Development Setup
1. **Fork the repository** on GitHub.
2. **Clone your fork** locally:
   ```bash
   git clone [https://github.com/YOUR-USERNAME/SieveComP.git](https://github.com/YOUR-USERNAME/SieveComP.git)
   cd SieveComP
3. **Create a virtual environment** (using `mamba`, `conda`, or `venv`) and activate it:
   ```bash
   mamba create -n SieveComP -c conda-forge python=3.10 pandas numpy pymysql shapely pytest
   mamba activate SieveComP
   pip install -e .
   ```
4. **Create a new branch** for your changes:
   ```bash
   git checkout -b my-feature-branch
   ```

### Coding Standards
* Follow [PEP 8](https://www.python.org/dev/peps/pep-0008/) for Python code style.
* Write clear and concise commit messages.
* Ensure all new functions, classes, and methods include comprehensive Python docstrings describing parameters and return types.
* Keep the core execution engine decoupled from the UI/CLI to maintain modularity and testability.

### Testing
We use pytest for unit testing. All new features must include corresponding test cases, and all bug fixes should include a regression test.
- Run the suite of tests to ensure everything is working correctly:
   ```bash
   pytest tests/ -v
   ```
- Ensure that tests involving the database use mocked responses or local test configuration files rather than requiring a live SeisComP connection.

### Submitting a Pull Request

1. Commit your changes with clear, descriptive commit messages.
2. Push your branch to your GitHub fork.
3. Open a Pull Request against the main branch of this repository.
4. Describe your changes in detail in the pull request description and link any relevant open issues.