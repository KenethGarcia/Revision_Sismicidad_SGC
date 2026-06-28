#%% md
# TOML Schema

The new implementation of the seismic revision routine works around a simple idea: The main code will remain untouchable, and the user will be able to define a schema for the input data. The schema will be defined in a TOML file, which is a simple and human-readable format for configuration files. The schema will define the expected structure of the input data, including the required fields, their types, and any constraints on their values. By doing this, the revision routine will be only a TOML file for the future Python package.

## Database configuration

Simple and easy: Define a .env file with the connection content (host, user, password, database) and the code will read it. The .env file should be in the same directory as the main code.

````toml
[database]
env_file = ".env"
````

## Query configuration

You can define a .sql file with the query content and the code will read it. The TOML file only needs to receive the full path to the .sql file using the `sql_file` key.

````toml
[query]
sql_file = "PATH_TO_YOUR_SQL_FILE.sql"
````

## Polygons

You can define a list of polygons in the TOML file. Each polygon should be stored in a file with structure:

```text
# ... header ...
-86.0022144623824,1.45673466814881
-84.7666682,3.049999
-84.3166713,3.5333309
```

And can be referenced in the TOML file like this:

````toml
# ── Polygon files ────────────────────────────────────────────
# Each [[polygons]] entry declares one polygon.
# Required keys:
#   name – identifier used in check rules (must be unique)
#   path – absolute or relative path to the .txt file
#            (relative paths are resolved from this TOML's directory)
# Optional keys:
#   description – human-readable label for documentation/logs
#   skip        – set to true to temporarily disable without deleting the entry

[[polygons]]
name        = "zona1"
path        = "polygons/zona1.txt"
description = "Magnitude zone 1 — MLr_1 region"

[[polygons]]
name        = "zona_experimental"
path        = "polygons/zona_experimental.txt"
description = "Experimental zone — not yet validated"
skip        = true
````

