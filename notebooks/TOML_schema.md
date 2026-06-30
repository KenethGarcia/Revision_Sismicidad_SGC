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

## Conditions

Probably one of the most important parts of the schema is the definition of conditions. Conditions are used to define rules that the input data must satisfy. Each condition will have a name, a description, and a set of rules that define the expected values for the fields in the input data.

The idea behind the TOML configuration is the use of nested arrays of tables to express the rules cleanly. Each condition will be defined as an array of tables, where each table represents a rule. The rules will be defined using a simple syntax that allows the user to specify the field name, the expected value, and any constraints on the value.

Think of every check as a tree of logic nodes, where each node is a condition and the leaves are the rules that define the expected values for the fields in the input data. A check is defined using the `[[checks]]` syntax, and each group of rules is defined using the `[[checks.groups]]` syntax. Finally, each condition is defined using the `[[checks.conditions]]` syntax.

> **NOTE:** In the IA world, you can just pass this tutorial to a LLM and ask it to generate the TOML file for you. The LLM will be able to understand the structure of the TOML file and generate the appropriate syntax for the rules.


### Root node: `[[checks]]`
In the root node, it is required to define:

- `name`: label for the rule, used in the output or logs.
- `logic`: boolean operator that joins all direct children of the root. Options are `and`, `or` or `xor`.

And it is optional to define:

- `description`: human-readable label for documentation/logs.
- `event_type`: the type of event that the check applies to. If not defined, the check will apply to all events. It should be a string or an array of strings. The event type is used to filter the input data before applying the check.

### Group node: `[[checks.groups]]`
In the group node, it is required to define:

- `logic`: boolean operator that joins all direct children of the group. Options are `and`, `or` or `xor`.

and it is optional to define:

- `description`: human-readable label for documentation/logs.
- `name`: label for the group, used in the output or logs.

### Condition node: `[[checks.conditions]]`
In the condition node, it is required to define:

- `rule_type`: the type of rule that will be applied. Options are `numeric`, `category`, `temporal`, `polygon`, `column_column`.
- `column`: the name of the column in the input data that the rule will be applied to.
- `mode`: operator for the rule. It depends on the `rule_type`. See below for more details.
- Additional parameters that depend on the `rule_type` and `mode`. See below for more details.

## Condition types

This section summarizes the available condition types and their required parameters. Each condition type has its own set of parameters that must be defined in order to create a valid rule.

### Numeric rules
Defined as a numeric comparison between the value of the column and a threshold. The available modes are:
1. `gt`: greater than
2. `lt`: less than
3. `ge`: greater than or equal to
4. `le`: less than or equal to
5. `eq`: equal to
6. `ne`: not equal to
7. `between`: between two values (inclusive)
8. `outside`: outside two values (exclusive)
9. `abs_gt`: absolute value greater than
10. `abs_ge`: absolute value greater than or equal to

Moreover, it is required to define:
- `threshold`: the threshold value for the comparison. Valid for one-side comparisons.
- `lower`, `upper`: the lower and upper bounds for the comparison. Valid for two-side comparisons (`between` and `outside`).

### Column-Column rules
Defined as a comparison between the values of two columns. It follows the general formula:

$$ events[left col] \quad  (mode) \quad factor * events[right col] + offset$$

The available modes are:
1. `gt`: greater than
2. `lt`: less than
3. `ge`: greater than or equal to
4. `le`: less than or equal to
5. `eq`: equal to
6. `ne`: not equal to

Moreover, it is required to define:
- `left_col`: the name of the left column in the input data that the rule will be applied to.
- `right_col`: the name of the right column in the input data that the rule will be applied to.

And it is optional to define:
- `factor`: a multiplier for the right column. Default is 1.0.
- `offset`: an offset for the right column. Default is 0.0.

### Non-numeric rules
Defined as search for a value in a list of categories. The available modes are:
1. `in`: the value is in the list of categories
2. `not_in`: the value is not in the list of categories
3. `is_null`: the value is null
4. `is_not_null`: the value is not null

It is required to define:
- `column`: the name of the column in the input data that the rule will be applied to.

And if the mode is `in` or `not_in`, it is also required to define:
- `values`: a list of categories that the column will be compared to.

### Polygon rules
Defined as a check if the value of the column is inside or outside a polygon. The available modes are:
1. `inside`: the value is inside the polygon
2. `outside`: the value is outside the polygon

It is required to define:
- `lat_col`: the name of the column in the input data that contains the latitude values.
- `lon_col`: the name of the column in the input data that contains the longitude values.
- `polygon`: the name of the polygon that will be used for the check. The polygon must be defined in the `[[polygons]]` section of the TOML file.

### Temporal rules
Defined as a numeric comparison between the value of the column and a threshold, but the value is expected to be a timestamp. The available modes are:
- `gt`: greater than
- `lt`: less than
- `ge`: greater than or equal to
- `le`: less than or equal to
- `eq`: equal to
- `ne`: not equal to

It is required to define:
- `column`: the name of the column in the input data that the rule will be applied to.
- `value`: the threshold value for the comparison. The value must be a valid timestamp in the `pandas.Timestamp` class (i.e., '2024-01-01T00:00:00Z' or '2024-01-01 00:00:00').

## How to define your own conditions

The strategy to define conditions is to first set the condition as a boolean operation and after that set the rules that will be applied to the input data. Please review the following examples before continue reading the rest of the documentation:

1. A simple check with a single condition:

````toml
[[checks]]
````toml
