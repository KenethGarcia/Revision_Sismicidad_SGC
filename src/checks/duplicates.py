# Author: Garcia-Cifuentes, K. <ORCID:0009-0001-2607-6359>

# --------------------------------------------------------------------------------------------------------
# This file contains functions to check duplicated events inside a catalog
# --------------------------------------------------------------------------------------------------------
import numpy as np
import pandas as pd


def haversine_np(
    lat1: float | np.ndarray,
    lon1: float | np.ndarray,
    lat2: float | np.ndarray,
    lon2: float | np.ndarray
) -> np.ndarray:
    """
    Fully vectorized haversine distance (km) between paired lat/lon arrays.

    Parameters
    ----------
    lat1 : float, np.array
        Latitude of the first point(s) in degrees. Can be a single float or a NumPy array of floats.
    lat2 : float, np.array
        Latitude of the second point(s) in degrees. Can be a single float or a NumPy array of floats.
    lon1 : float, np.array
        Longitude of the first point(s) in degrees. Can be a single float or a NumPy array of floats.
    lon2 : float, np.array
        Longitude of the second point(s) in degrees. Can be a single float or a NumPy array of floats.

    Returns
    -------
    np.ndarray
        Array of distances in kilometers between the paired points. The output shape matches the input shape of the latitude and longitude arrays.
    """
    R = 6371.0088
    lat1r, lat2r = np.radians(lat1), np.radians(lat2)
    dlat = lat2r - lat1r
    dlon = np.radians(lon2 - lon1)
    a = np.sin(dlat / 2.0) ** 2 + np.cos(lat1r) * np.cos(lat2r) * np.sin(dlon / 2.0) ** 2
    return 2 * R * np.arcsin(np.sqrt(a))

def check_duplicates_adjacent(
    events: pd.DataFrame,
    columns: list[str],
    time_window: int,
    dist_threshold: float,
) -> pd.DataFrame:
    """
    Identifies duplicate events based on time proximity and geographical
    distance between temporally-adjacent events (after sorting by time).

    Time complexity: O(n) — all comparisons are vectorized NumPy array
    operations; only the (typically rare) confirmed duplicate pairs are
    iterated in Python to build per-row observation text.

    Parameters
    ----------
    events : pd.DataFrame
        Seismic data for the given time range.
    columns : list[str]
        List of columns to extract time values, latitudes, longitudes and IDs.
    time_window : int
        Time window in seconds to detect duplicated events.
    dist_threshold : float
        Distance threshold in kilometers to detect duplicates.

    Returns
    -------
    pd.DataFrame
        Subset of `events` (all original columns preserved) with an added
        'Observations' column, containing only the flagged duplicate rows.
    """
    if len(events) < 2:
        empty = events.copy()
        empty['Observations'] = pd.Series(dtype='object')
        return empty.iloc[0:0]

    sorted_events = events.sort_values(columns[0])

    times = sorted_events[columns[0]].to_numpy()
    lats  = sorted_events[columns[1]].to_numpy(dtype=np.float64)
    lons  = sorted_events[columns[2]].to_numpy(dtype=np.float64)
    ids   = sorted_events[columns[3]].to_numpy()

    time_diff   = np.abs(times[1:] - times[:-1])
    within_time = time_diff <= np.timedelta64(time_window, 's')

    distances   = haversine_np(lats[:-1], lons[:-1], lats[1:], lons[1:])
    within_dist = distances <= dist_threshold

    adjacent_dup = within_time & within_dist
    dup_idx = np.where(adjacent_dup)[0]

    if dup_idx.size == 0:
        empty = events.copy()
        empty['Observations'] = pd.Series(dtype='object')
        return empty.iloc[0:0]

    obs_map: dict[int, list[str]] = {}
    for i in dup_idx:
        obs_map.setdefault(int(i), []).append(f'Possible duplicate event of {ids[i + 1]}')
        obs_map.setdefault(int(i) + 1, []).append(f'Possible duplicate event of {ids[i]}')

    flagged_positions = sorted(obs_map.keys())
    flagged = sorted_events.iloc[flagged_positions].copy()
    flagged['Observations'] = ['; '.join(obs_map[p]) for p in flagged_positions]

    return flagged


