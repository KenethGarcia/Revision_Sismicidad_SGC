# Author: Garcia-Cifuentes, K. <ORCID:0009-0001-2607-6359>
# This file contains the seismic revision routine for the RSNC catalog.

import os
import sys
import json
import time
import argparse
import pymysql
import warnings
import numpy as np
import pandas as pd
import datetime as dt
import haversine as hs
import importlib.util
import multiprocessing
import concurrent.futures
from tqdm import tqdm, trange
from typing import Union
from colorama import init, Fore

########################################################################################################################
# Import utils wherever if the executed .py file is outside the src folder
file_path = os.path.join(os.path.dirname(__file__), 'utils.py') # Location of utils.py

# Load the module as 'ut' in order to avoid conflicts with the 'utils' name
spec = importlib.util.spec_from_file_location("ut", file_path)
ut = importlib.util.module_from_spec(spec)
sys.modules["ut"] = ut
spec.loader.exec_module(ut)
########################################################################################################################

# Force the spawn method to avoid issues with the 'fork' method, avoiding deadlocks in the code
multiprocessing.set_start_method('spawn', force=True)

# Initialize colorama, avoiding manually reset the text color each time
init(autoreset=True)

# Define columns where we will extract the information
columns = ['time_value', 'publicID', 'text', 'depth_value', 'magnitude_value', 'magnitude_type',
           'quality_standardError', 'depth_uncertainty', 'latitude_uncertainty', 'longitude_uncertainty',
           'quality_associatedPhaseCount', 'creationInfo_author', 'type', 'creationInfo_agencyID']
# Columns for the resulting table printed/saved
result_columns = ['Date', 'Event ID', 'Region', 'Depth', 'M', 'M type', 'RMS', 'Er depth', 'Er lat', 'Er lon', 'Phases',
                  'Author', 'Type', 'Agency', 'Observations']

# Read the model file for both regular, volcanic and special zones
volcanic_data = {}
zone_data = {}
special_data = {}
model_folder = os.path.join(os.path.dirname(os.path.dirname(__file__)), "model_files")
bna_folder = os.path.join(os.path.dirname(os.path.dirname(__file__)), "bna_volcanic_files")
ut.model_reader(model_folder, zone_data, re_order=True)
ut.model_reader(bna_folder, volcanic_data)
special_data['colom_ecu_fro.txt'] = zone_data.pop('colom_ecu_fro.txt', None)
special_data['zona_nll.txt'] = zone_data.pop('zona_nll.txt', None)


def connect2mysql(
        name: str,
        start_time: dt.datetime,
        end_time: dt.datetime,
):
    """
    Parameters:
    -----------
    name : str
        'sentido','destacado','normal'
    start_time: datetime object
        Start time with the next format: "YYYYmmdd HHMMss"
    end_time: datetime object
        End time with the next format: "YYYYmmdd HHMMss"

    :returns:
    ----------
    A pandas dataframe with the seismic data for the given time range.
    """
    time_parts = ['year', 'month', 'day', 'hour', 'minute', 'second']

    start_time_values = {part: f"{getattr(start_time, part):02d}" for part in time_parts}
    end_time_values = {part: f"{getattr(end_time, part):02d}" for part in time_parts}

    year1, mes1, dia1, hora1, min1, sec1 = start_time_values.values()
    year2, mes2, dia2, hora2, min2, sec2 = end_time_values.values()

    # Load the queries from the json file
    json_folder = os.path.join(os.path.dirname(__file__), 'queries.json')
    with open(json_folder) as f:
        queries = json.load(f)

    # Connect to the database, supress the UserWarning and query data
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        codex = f'{queries[name]}"{year1}/{mes1}/{dia1} {hora1}:{min1}:{sec1}" and "{year2}/{mes2}/{dia2} {hora2}:{min2}:{sec2}"'
        db = pymysql.connect(host="172.25.3.135", user="consulta", passwd="consulta", db="seiscomp3")

        # Add a message to show query progress
        with tqdm(total=1, desc="Querying database...", unit="query", leave=False, bar_format="{desc}") as pbar:
            sql_db = pd.read_sql_query(codex, db)
            pbar.update(1)

        df = pd.DataFrame(sql_db)
        df = df.where(pd.notnull(df), None)
        df = df.sort_values("time_value", ascending=False)

        # Change name of the 16th column to 'magnitude_type' in order to avoid conflicts with column 11.
        df = ut.correct_df_columns(df)
        db.close()
    return df


