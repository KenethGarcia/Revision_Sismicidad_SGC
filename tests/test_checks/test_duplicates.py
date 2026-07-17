# Author: Garcia-Cifuentes, K. <ORCID:0009-0001-2607-6359>

# --------------------------------------------------------------------------------------------------------
# This file contains tests for the duplicates.py function
# --------------------------------------------------------------------------------------------------------
import pytest
import numpy as np
import pandas as pd

from src.checks.duplicates import (
    haversine_np,
    check_duplicates_adjacent,
    check_duplicates_sswa
)

def test_haversine_formulae():
    """
    Function to test the haversine formulae implemented in the duplicates.py file.
    It checks if the distance between two points is calculated correctly.
    """
    # Test case 1: Check for zero distance
    lat = np.array([4.0, 10.0])
    lon = np.array([-74.0, -70.0])
    d = haversine_np(lat, lon, lat, lon)
    assert d.shape == lat.shape
    assert np.allclose(d, 0.0)

    # Test case 2: Known distance scalar - Roughly Bogotá (~4.71,-74.07) to Medellín (~6.25,-75.56)
    lat1, lon1 = 4.71, -74.07
    lat2, lon2 = 6.25, -75.56
    d = haversine_np(lat1, lon1, lat2, lon2)
    # Expect something in the ~215–235 km range
    assert np.allclose(d, 225.0, atol=20.0)

    # Test case 3: Array of distances
    lat1 = np.array([0.0, 0.0])
    lon1 = np.array([0.0, 0.0])
    lat2 = np.array([0.0, 1.0])
    lon2 = np.array([1.0, 0.0])
    d = haversine_np(lat1, lon1, lat2, lon2)
    assert d.shape == lat1.shape
    # Distances should be > 0 and of similar magnitude
    assert np.all(d > 0.0)


def test_check_duplicates_adjacent():
    """
    Function to test the check_duplicates_adjacent function.
    It checks if the function correctly identifies adjacent duplicates.
    """
    # Test case 1: Too few events to check
    df = pd.DataFrame(
        {
            "time": [pd.Timestamp("2024-01-01T00:00:00")],
            "lat": [4.0],
            "lon": [-74.0],
            "id": ["E1"],
        }
    )
    result = check_duplicates_adjacent(df, ["time", "lat", "lon", "id"], time_window=4, dist_threshold=100.0)
    assert isinstance(result, pd.DataFrame)
    assert list(result.columns) == list(df.columns) + ["Observations"]
    assert len(result) == 0

    # Test case 2: No duplicates
    df = pd.DataFrame(
        {
            "time": [
                pd.Timestamp("2024-01-01T00:00:00"),
                pd.Timestamp("2024-01-01T01:00:00"),
            ],
            "lat": [4.0, 5.0],
            "lon": [-74.0, -75.0],
            "id": ["E1", "E2"],
        }
    )
    result = check_duplicates_adjacent(df, ["time", "lat", "lon", "id"], time_window=4, dist_threshold=100.0)
    assert isinstance(result, pd.DataFrame)
    assert list(result.columns) == list(df.columns) + ["Observations"]
    assert len(result) == 0

    # Test case 3: One single duplicate in various events
    times = pd.to_datetime(
        ["2024-01-01T00:00:00",
         "2024-01-01T00:00:01",
         "2024-01-01T00:00:02"]
    )
    df = pd.DataFrame(
        {
            "time": times,
            "lat": [4.0, 4.0001, 4.5],  # third is far away
            "lon": [-74.0, -74.0001, -75.0],
            "id": ["E1", "E2", "E3"],
        }
    )
    result = check_duplicates_adjacent(df, ["time", "lat", "lon", "id"], time_window=4, dist_threshold=50.0)
    assert len(result) == 2    # Only E1 and E2 should be flagged
    ids = result["id"].tolist()
    assert set(ids) == {"E1", "E2"}
    obs = result["Observations"].tolist()

    # Each event should mention the other as a possible duplicate
    assert any("E2" in o for o in obs)
    assert any("E1" in o for o in obs)
    # Index should be reset
    assert list(result.index) == [0, 1]

    # Test case 4: Multiple pairs of duplicates
    times = pd.to_datetime(
        ["2024-01-01T00:00:00",
         "2024-01-01T00:00:01",
         "2024-01-01T00:01:00",
         "2024-01-01T00:01:01"]
    )
    df = pd.DataFrame(
        {
            "time": times,
            "lat": [4.0, 4.0001, 5.0, 5.0001],
            "lon": [-74.0, -74.0001, -75.0, -75.0001],
            "id": ["E1", "E2", "E3", "E4"],
        }
    )
    result = check_duplicates_adjacent(df, ["time", "lat", "lon", "id"], time_window=4, dist_threshold=50.0)

    assert len(result) == 4
    # Each ID should be present
    assert set(result["id"].tolist()) == {"E1", "E2", "E3", "E4"}
    # E1 observations mention E2, E3 mentions E4, etc.
    for row in result.itertuples():
        if row.id == "E1":
            assert "E2" in row.Observations
        if row.id == "E2":
            assert "E1" in row.Observations
        if row.id == "E3":
            assert "E4" in row.Observations
        if row.id == "E4":
            assert "E3" in row.Observations


