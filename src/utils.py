# Author: Garcia-Cifuentes, K. <ORCID:0009-0001-2607-6359>
# This python file represents a new version of the utils.py file used in the revision routine.

import os
import glob
import numpy as np
import pandas as pd
from typing import Union
from colorama import Fore
from shapely.geometry import Point, Polygon

files_available = ('zona_vmm.txt', 'zona3.txt', 'zona2.txt', 'zona_PtoGaitan.txt', 'zona4.txt', 'zona1.txt',
                    'zona5.txt', 'Modelo_Cesar.txt', 'Modelo_CARMA.txt', 'colom_ecu_fro.txt', 'zona_nll.txt')

def model_reader(
        model_folder: str,
        dict_name: dict,
        re_order: bool = False
):
    """
    A function to read the model txt files and return the model points.
    Parameters:
    -----------
    model_folder: str
        Path of the model file.
    dict_name: dict
        Dictionary to store the model points.
    re_order: bool (default=False)
        A flag to reorder the model files, used for the non-volcanic models.
    """
    for filepath in glob.glob(os.path.join(model_folder, "*.txt")):  # Loop over all files in the folder
        df = pd.read_csv(filepath, names=['x', 'y'], skiprows=1)  # Read the file, avoiding the first row (header)
        dict_name[os.path.basename(filepath)] = df.values  # Save the model points in a dictionary
    if re_order:
        ordered_dict = {key: dict_name[key] for key in files_available if key in dict_name}
        dict_name.clear()
        dict_name.update(ordered_dict)
    return None


def inside_the_polygon(
        p: tuple,
        pol_points: Union[list, tuple, np.ndarray, pd.Series],
):
    """
    A function to check if a point is inside a polygon. It works for both volcanic and non-volcanic polygons.
    Parameters:
    -----------
    p: tuple
        Point of the event. (lon, lat)

    pol_points: list of tuples/arrays
        Each tuple indicates one polygon point (lon, lat).

    Returns:
    --------
    True inside
    """
    polygon = Polygon(pol_points)
    point = Point(p)
    return polygon.contains(point)  # Return True if the point is inside the polygon


def correct_df_columns(
        df: pd.DataFrame
):
    """
    A function to correct the columns of the dataframe queried in seiscomp. In particular, this function is designed to
    fix the two repeated columns named 'type'. The second column 'type', corresponding to the magnitude type of the
    event is corrected to 'magnitude_type'.

    Parameters:
    -----------
    df: pandas.Dataframe
        Table queried to be corrected

    Returns:
    --------
    df: pandas.Dataframe
        Corrected table
    """
    if df.columns.duplicated().sum() > 0 and len(df.columns.get_indexer_for(['type'])) > 1:
        indexes = df.columns.get_indexer_for(['type'])
        # Change ONLY the last column name to 'magnitude_type'
        df.columns = df.columns[:indexes[1]].to_list() + ['magnitude_type'] + df.columns[indexes[1]+1:].to_list()
    return df

def inside_bna_polygon(
        p: tuple,
        volcanic_model_dict: dict
):
    """
    A function to check if a point is into any volcanic polygon (OVSMA, OVSPOP, OVSPAS)
    Parameters:
    -----------
    p: tuple
        Point of the event. (lon, lat)

    volcanic_model_dict: dict
        Dictionary containing the volcanic polygons.

    Returns:
    --------
    True if it is inside.
    """
    for volcanic_bna, polygon_txt in volcanic_model_dict.items():
        if inside_the_polygon(p, polygon_txt):
            return True
    return False

def inside_zone_polygon(
        p: tuple,
        model_dict: dict,
        check_models: bool = True
):
    """
    A function to check if a point is inside a zone polygon.

    Parameters:
    -----------
    p: tuple
        Point of the event. (lon,lat)

    model_dict: dict
        Dictionary containing the zone/model polygons.

    check_models: bool (default=True)
        A flag to check if the point is inside any model instead of the RSNC zones.

    Returns:
    --------
    A tuple containing a boolean and the name of the model if it is inside any polygon.
    """
    if check_models:  # If check_models is True, select only the keys in dict containing the word 'Modelo' and 'zona_vmm.txt', 'zona_PtoGaitan.txt'
        model_dict = {k: v for k, v in model_dict.items() if 'Modelo' in k or 'zona_vmm.txt' in k or 'zona_PtoGaitan.txt' in k}
    else:
        model_dict = {k: v for k, v in model_dict.items() if 'Modelo' not in k}
    for model_name, polygon_txt in model_dict.items():
        if inside_the_polygon(p, polygon_txt):
            return True, model_name
    return False, None