def single_check(
        event: Union[list, tuple, np.ndarray, pd.Series],
        special_events: pd.DataFrame,
        flag: bool
):
    """
    A function to check the seismic data for a single event.

    Parameters:
    -----------
    event : list, tuple, numpy array or pandas series
        Seismic data for a single event. It should contain the following information:
        (0) Date and time of the event ('time_value')
        (1) Event ID ('publicID')
        (2) Depth ('depth_value')
        (3) Magnitude ('magnitude_value')
        (4) RMS ('quality_standardError')
        (5) Depth uncertainty ('depth_uncertainty')
        (6) Latitude uncertainty ('latitude_uncertainty')
        (7) Longitude uncertainty ('longitude_uncertainty')
        (8) Phase count ('quality_associatedPhaseCount')
        (9) Author ('creationInfo_author')
        (10) Event type ('type'), i.e., 'earthquake', 'not_locatable'
        (11) Agency ('creationInfo_agencyID')
        (12) Localization text ('text'), i.e., "Cimitarra - Santander, Colombia"
        (13) Latitude ('latitude_value')
        (14) Longitude ('longitude_value')
        (15) Magnitude type ('magnitude_type'), i.e., 'MLr_vmm'
        (16) Localization method used ('methodID'), i.e., 'Hypo71'
        (17) Earth model used ('earthModelID'), i.e., 'iasp91', 'RSNC'

    special_events: pandas dataframe
        Featured events for the given time range. Used for inspection of the events.
    flag: bool
        Flag to indicate if check for 7 or less phase counts.

    :returns:
    ----------
    A Tuple with the following information if the event has observations: (a) Date and time of the event, (b) Event ID,
    (c) Region, (d) Depth, (e) Magnitude, (f) Magnitude type, (g) RMS, (h) Depth uncertainty, (i) Latitude uncertainty,
    (j) Longitude uncertainty, (k) Phase count, (l) Author, (m) Event type, (n) Agency, (o) Observations. If the event
    has no observations, the tuple will be empty.
    """
    observations = []
    lat, lon = event['latitude_value'], event['longitude_value']
    inside_volcanic_zones = ut.inside_bna_polygon((lon, lat), volcanic_data)

    # First check: High RMS values
    exceptions = ["not locatable", "outside of network interest", "volcanic eruption", "explosion", "not existing"]
    if event['quality_standardError'] > 1.51 and event['type'] not in exceptions:
        observations.append("High RMS value")
        
    # Second check: High localization uncertainties
    exceptions_loc = ["not locatable", "outside of network interest", "volcanic eruption", "explosion", "not existing"]
    # Check if any of the uncertainties are greater than or equal to 12, avoiding NaN values
    if any(pd.notnull(event[col]) and event[col] >= 12 for col in ['latitude_uncertainty', 'longitude_uncertainty', 'depth_uncertainty']) and event['type'] not in exceptions_loc:
        observations.append("High localization uncertainties")

    # Third check: Locatable events with anomalous label
    if event['type'] == "not locatable" and event['quality_associatedPhaseCount'] >= 8:
        # Check if the event is inside volcanic zones and it must have not locatable label
        if not inside_volcanic_zones:
            observations.append("Locatable event")

    # Fourth check: Check correspondence between zones and magnitude labels
    if event['quality_associatedPhaseCount'] >= 7 and event['type'] not in ["not locatable", "not existing"]:
        # Peñaranda request: Ignore events with 'Mw' label and inside 'DESTACADO' events
        if not (event['magnitude_type'] == 'Mw' and event['publicID'] in special_events['publicID'].values):
            boolean, correct_mag = ut.magnitude_check((lon, lat), event['magnitude_type'], zone_data)
            if not boolean and correct_mag is not None:  # If the event is inside a zone, show the correct magnitude label
                    observations.append(f"Correct magnitude with {correct_mag} (Current: {event['magnitude_type']})")
            # Fifth check: Check for correct models for CARMA, Cesar, VMM and PtoGaitan zones
        sol, model_sol = ut.inside_zone_polygon((lon, lat), zone_data, check_models=True)
        if sol:
            if model_sol == 'zona_vmm.txt' and event['earthModelID'] != 'VMM':
                observations.append("Correct model to modelVMM")
            elif model_sol == 'Modelo_Cesar.txt' and event['earthModelID'] != 'modelCesar2':
                observations.append("Correct model to modelCesar2")
            elif model_sol == 'Modelo_CARMA.txt' and event['earthModelID'] != 'CARMA':
                observations.append("Correct model to CARMA")
            elif model_sol == 'zona_PtoGaitan.txt' and event['earthModelID'] != 'Pto_Gaitan':
                observations.append("Correct model to Pto_Gaitan")

    # Sixth check: Check if the event has 7 or less phase counts
    if event['quality_associatedPhaseCount'] <= 7 and flag and event['type'] == "not locatable":
        observations.append("Event with 7 or less phase count")

    # Seventh check: Check if the event does NOT have any label, or it is anomalous
    valid_labels = ["earthquake", "not locatable", "volcanic eruption", "explosion", "not existing", "outside of network interest"]
    if pd.isnull(event['type']):
        observations.append("Event without label. Update ASAP!")
    else:
        if event['type'] not in valid_labels:
            observations.append(f"Event with invalid label '{event['type']}'")

    # Eighth check: Check if the event has not been processed by the user
    cases = ["scanloc", "scautoloc_reg", "scanlocbay", "AI_picker"]
    if event['creationInfo_author'] in cases and event['type'] != "not existing" and event['creationInfo_agencyID'] == "SGC":
        observations.append("Unprocessed or unassociated event")

    # Ninth check: Check international events without agency association
    if event['type'] == "outside of network interest" or event['creationInfo_author'] == cases[1]:
        if event['creationInfo_agencyID'] == "SGC" and event['magnitude_value'] >= 5.0:
            observations.append("International event without any associated agency")

    # Tenth check: Check if a 'destacado' event has the correct label
    if event['type'] not in exceptions and event['magnitude_value'] >= 4.0 and event['publicID'] not in special_events['publicID'].values:
        observations.append(f"Event with M = {event['magnitude_value']:.2f} without 'DESTACADO' label")

    # Eleventh check: Check if any event inside the volcanic zones has the correct 'not locatable' label
    exceptions_vol = ["not locatable", "volcanic eruption", "not existing"]
    if inside_volcanic_zones:
        if event['creationInfo_agencyID'] == "SGC" and event['type'] not in exceptions_vol:
            observations.append(f"Volcanic event with wrong label '{event['type']}'")
        elif event['type'] == "volcanic eruption" and event['publicID'] not in special_events['publicID'].values:
            observations.append("Volcanic event without 'DESTACADO' label or without 'not locatable' label")

    # Twelfth check: Check if any event outside all zone 1-5 and inside the network interest has depth less than 30 km
    # BUG: The condition for lon, lat is ambiguous. Events with lon > -72.6 and < -70 inside the network interest are NOT considered yet.
    # if lat > 1 and lon < -72.6 and event['depth_value'] > 30 and event['type'] == "earthquake" and not ut.inside_zone_polygon((lon, lat), zone_data, check_models=False)[0]:
    if 7.5 > lat > 3 and lon < -77.2 and event['depth_value'] > 30 and event['type'] == "earthquake":
        observations.append(f"Pacific/Caribe event with high depth: {event['depth_value']:.2f} km")

    # Thirteenth check: Check if the event has negative depth
    if event['depth_value'] < 0 and event['type'] == "earthquake":
        observations.append(f"Event with negative depth: {event['depth_value']:.2f} km")

    # Fourteenth check: Check if the event has an 'earthquake' label but has less than 6 phases
    if event['type'] == "earthquake" and event['quality_associatedPhaseCount'] < 6:
        observations.append(f"Event with 'earthquake' label but has {event['quality_associatedPhaseCount']} phases")

    # Fifteenth check: Check if the event is inside/outside local zone and has wrong label
    cases = ["earthquake", "volcanic eruption"]
    if not ut.inside_the_polygon((lon, lat), special_data['colom_ecu_fro.txt']):
        if event['type'] in cases:
            observations.append(f"Event outside local zone with '{event['type']}' label")
    else:
        if event['type'] == "outside of network interest":
            observations.append("Event inside local zone with 'outside of...' label")

    # Sixteenth check: Verify if 'DESTACADO' events inside NonLinLoc zone use the correct earth model
    # Define a boolean to check if the event is inside the NonLinLoc zone but outside the VMM and volcanic zones
    nll_bool = ut.inside_the_polygon((lon,lat), special_data['zona_nll.txt']) and not ut.inside_the_polygon((lon,lat), zone_data['zona_vmm.txt']) and not inside_volcanic_zones
    if event['publicID'] in special_events['publicID'].values and nll_bool and event['earthModelID'] != 'Poveda_et_al_2018':
        observations.append("'DESTACADO' event inside NonLinLoc zone without NLL localization model")
    
    # Seventeenth check: Events with Hypo earthmodel but more than 101 phases:
    if event['methodID'] == 'Hypo71' and event['quality_standardError'] == 0.0 and event['type'] in ["outside of network interest", "earthquake"]:
        observations.append(f"{event['methodID']}-{event['earthModelID']} event with more than 101 phases? (RMS 0.0)")
    
    if len(observations) > 0:  # If the event has observations, return the information
        return event[columns], observations
    else:
        return None, None