def test_check_duplicates_sswa():
    """
    Function to test the check_duplicates_sswa function.
    It checks if the function correctly identifies duplicates using the sorted sliding window approach.
    """
    # Test case 1: Too few events to check
    df = pd.DataFrame(
        {
            "time": [pd.Timestamp("2024-01-01T00:00:00")],
            "lat": [4.0],
            "lon": [-74.0],
            "id": ["E1"],
        }
    )
    result = check_duplicates_sswa(df, ["time", "lat", "lon", "id"], time_window=4, dist_threshold=100.0)
    assert isinstance(result, pd.DataFrame)
    assert list(result.columns) == list(df.columns) + ["Observations"]
    assert len(result) == 0

    # Test case 2: No duplicates
    df = pd.DataFrame(
        {
            "time": [
                pd.Timestamp("2024-01-01T00:00:00"),
                pd.Timestamp("2024-01-01T01:00:00"),
            ],
            "lat": [4.0, 5.0],
            "lon": [-74.0, -75.0],
            "id": ["E1", "E2"],
        }
    )
    result = check_duplicates_sswa(df, ["time", "lat", "lon", "id"], time_window=4, dist_threshold=100.0)
    assert isinstance(result, pd.DataFrame)
    assert list(result.columns) == list(df.columns) + ["Observations"]
    assert len(result) == 0

    # Test case 3: Three duplicates in the same chain (not detected by adjacent approach)
    times = pd.to_datetime(
        [
            "2024-01-01T00:00:10",  # E2
            "2024-01-01T00:00:00",  # E1
            "2024-01-01T00:00:15",  # E3
        ]
    )
    df = pd.DataFrame(
        {
            "time": times,
            "lat": [4.0, 4.00005, 4.0001],  # all close
            "lon": [-74.0, -74.00005, -74.0001],
            "id": ["E2", "E1", "E3"],
        }
    )
    result = check_duplicates_sswa(df, ["time", "lat", "lon", "id"], time_window=20, dist_threshold=50.0)

    # All three events should be flagged once
    assert len(result) == 3
    ids = result["id"].tolist()
    assert set(ids) == {"E1", "E2", "E3"}

    # Observations should contain references to other IDs for each event
    for row in result.itertuples():
        if row.id == "E1":
            assert "E2" in row.Observations or "E3" in row.Observations
        if row.id == "E2":
            assert "E1" in row.Observations or "E3" in row.Observations
        if row.id == "E3":
            assert "E1" in row.Observations or "E2" in row.Observations

    # Index reset
    assert list(result.index) == [0, 1, 2]


if __name__ == "__main__":
    pytest.main()