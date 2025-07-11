import os
import sys
import unittest
import importlib.util
import numpy as np
import pandas as pd
from shapely.geometry import Polygon

# Import utils as ut wherever the executed file is located
file_path = os.path.join(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'src'), 'utils.py')  # Location of utils.py

# Load the module as 'ut' in order to avoid conflicts with the 'utils' name
spec = importlib.util.spec_from_file_location("ut", file_path)
ut = importlib.util.module_from_spec(spec)
sys.modules["ut"] = ut
spec.loader.exec_module(ut)

models_available = ('zona_vmm.txt', 'zona3.txt', 'zona2.txt', 'zona_PtoGaitan.txt', 'zona4.txt', 'zona1.txt',
                    'zona5.txt', 'Modelo_Cesar.txt', 'Modelo_CARMA.txt')
volcanic_models_available = ('obsman.txt', 'obspas1.txt', 'obspas2.txt', 'obspas3.txt', 'obspas4.txt', 'obspas5.txt',
                             'obspas6.txt', 'obspas7.txt', 'obspas8.txt', 'obspas9.txt', 'obspop.txt', 'obspopvnh.txt')

model_folder = os.path.join(os.path.dirname(os.path.dirname(__file__)), "model_files")
bna_folder = os.path.join(os.path.dirname(os.path.dirname(__file__)), "bna_volcanic_files")