def check_duplicates(
        events: pd.DataFrame
):
    """
    Identifies duplicate events based on time and geographical distance.

    Parameters:
    -----------
    events: pandas dataframe
        Seismic data for the given time range. Generally obtained from the connect2mysql function.

    Returns:
    --------
    duplicates: A pandas dataframe
        Table with information about duplicate events.
    """
    # Filter events with the following types
    checks = ["earthquake", "volcanic eruption", "explosion", "outside of network interest"]
    selections = events[events['type'].isin(checks)].reset_index(drop=True)

    # Make a pandas dataframe to store the info of the duplicates
    duplicates = pd.DataFrame()

    # Loop over al earthquakes, ordered by time
    for i in trange(len(selections) - 1, desc="Checking duplicates", unit="event", leave=False):
        event1 = selections.iloc[i]  # Take the i-esim event on the list
        event2 = selections.iloc[i + 1]  # Compared to the next event

        # Check if the events are within 4 seconds of each other
        time_diff = abs((event2['time_value'] - event1['time_value']).total_seconds())
        if time_diff <= 4:
            # Estimate the distance between the two events using haversine formula
            distance = hs.haversine((event1['latitude_value'], event1['longitude_value']),
                                     (event2['latitude_value'], event2['longitude_value']))
            if distance <= 100:  # If both events are within 100 km and 4 seconds, they can be duplicates
                dup_1 = event1[columns].copy()
                dup_1['Observations'] = f'Possible duplicate event of {event2["publicID"]}'
                dup_2 = event2[columns].copy()
                dup_2['Observations'] = f'Possible duplicate event of {event1["publicID"]}'
                # Add the two events to the duplicates dataframe
                duplicates = pd.concat([duplicates, dup_1.to_frame().T], ignore_index=True)
                duplicates = pd.concat([duplicates, dup_2.to_frame().T], ignore_index=True)
    return duplicates