def check_duplicates_sswa(
    events: pd.DataFrame,
    columns: list[str],
    time_window: int,
    dist_threshold: float,
) -> pd.DataFrame:
    """
    Identifies duplicate events based on time proximity and geographical
    distance, using a sliding time window (compares every event against
    ALL others within time_window seconds, not just its direct neighbor).

    Parameters
    ----------
    events : pd.DataFrame
        Seismic data for the given time range. Must contain the columns
        referenced by `columns`.
    columns : list[str]
        Ordered list [time_col, lat_col, lon_col, id_col] identifying which
        columns hold time, latitude, longitude, and event ID values.
    time_window : int
        Time window in seconds to detect duplicated events.
    dist_threshold : float
        Distance threshold in kilometers to detect duplicates.

    Returns
    -------
    pd.DataFrame
        Subset of `events` (all original columns preserved) with an added
        'Observations' column, one row per flagged duplicate event —
        chains of 3+ nearby events are merged into a single row per event
        rather than duplicated across multiple pair-rows.
    """
    time_col, lat_col, lon_col, id_col = columns
    selections = events.copy()

    if len(selections) < 2:
        empty = events.copy()
        empty['Observations'] = pd.Series(dtype='object')
        return empty.iloc[0:0]

    sorted_events = selections.sort_values(time_col).reset_index(drop=True)

    times = sorted_events[time_col].to_numpy()
    lats = sorted_events[lat_col].to_numpy(dtype=np.float64)
    lons = sorted_events[lon_col].to_numpy(dtype=np.float64)
    ids = sorted_events[id_col].to_numpy()
    n = len(sorted_events)

    window_delta = np.timedelta64(time_window, 's')

    # For every i, right_bound[i] = first index j where times[j] > times[i] + window
    right_bound = np.searchsorted(times, times + window_delta, side='right')

    obs_map: dict[int, list[str]] = {}

    for i in range(n - 1):
        j_end = right_bound[i]
        if j_end <= i + 1:
            continue

        window_lats = lats[i + 1:j_end]
        window_lons = lons[i + 1:j_end]
        distances = haversine_np(lats[i], lons[i], window_lats, window_lons)

        matched_offsets = np.where(distances <= dist_threshold)[0]
        if matched_offsets.size == 0:
            continue

        matched_js = i + 1 + matched_offsets
        for j in matched_js:
            obs_map.setdefault(i, []).append(f'Possible duplicate event of {ids[j]}')
            obs_map.setdefault(int(j), []).append(f'Possible duplicate event of {ids[i]}')

    if not obs_map:
        empty = events.copy()
        empty['Observations'] = pd.Series(dtype='object')
        return empty.iloc[0:0]

    flagged_positions = sorted(obs_map.keys())
    flagged = sorted_events.iloc[flagged_positions].copy()
    flagged['Observations'] = ['; '.join(obs_map[p]) for p in flagged_positions]

    return flagged.reset_index(drop=True)


def check_duplicates(
    events: pd.DataFrame,
    subset: list[str] | None = None,
    method: str = "adjacent",
    time_window: int = 4,
    dist_threshold: float = 100.0,
) -> pd.DataFrame:
    """
    Vectorized duplicate search for seismic quality checks.

    Parameters
    ----------
    events : pd.DataFrame
        Input seismic dataframe.
    subset : list[str]
        List of columns to consider for identifying duplicates.
        If not specified, defaults to ['time_value', 'latitude_value', 'longitude_value', 'publicID'].
    method : str
        Determines the method for identifying duplicates:
            'adjacent' -> Adjacent-only method.
            Flags a row as a duplicate if it has the same values in the specified subset as the previous row.
            This method is faster but only detects duplicates that are next to each other in the DataFrame. Recommended
            if the events are time-ordered and the usual time difference between two events is similar to the time window.
            'sswa'      -> Sorted Sliding Window Approach. Flags a row as a duplicate if it has the same values in the
            specified subset as any of the previous rows within a sliding window of specified size.
            This method is slower but can detect duplicates that are not adjacent. Recommended if the events are not
            time-ordered or if the usual time difference between two events is shorter than the time window.
    time_window : int
        Time window in seconds to detect duplicates. Defaults to 4.
    dist_threshold : float
        Distance threshold in kilometers to detect duplicates. Defaults to 100.0.

    Returns
    -------
    pd.DataFrame
        Subset of `events` (all original columns preserved) with an added
        'Observations' column, one row per flagged duplicate event —
        chains of 3+ nearby events are merged into a single row per event
        rather than duplicated across multiple pair-rows.
    """
    if subset is None:
        subset = ['time_value', 'latitude_value', 'longitude_value', 'publicID']

    if method == "adjacent":
        return check_duplicates_adjacent(events, subset, time_window, dist_threshold)
    elif method == "sswa":
        return check_duplicates_sswa(events, subset, time_window, dist_threshold)
    else:
        raise ValueError(f"Unsupported method: {method!r}. Supported methods are 'adjacent' and 'sswa'.")