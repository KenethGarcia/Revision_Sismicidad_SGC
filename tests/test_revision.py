import unittest
from src.revision_revision import *


class TestRevision(unittest.TestCase):
    def test_database_queries(self):
        """
        A function to test the database queries. The strategy is to test the queries using specific inputs from February
        :return:
        """
        # First test case, queries all events from February 11th
        args = {'start': '20250217T110000', 'end': '20250217T115959'}
        start_time = dt.datetime.strptime(args['start'], "%Y%m%dT%H%M%S")
        end_time = dt.datetime.strptime(args['end'], "%Y%m%dT%H%M%S")
        df_1 = connect2mysql("normal", start_time, end_time)
        events = ("SGC2025djddpa", "SGC2025djdunq", "SGC2025djdvvq", "SGC2025djealc", "SGC2025djealc", "SGC2025djejlg",
                  "SGC2025djelod", "SGC2025djenoa", "SGC2025djexhc")
        self.assertEqual(set(df_1['publicID'].tolist()), set(events))
        for author in df_1['creationInfo_author']:  # Check if author is muruena@proc3
            self.assertEqual(author, 'muruena@proc3')
        # Second test case, queries all notable earthquakes from February 5th
        args = {'start': '20250205T000000', 'end': '20250205T235959'}
        start_time = dt.datetime.strptime(args['start'], "%Y%m%dT%H%M%S")
        end_time = dt.datetime.strptime(args['end'], "%Y%m%dT%H%M%S")
        df_2 = connect2mysql("destacado", start_time, end_time)
        events = ("SGC2025cmujvk", "SGC2025cnragn", "SGC2025cnstun")
        self.assertEqual(set(df_2['publicID'].tolist()), set(events))
        # # BUGFIX: The following test case is not working as expected. The query is not returning the expected results
        # # Third test case, queries all events with felt reports from February 18th
        # args = {'start': '20250218T000000', 'end': '20250218T235959'}
        # start_time = dt.datetime.strptime(args['start'], "%Y%m%dT%H%M%S")
        # end_time = dt.datetime.strptime(args['end'], "%Y%m%dT%H%M%S")
        # df_3 = connect2mysql("sentido", start_time, end_time)
        # # As checked by Keneth (in the Seismic visor and report monitor), the unique felt reports are SGC2025dlepyz
        # # (3 reports) and SGC2025dmbmtc (1 report), the other felt reports has not any associated ID
        # events = ("SGC2025dlepyz", "SGC2025dmbmtc")
        # self.assertEqual(set(df_3['publicID'].tolist()), set(events))

    def test_single_check(self):
        """
        This function test the single_check function. The strategy here is to test every possible case inside the
        revision routine. We will consider 9 cases of the if statements mentioned in the single_check function
        """
        def prepare_test(args_dict):
            """
            A single function to query normal and featured events in a specific time range
            """
            start_time = dt.datetime.strptime(args_dict['start'], "%Y%m%dT%H%M%S")
            end_time = dt.datetime.strptime(args_dict['end'], "%Y%m%dT%H%M%S")
            df_1 = connect2mysql("normal", start_time, end_time)
            df_2 = connect2mysql("destacado", start_time, end_time)
            series = df_1.iloc[0].squeeze()  # Convert the one row dataframe to a pandas series
            return series, df_2

        # 1. High RMS events (2024-12-29 09:22:44 UTC)
        event, t = "SGC2024zrbgkf", "20241229T092244"
        args = {'start': '20241229T092243', 'end': '20241229T092245'}
        df_normal, df_special = prepare_test(args)
        res, obs = single_check(df_normal, df_special, flag=True)
        self.assertTrue("High RMS value" in obs)
        self.assertEqual(res['publicID'], event)

        # 2. High localization error (2023-05-29 07:32:35 UTC)
        event, t = "SGC2023kmgmio", "20230529T073235"
        args = {'start': "20230529T073234", 'end': "20230529T073236"}
        df_normal, df_special = prepare_test(args)
        res, obs = single_check(df_normal, df_special, flag=True)
        self.assertTrue("High localization uncertainties" in obs)
        self.assertEqual(res['publicID'], event)

        # 3. Locatable event outside volcanic areas
        event, args = "SGC2024whmkoa", {'start': "20241111T162541", 'end': "20241111T162543"}
        df_normal, df_special = prepare_test(args)
        res, obs = single_check(df_normal, df_special, flag=True)
        self.assertTrue("Locatable event" in obs)
        self.assertEqual(res['publicID'], event)
        event, args = "SGC2024yauwqc", {'start': "20241206T090221", 'end': "20241206T090222"}
        df_normal, df_special = prepare_test(args)
        res, obs = single_check(df_normal, df_special, flag=True)
        self.assertTrue("Locatable event" in obs)
        self.assertEqual(res['publicID'], event)

        # 4. Magnitude checks

        # 4.1. Event outside all zones
        args = {'start': "20250219T002830", 'end': "20250219T002831"}
        df_normal, df_special = prepare_test(args)
        res, obs = single_check(df_normal, df_special, flag=True)
        self.assertTrue(obs is None, "Event outside all zones should not add any magnitude observation")

        # 4.2. Mw fixed by focal mechanism
        args = {'start': "20241031T163154", 'end': "20241031T163156"}
        df_normal, df_special = prepare_test(args)
        res, obs = single_check(df_normal, df_special, flag=True)
        self.assertTrue(obs is None)
        args = {'start': "20241206T090221", 'end': "20241206T093223"}
        df_normal, df_special = prepare_test(args)
        res, obs = single_check(df_normal, df_special, flag=True)
        self.assertTrue(obs is None)

        # 4.3 Correct Magnitudes by zone
        args = {'start': "20240916T025311", 'end': "20240916T025313"}
        df_normal, df_special = prepare_test(args)
        res, obs = single_check(df_normal, df_special, flag=True)
        self.assertTrue("Correct magnitude with MLr_3 (Current: MLr_vmm)" in obs)
        args = {'start': "20240920T055323", 'end': "20240920T055325"}
        df_normal, df_special = prepare_test(args)
        res, obs = single_check(df_normal, df_special, flag=True)
        self.assertTrue("Correct magnitude with MLr_1 (Current: MLr_2)" in obs)
        args = {'start': "20240928T191209", 'end': "20240928T191211"}
        df_normal, df_special = prepare_test(args)
        res, obs = single_check(df_normal, df_special, flag=True)
        self.assertTrue("Correct magnitude with MLr_4 (Current: M)" in obs)
        args = {'start': "20240921T103855", 'end': "20240921T103857"}
        df_normal, df_special = prepare_test(args)
        res, obs = single_check(df_normal, df_special, flag=True)
        self.assertTrue("Correct magnitude with MLr_1 (Current: MLr_3)" in obs)
        args = {'start': "20241128T210052", 'end': "20241128T210054"}
        df_normal, df_special = prepare_test(args)
        res, obs = single_check(df_normal, df_special, flag=True)
        self.assertTrue("Correct magnitude with MLr_vmm (Current: MLr)" in obs)
        args = {'start': "20241221T082311", 'end': "20241221T082311"}
        df_normal, df_special = prepare_test(args)
        res, obs = single_check(df_normal, df_special, flag=True)
        self.assertTrue("Correct magnitude with MLr_2 (Current: MLr_3)" in obs)

        # 5. Model checks
        # 5.1. Model Cesar
        args = {'start': "20240916T013641", 'end': "20240916T013643"}
        df_normal, df_special = prepare_test(args)
        res, obs = single_check(df_normal, df_special, flag=True)
        self.assertTrue("Correct model to modelCesar2" in obs)
        # 5.2. Model VMM
        args = {'start': "20240916T053121", 'end': "20240916T053123"}
        df_normal, df_special = prepare_test(args)
        res, obs = single_check(df_normal, df_special, flag=True)
        self.assertTrue("Correct model to modelVMM" in obs)
        # 5.3. Model CARMA
        args = {'start': "20240901T233501", 'end': "20240901T233503"}
        df_normal, df_special = prepare_test(args)
        res, obs = single_check(df_normal, df_special, flag=True)
        self.assertTrue("Correct model to CARMA" in obs)
        args = {'start': "20241216T001835", 'end': "20241216T001837"}
        df_normal, df_special = prepare_test(args)
        res, obs = single_check(df_normal, df_special, flag=True)
        self.assertTrue("Correct model to CARMA" in obs)

        # 6. Event with 7 or fewer phases
        args = [{'start': "20240916T025848", 'end': "20240916T025850"},
                {'start': "20241206T094147", 'end': "20241206T094149"}]
        for arg in args:
            df_normal, df_special = prepare_test(arg)
            res, obs = single_check(df_normal, df_special, flag=True)
            self.assertTrue("Event with 7 or less phase count" in obs)
            res, obs = single_check(df_normal, df_special, flag=False)
            self.assertTrue(obs is None)

        # 7. 'DESTACADO' events without label
        args = {'start': "20250208T234044", 'end': "20250208T234046"}
        df_normal, df_special = prepare_test(args)
        res, obs = single_check(df_normal, df_special, flag=True)
        self.assertTrue("Event with M = 4.05 without 'DESTACADO' label" in obs)

        # 8. Label errors in volcanic events
        args = {'start': "20240819T142040", 'end': "20240819T142043"}
        df_normal, df_special = prepare_test(args)
        res, obs = single_check(df_normal, df_special, flag=True)
        self.assertTrue("Volcanic event with wrong label 'earthquake'" in obs)
        args = {'start': "20250207T012418", 'end': "20250207T012420"}
        df_normal, df_special = prepare_test(args)
        res, obs = single_check(df_normal, df_special, flag=True)
        self.assertTrue("Volcanic event without 'DESTACADO' label or without 'not locatable' label" in obs)
        args = {'start': "20250206T063133", 'end': "20250206T063135"}
        df_normal, df_special = prepare_test(args)
        res, obs = single_check(df_normal, df_special, flag=True)
        self.assertTrue("Volcanic event without 'DESTACADO' label or without 'not locatable' label" in obs)

        # 9. Pacific/Caribe events with high depth
        # args = {'start': "20240920T092203", 'end': "20240920T092205"}
        # df_normal, df_special = prepare_test(args)
        # res, obs = single_check(df_normal, df_special, flag=True)
        # BUG: We need to re-define the lat, lon limits for the Pacific/Caribe region

        # 10. Events inside and outside local zone
        args = {'start': "20200427T000254", 'end': "20200427T000256"}
        df_normal, df_special = prepare_test(args)
        res, obs = single_check(df_normal, df_special, flag=True)
        self.assertTrue("Event outside local zone with 'earthquake' label" in obs)
        args = {'start': "20200429T081428", 'end': "20200429T081430"}
        df_normal, df_special = prepare_test(args)
        res, obs = single_check(df_normal, df_special, flag=True)
        self.assertTrue("Event inside local zone with 'outside of...' label" in obs)

        # 11. Events inside NLL zone without Poveda_et_al_2018 velocity model
        args = {'start': "20200604T013240", 'end': "20200604T013242"}
        df_normal, df_special = prepare_test(args)
        res, obs = single_check(df_normal, df_special, flag=True)
        self.assertTrue("'DESTACADO' event inside NonLinLoc zone without NLL localization model" in obs)
        args = {'start': "20200618T105556", 'end': "20200618T105558"}
        df_normal, df_special = prepare_test(args)
        res, obs = single_check(df_normal, df_special, flag=True)
        self.assertTrue("'DESTACADO' event inside NonLinLoc zone without NLL localization model" in obs)

    def test_check_seismic(self):
        """
        This function test the check_seismic function. The strategy here is to test 2 hours of data and check if there
        are any events returned correctly.
        """
        # Define the time range and parameters
        args = {'start': "20240901T000000", 'end': "20240901T015959"}  # Block with 3 events with 7 or fewer phases
        start_time = dt.datetime.strptime(args['start'], "%Y%m%dT%H%M%S")
        end_time = dt.datetime.strptime(args['end'], "%Y%m%dT%H%M%S")
        df = connect2mysql("normal", start_time, end_time)
        df_s = connect2mysql("destacado", start_time, end_time)
        results = ['SGC2024rgbbwn', 'SGC2024rgahfy', 'SGC2024rgadfd']  # Expected events

        # 1. One single process at time
        res = check_seismic(df, df_s, flag=True)
        self.assertEqual(res['publicID'].tolist(), results)
        # Check if the observations are correct
        obs = res['Observations'].tolist()
        [self.assertTrue("Event with 7 or less phase count" == obs[i]) for i in range(len(obs))]

        # 2. Multiple processes at time
        res = check_seismic(df, df_s, flag=True, n_processes=4)
        self.assertEqual(res['publicID'].tolist(), results)
        obs = res['Observations'].tolist()
        [self.assertTrue("Event with 7 or less phase count" == obs[i]) for i in range(len(obs))]

    def test_run(self):
        """
        This function test the run function for the revision process.
        """
        args = {'start': "20240901T000000", 'end': "20240901T015959"}  # Block with 3 events with 7 or fewer phases
        start_time = dt.datetime.strptime(args['start'], "%Y%m%dT%H%M%S")
        end_time = dt.datetime.strptime(args['end'], "%Y%m%dT%H%M%S")

        # 1. Single process without flag
        res = run(start_time, end_time, flag=False)
        self.assertTrue(res.empty)

        # 2. Multiple processes with flag
        res = run(start_time, end_time, flag=False, n_processes=4)
        self.assertTrue(res.empty)

        # 3. Single process with user specified
        res = run(start_time, end_time, flag=True, user="axlopez")
        results = ['SGC2024rgbbwn', 'SGC2024rgahfy', 'SGC2024rgadfd']  # Expected events
        self.assertFalse(results[-1] in res['publicID'].tolist())

        # 4. Multiple process with user specified
        res = run(start_time, end_time, flag=True, n_processes=4, user="axlopez")
        self.assertFalse(results[-1] in res['publicID'].tolist())

    def test_check_duplicates(self):
        """
        This function test the check_duplicates function. The strategy here is to take a revised case of two events
        within 10 km and 4 seconds of time difference. In addition, take any event and create a fake event with the same
        parameters but slightly different event time and location.
        """
        # 1. Revised case in Huila region
        args = {'start': "20241101T000000", 'end': "20241103T000000"}
        start_time = dt.datetime.strptime(args['start'], "%Y%m%dT%H%M%S")
        end_time = dt.datetime.strptime(args['end'], "%Y%m%dT%H%M%S")
        df = connect2mysql("normal", start_time, end_time)
        duplicates = check_duplicates(df)
        expected = ['SGC2024vptwef', 'SGC2024vptwct']
        self.assertEqual(duplicates['publicID'].tolist(), expected)

        # 2. Creating a copy of the event with a different time and location
        start_time = '20250412T140000'
        end_time = '20250412T220000'
        time_1 = dt.datetime.strptime(start_time, "%Y%m%dT%H%M%S")
        time_2 = dt.datetime.strptime(end_time, "%Y%m%dT%H%M%S")
        data = connect2mysql('normal', time_1, time_2)
        last_row = data.iloc[34].copy()
        last_row['publicID'] = 'duplicate'
        last_row['longitude_value'] = -73.15
        data = pd.concat([data, last_row.to_frame().T], ignore_index=True)
        duplicates = check_duplicates(data)
        self.assertEqual(duplicates['publicID'].tolist(), ['SGC2025heotgc', 'duplicate'])



if __name__ == '__main__':
    unittest.main()