def check_seismic(
        df: pd.DataFrame,
        special_df: pd.DataFrame,
        flag: bool,
        n_processes: int = 1
):
    """
    A function to check the seismic data for a given time range.

    Parameters:
    -----------
    df : pandas dataframe
        Seismic data for the given time range. Generally obtained from the connect2mysql function.
    special_df: pandas dataframe
        Featured events for the given time range.
    flag: bool
        Flag to indicate if check for 7 or less phase counts.
    n_processes: int
        Number of processes to use if parallel processing is enabled.

    :returns:
    ----------
    A pandas dataframe, where each row contains the following information for a single event: (a) Date and time of the
    event, (b) Event ID, (c) Depth, (d) Magnitude, (e) Magnitude type, (f) RMS, (g) Depth uncertainty, (h) Latitude
    uncertainty, (i) Longitude uncertainty, (j) Phase count, (k) Author, (l) Event type, (m) Agency, (n) Observations.
    """
    events_with_observations = pd.DataFrame()
    if n_processes == 1:
        for _, event in tqdm(df.iterrows(), total=len(df), desc='Processing events', unit='events', leave=False):  # Loop over each event queried from the database
            event_info, errors = single_check(event, special_df, flag)  # Check if the event has observations
            if event_info is not None:  # If the event has observations, append each observation to the dataframe
                for error in errors:
                    event_info_copy = event_info.copy()  # Create a copy of event_info to modify
                    event_info_copy['Observations'] = error
                    events_with_observations = pd.concat([events_with_observations, event_info_copy.to_frame().T], ignore_index=True)
    else:
        print(Fore.GREEN + f"Fixing {n_processes} workers for parallel processing...")
        with concurrent.futures.ProcessPoolExecutor(max_workers=n_processes) as executor:
            results = list(tqdm(executor.map(single_check, [event for _, event in df.iterrows()], [special_df] * len(df), [flag] * len(df)), total=len(df), desc='Processing events', unit='events', leave=False))
            # For each result, check if the event has observations and append the info to the dataframe
            for _, (event_info, errors) in enumerate(results):
                if event_info is not None:
                    for error in errors:
                        event_info['Observations'] = error
                        events_with_observations = pd.concat([events_with_observations, event_info.to_frame().T], ignore_index=True)
    return events_with_observations