def magnitude_check(
        p: tuple,
        magnitude_name: str,
        model_dict: dict
):
    """
    A function to check the magnitude of an event according to the zone and magnitude type.

    Parameters:
    -----------
    p: tuple
        Point of the event. (lon, lat)

    magnitude_name: str
        Name of the magnitude type that the event should have.

    model_dict: dict
        Dictionary containing the zone/model polygons.

    Returns:
    --------
    True if the event is inside the corresponding zone and has the correct magnitude type. Else, a tuple with False and
    the correct magnitude type.
    """
    # Define the association between the zone names and magnitude types
    magnitudes = {'zona1.txt': 'MLr_1', 'zona2.txt': 'MLr_2', 'zona3.txt': 'MLr_3', 'zona4.txt': 'MLr_4',
                  'zona5.txt': 'MLr_5', 'zona_vmm.txt': 'MLr_vmm', 'zona_PtoGaitan.txt': 'MLr_PtoGtn'}
    # Check if the event is inside any zone in RSNC
    zone_results = inside_zone_polygon(p, model_dict, check_models=False)
    # If the event is inside a zone and has the correct magnitude type, return True
    if zone_results[0]:
        if magnitudes[zone_results[1]] == magnitude_name:
            return True, None
    return False, magnitudes[zone_results[1]] if zone_results[0] else None

def printer(
        df: pd.DataFrame,
        p: bool = True,
        f: bool = True
):
    """
    Function to pretty-print the obtained dataframe from the revision routine.

    Parameters:
    -----------
    df: pandas.Dataframe
        Table to be printed.

    p: bool (default=False)
        A flag to print the table in a fancy style or not. It is recommended to set False if your console does not fit
        the table properly.

    f: bool (default=True)
        A flag to indicate if retrieve non-locatable events with 7 or less phase count.

    Returns:
    --------
    None
    """
    # Count how many unique values are in the 'Event ID' column
    unique_ids = df['Event ID'].nunique()

    # Count how many events have the observation: 'Event with 7 or less phase count'
    phase_count_events = df[df['Observations'] == 'Event with 7 or less phase count'].shape[0]

    # Convert error columns to float in order to round them
    df['M'] = pd.to_numeric(df['M'], errors='coerce')
    df['Er depth'] = pd.to_numeric(df['Er depth'], errors='coerce')
    df['Er lat'] = pd.to_numeric(df['Er lat'], errors='coerce')
    df['Er lon'] = pd.to_numeric(df['Er lon'], errors='coerce')

    # Round the columns to 2 decimal places
    df[['M', 'Er depth', 'Er lat', 'Er lon']] = df[['M', 'Er depth', 'Er lat', 'Er lon']].round(2)

    # Change all Nan values to '--' in the table
    df = df.infer_objects(copy=False).fillna('--')

    # From the Region column, remove all the 'Colombia' word at the end of the string, if it exists
    df['Region'] = df['Region'].str.replace(', Colombia', '')

    # Print using a fancy style
    pd.set_option('display.max_rows', None)

    # Print the table
    print(df.to_markdown(tablefmt='fancy_grid', floatfmt='.2f')) if p else print(df)

    print(Fore.RED + f"\nEvents with errors: {unique_ids - phase_count_events}")
    print(Fore.LIGHTBLUE_EX + f"Non locatable events: {phase_count_events}\n") if f else None
    return None

def remove_accents(
        df: pd.DataFrame,
        column: str = 'Region'
):
    """
    Function to remove accents from the Region column of the dataframe.

    Parameters:
    -----------
    df: pandas.Dataframe
        Table with the region names to be corrected.

    column: str (default='Region')
        Column name to be corrected. It is set to 'Region' by default, but it can be changed to any other column.

    Returns:
    --------
    None
    """
    accents = {"Ã¡": "á", "Ã©": "é", "Ã­": "í", "Ã³": "ó", "Ãº": "ú", "Ã±": "ñ", 'Ã\\x81': "Á", 'Ã\\x89': "É",
               'Ã\\x8D': "Í", 'Ã\\x93': "Ó", 'Ã\\x9A': "Ú", 'Ã\\x91': "Ñ", 'Ã\\xAA': "ª", 'Ã\\xB0': "º"}

    # Remove accents from the Region column
    try:
        for acc, char in accents.items():
            df[column] = df[column].str.replace(acc, char)
    except KeyError:
        print(Fore.RED + f"Column '{column}' not found in the dataframe.")
    return None