class TestUtils(unittest.TestCase):
    def test_model_reader(self):
        """
        A function to test the model_reader function. The strategy is to read the model files of both regular and
        volcanic zones and compared the keys of the txt files and the type of the values. Moreover, it checks if the
        polygons read are valid.
        :return:
        """
        test_model_contents = {}  # Dictionary to store the model points
        ut.model_reader(model_folder, test_model_contents, re_order=True)
        # Assert that the dictionary is not empty
        self.assertTrue(test_model_contents, "Error reading the model files: No data was read")
        self.assertTrue(tuple(test_model_contents.keys()) == tuple(models_available),
                        f"Error reading the model files: Expected keys {models_available} but got "
                        f"{test_model_contents.keys()}")
        self.assertTrue(all(isinstance(value, np.ndarray) for value in test_model_contents.values()),
                        "Error reading the model files: Not all values are numpy arrays")
        volcanic_test_model_contents = {}  # Dictionary to store the volcanic models
        ut.model_reader(bna_folder, volcanic_test_model_contents)
        self.assertTrue(volcanic_test_model_contents, "Error reading the model files: No data was read")
        self.assertTrue(set(volcanic_test_model_contents.keys()) == set(volcanic_models_available),
                        f"Error reading volcanic model files: Expected keys {volcanic_models_available} but got "
                        f"{volcanic_test_model_contents.keys()}")
        self.assertTrue(all(isinstance(value, np.ndarray) for value in volcanic_test_model_contents.values()),
                        "Error reading volcanic model files: Not all values are numpy arrays")
        # Check that all polygons defined in the model files are valid
        for file, polygon in test_model_contents.items():
            polygon = Polygon(polygon)
            is_valid = polygon.is_valid
            self.assertTrue(is_valid, f"Error in model_reader: Polygon in {file} is not valid")
        for file, polygon in volcanic_test_model_contents.items():
            polygon = Polygon(polygon)
            is_valid = polygon.is_valid
            self.assertTrue(is_valid, f"Error in model_reader: Polygon in {file} is not valid")


    def test_inside_polygon(self):
        point_1 = (4.5, 4.5)
        point_2 = (0.001, 0.001)
        polygon_1 = np.array([[0, 0], [0, 5], [5, 5], [5, 0]])  # Square of size 5
        polygon_2 = np.array([[0, 0], [0, 5], [5, 5], [5, 0], [0, 0]]) # Square of size 5 repeating the first point
        polygon_3 = np.array([[-1, 1], [1, 1], [1, -1], [-1, -1]])  # Square of size 2
        self.assertTrue(ut.inside_the_polygon(point_1, polygon_1),
                        "Error in inside_the_polygon: Point 1 should be inside the square")
        self.assertTrue(ut.inside_the_polygon(point_1, polygon_2),
                        "Error in inside_the_polygon: Point 1 should be inside the square with repeated points")
        self.assertTrue(ut.inside_the_polygon(point_2, polygon_1),
                        "Error in inside_the_polygon: Point 2 should be inside the square")
        self.assertTrue(ut.inside_the_polygon(point_2, polygon_2),
                        "Error in inside_the_polygon: Point 2 should be inside the square with repeated points")
        self.assertFalse(ut.inside_the_polygon(point_1, polygon_3),
                        "Error in inside_the_polygon: Point 1 should not be inside the square")
        self.assertTrue(ut.inside_the_polygon(point_2, polygon_3),
                        "Error in inside_the_polygon: Point 2 should be inside the square")

    def test_df_corrector(self):
        """
        Function to test the df_corrector function. The strategy is to correct the format of the dataframe and compare
        the new dataframe with the expected columns.
        :return:
        """
        columns_before = ['time_value', 'publicID', 'depth_value', 'magnitude_value', 'quality_standardError',
                          'depth_uncertainty', 'latitude_uncertainty', 'longitude_uncertainty',
                          'quality_associatedPhaseCount', 'creationInfo_author', 'type', 'creationInfo_agencyID',
                          'text', 'latitude_value', 'longitude_value', 'type', 'methodID', 'earthModelID']
        # Create an empty dataframe with the columns in the wrong format
        df = pd.DataFrame(columns=columns_before)
        df = ut.correct_df_columns(df)
        # Assert that 'type' column is not repeated
        self.assertTrue(len(df.columns.get_indexer_for(['type'])) == 1,
                        "Error in df_corrector: 'type' column is repeated")
        self.assertTrue(len(columns_before) == len(df.columns),
                        "Error in df_corrector: Table does not have the same number of expected columns")

    def test_inside_bna_polygon_2(self):
        """
        Function to test if a point is inside or outside a volcanic area. The strategy is to test points that are within
        and outside all the volcanic areas in the RSNC (Manizales, Popayán, Pasto).

        BUG: At least for 18-02-2025, any points in area obspas3 and outside obspas1 are NOT being detected correctly.
        :return:
        """
        # Read the volcanic models
        volcanic_data = {}
        ut.model_reader(bna_folder, volcanic_data)

        # Test points within every volcanic area in RSNC
        test_points = ((-75.3413, 4.8149), (-75.9569, 2.8414), (-76.6090, 2.1458), (-77.0261, 1.2968),
                       (-77.1466, 1.2810), (-77.1219, 0.9277), (-78.0182, 0.6236), (-78.0024, 0.7550),
                       (-77.9382, 1.1744), (-77.8275, 0.9447))  # Zone 3 Bugs: (-76.6922, 1.4318), (-76.9302, 1.7689),
        outside_points = ((-77.1556, 1.3832), (-76.1254, 4.9232))
        for point in test_points:
            self.assertTrue(ut.inside_bna_polygon(point, volcanic_data),
                            f"Error in inside_bna_polygon: Point {point} should be inside a volcanic area")
        for point in outside_points:
            self.assertFalse(ut.inside_bna_polygon(point, volcanic_data),
                            f"Error in inside_bna_polygon: Point {point} should NOT be inside a volcanic area")

    def test_inside_zone_polygon(self):
        """
        Function to test if a point is inside or outside a regular area in the RSNC maps. The strategy is to test points
        that are in every one of the zones in the RSNC (from 1 to 5), points within model areas such as CARMA and Cesar,
        and points outside all the zones.
        """
        def inside_test_zone(point, data, zone_name, checks):
            self.assertTrue(ut.inside_zone_polygon(point, data, check_models=checks) == (True, zone_name),
                            f"Error in test2: Point {point} should be inside {zone_name}")

        # Read the regular models
        model_data = {}
        ut.model_reader(model_folder, model_data, re_order=True)
        # Start testing zones: 1 to 5
        point_zone1 = (-78.5704, 7.1168)  # Point inside zone1
        inside_test_zone(point_zone1, model_data, 'zona1.txt', checks=False)
        point_zone2 = (-76.0614, 2.8474)  # Point inside zone2 but OUTSIDE zona_vmm
        inside_test_zone(point_zone2, model_data, 'zona2.txt', checks=False)
        point_zone3 = (-71.0546, 6.7915)  # Point inside zone3
        inside_test_zone(point_zone3, model_data, 'zona3.txt', checks=False)
        point_zone3 = (-73.13733333, 7.561833333) # Point inside zone3
        inside_test_zone(point_zone3, model_data, 'zona3.txt', checks=False)
        point_zone4 = (-76.04, 8.48)  # Point inside zona4 but OUTSIDE Modelo_CARMA zone
        inside_test_zone(point_zone4, model_data, 'zona4.txt', checks=False)
        point_zone5 = (-69.7311, 2.3815)  # Point inside zona5
        inside_test_zone(point_zone5, model_data, 'zona5.txt', checks=False)
        point_zone_vmm = (-73.9294, 5.9988)  # Point inside zona_vmm and zone2
        inside_test_zone(point_zone_vmm, model_data, 'zona_vmm.txt', checks=False)
        # Now test models CARMA and Cesar
        point_cesar = (-73.52, 9.61)  # Point inside Cesar and zona4
        inside_test_zone(point_cesar, model_data, 'Modelo_Cesar.txt', checks=True)
        point_carma = (-75.1997, 12.4335)  # Point inside CARMA but OUTSIDE zona4
        inside_test_zone(point_carma, model_data, 'Modelo_CARMA.txt', checks=True)
        point_carma_2 = (-74.6808, 9.5052)  # Point inside CARMA and zona4
        inside_test_zone(point_carma_2, model_data, 'Modelo_CARMA.txt', checks=True)
        point_carma_zone3 = (-73.1110, 8.7804)  # Point insde CARMA and zona3
        inside_test_zone(point_carma_zone3, model_data, 'Modelo_CARMA.txt', checks=True)

    def test_magnitude_check(self):
        """
        Function to test the magnitude_check function. The strategy here is to test both correct and incorrect cases of
        magnitude types and points in RSNC zones.
        """
        # Read the regular models
        model_data = {}
        ut.model_reader(model_folder, model_data, re_order=True)
        # Test zones with different magnitudes:
        # Point inside zone1
        point_zone1 = (-78.5704, 7.1168)
        self.assertTrue(ut.magnitude_check(point_zone1, 'MLr_1', model_data)[0],
                        "Error in magnitude_check: Point inside zone1 with MLr_1 got False")
        boolean, correct_mag = ut.magnitude_check(point_zone1, 'MLr_vmm', model_data)
        self.assertFalse(boolean, "Error in magnitude_check: Point inside zone1 with MLr_vmm does not been detected")
        self.assertTrue(correct_mag == 'MLr_1', "Error in magnitude_check: Magnitude marked as correct is NOT MLr_1")
        # Point inside zone2
        point_zone2 = (-76.0614, 2.8474)  # Point inside zone2 but OUTSIDE zona_vmm
        self.assertTrue(ut.magnitude_check(point_zone2, 'MLr_2', model_data)[0],
                        "Error in magnitude_check: Point inside zone2 with MLr_2 got False")
        boolean, correct_mag = ut.magnitude_check(point_zone2, 'MLr_vmm', model_data)
        self.assertFalse(boolean,"Error in magnitude_check: Point inside zone2 with MLr_vmm does not been detected")
        self.assertTrue(correct_mag == 'MLr_2', "Error in magnitude_check: Magnitude marked as correct is NOT MLr_2")
        # Point inside zone3
        point_zone3 = (-71.0546, 6.7915)
        self.assertTrue(ut.magnitude_check(point_zone3, 'MLr_3', model_data)[0],
                        "Error in magnitude_check: Point inside zone3 with MLr_3 got False")
        boolean, correct_mag = ut.magnitude_check(point_zone3, 'MLr_vmm', model_data)
        self.assertFalse(boolean,"Error in magnitude_check: Point inside zone3 with MLr_vmm does not been detected")
        self.assertTrue(correct_mag == 'MLr_3', "Error in magnitude_check: Magnitude marked as correct is NOT MLr_3")
        # Point inside zona4 but OUTSIDE Modelo_CARMA zone
        point_zone4 = (-76.04, 8.48)
        self.assertTrue(ut.magnitude_check(point_zone4, 'MLr_4', model_data)[0],
                        "Error in magnitude_check: Point inside zone4 with MLr_4 got False")
        boolean, correct_mag = ut.magnitude_check(point_zone4, 'MLr_3', model_data)
        self.assertFalse(boolean, "Error in magnitude_check: Point inside zone4 with MLr_3 does not been detected")
        self.assertTrue(correct_mag == 'MLr_4', "Error in magnitude_check: Magnitude marked as correct is NOT MLr_4")
        # Point inside zona5
        point_zone5 = (-69.7311, 2.3815)
        self.assertTrue(ut.magnitude_check(point_zone5, 'MLr_5', model_data)[0],
                        "Error in magnitude_check: Point inside zone1 with MLr_1 got False")
        boolean, correct_mag = ut.magnitude_check(point_zone5, 'MLr_vmm', model_data)
        self.assertFalse(boolean,"Error in magnitude_check: Point inside zone5 with MLr_vmm does not been detected")
        self.assertTrue(correct_mag == 'MLr_5', "Error in magnitude_check: Magnitude marked as correct is NOT MLr_5")
        # Point inside zona_vmm and zone2
        point_zone_vmm = (-73.9294, 5.9988)  # Point inside zona_vmm and zone2
        self.assertTrue(ut.magnitude_check(point_zone_vmm, 'MLr_vmm', model_data)[0],
                        "Error in magnitude_check: Point inside zone1 with MLr_1 got False")
        boolean, correct_mag = ut.magnitude_check(point_zone_vmm, 'MLr_2', model_data)
        self.assertFalse(boolean,"Error in magnitude_check: Point inside zone_vmm with MLr_3 does not been detected")
        self.assertTrue(correct_mag == 'MLr_vmm', "Error in magnitude_check: Magnitude marked as correct is NOT MLr_vmm")
        # Point outside all the zones
        point_outside = (-79, 1.4)
        boolean, correct_mag = ut.magnitude_check(point_outside, 'MLr_2', model_data)
        self.assertFalse(boolean, "Error in magnitude_check: Point outside all zones should not be detected")
        self.assertTrue(correct_mag is None, "Error in magnitude check: Should not have a correct magnitude return value for points outside all zones")

if __name__ == '__main__':
    unittest.main()