def run(
        start_time: dt.datetime,
        end_time: dt.datetime,
        flag: bool,
        user: str = None,
        n_processes: int = 1
):
    """
    A function to run the seismicity revision routine for the RSNC catalog.

     Parameters:
    -----------
    start_time: datetime object
        Start time with the next format: "YYYYmmdd HHMMss"
    end_time: datetime object
        End time with the next format: "YYYYmmdd HHMMss"
    flag: bool
        Flag to indicate if check for 7 or less phase counts.
    user: str
        Username to check only the events that have been processed by the user.
    n_processes: int
        Number of processes to use if parallel processing is enabled.

    :returns:
    ----------
    A pandas dataframe, where each row contains the following information for a single event: (a) Date and time of the
    event, (b) Event ID, (c) Depth, (d) Magnitude, (e) Magnitude type, (f) RMS, (g) Depth uncertainty, (h) Latitude
    uncertainty, (i) Longitude uncertainty, (j) Phase count, (k) Author, (l) Event type, (m) Agency, (n) Observations.
    """
    # Query data from seiscomp3 database
    data = connect2mysql('normal', start_time, end_time)
    featured_events = connect2mysql('destacado', start_time, end_time)

    # If user is specified, filter data
    if user is not None:
        # Take into account the different servers for each user and the user 'bdrsn'
        users = [f"{user}@proc{i}" for i in range(1, 5)] if user != 'bdrsn' else ['bdrsn']
        data = data[data['creationInfo_author'].isin(users)]

    # Check for duplicates
    duplicates = check_duplicates(data)
    # Check seismic data
    observations = check_seismic(data, featured_events, flag, n_processes)

    # If there are duplicates, add them to the observations dataframe
    if not duplicates.empty:
        observations = pd.concat([observations, duplicates], ignore_index=True)
        # Order the dataframe by time_value
        observations = observations.sort_values(by='time_value', ascending=False)

    return observations


def read_args():
    prefix = "+"

    parser = argparse.ArgumentParser("Seismic revision routine. ", prefix_chars=prefix)

    parser.add_argument(prefix + "n", prefix * 2 + "n_processes",
                        default=1,
                        type=int,
                        metavar='',
                        help="Número de procesos a utilizar (Recomendado para largos periodos de tiempo)", required=False)

    parser.add_argument(prefix + "f", prefix * 2 + "flag",
                        action='store_false',
                        help="Etiqueta para buscar eventos con 7 o menos fases", required=False)

    parser.add_argument(prefix + "s", prefix * 2 + "start",
                        default=None,
                        type=str,
                        metavar='',
                        help="Fecha inicial en formato yyyymmddThhmmss", required=True)

    parser.add_argument(prefix + "e", prefix * 2 + "end",
                        default=None,
                        type=str,
                        metavar='',
                        help="Fecha final en formato yyyymmddThhmmss", required=True)

    parser.add_argument(prefix + "u", prefix * 2 + "user",
                        default=None,
                        type=str,
                        metavar='',
                        help="Digitar el nombre del usuario")

    parser.add_argument(prefix + "o", prefix * 2 + "output",
                        action='store_true',
                        help="Etiqueta para guardar los resultados en un archivo csv")

    parser.add_argument(prefix + "p", prefix * 2 + "printer",
                        action='store_true',
                        help="Etiqueta para imprimir los resultados usando pandas. Se recomienda añadir en caso de que"
                             "la tabla de resultados no se imprima correctamente.")

    args_parser = parser.parse_args()
    vars_args = vars(args_parser)
    return vars_args


if __name__ == '__main__':
    params = read_args()
    time1 = dt.datetime.strptime(params['start'], "%Y%m%dT%H%M%S")
    time2 = dt.datetime.strptime(params['end'], "%Y%m%dT%H%M%S")
    user_def = params["user"]
    output = params["output"]
    flag_def = params["flag"]
    n = params["n_processes"]
    printer = params["printer"]

    start = time.time()
    result = run(time1, time2, flag_def, user_def, n)

    if not result.empty:  # Check if the result is an empty dataframe
        result.columns = result_columns  # Change columns names
        # Remove accents from the Region column to print and save results
        ut.remove_accents(result, 'Region')
        ut.printer(result, printer, flag_def)  # Print results
        if output:  # Save results if required
            result.to_csv(f"seismic_revision_{params['start']}_{params['end']}.csv", index=False)
            print(Fore.RED + f"File seismic_revision_{params['start']}_{params['end']}.csv saved in {os.getcwd()}")
    else:
        print(Fore.RED + "No seismic data observations found for the given time range.")
    end = time.time()
    print(Fore.GREEN + f"Seismic revision routine executed in {end - start:.2f} seconds.")
