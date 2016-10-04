#!/usr/bin/env python3.5
import pandas as pd
import sqlalchemy

import unittest
import pdb
from collections import OrderedDict
from decimal import Decimal

from features import compute_bursts, FeatureStorage


def db_helper(db, table_name, feature_names):
    """Helper function for testing a table in the database. Takes some
    column(s) in a table and generates a dict.

    Args:
        db [FeatureStorage object]: database object
        table_name [string]: name of the table to test
        feature_names [list of strings]: names of the columns to test

    Returns:
        actual_output [dict]: Contains the actual output in a dict that 
            can be easily compared with the expected output dict defined
            in the test
    """

    select_query = "SELECT * FROM {} ORDER BY exampleid; ".format(table_name)
    result = db.engine.execute(select_query)

    # Ensure we preserve the order of the columns with an OrderedDict
    actual_output = OrderedDict({'exampleid': []})
    for feature_name in feature_names:
        actual_output.update({feature_name: []})

    column_names = ['exampleid'] + feature_names

    for row in result:
        for column_index, column_name in enumerate(column_names):
            # SQLAlchemy will by default return decimal.Decimal objects
            # which we want to convert to floats
            if isinstance(row[1], Decimal):
                actual_output[column_name].append(float(row[column_index]))
            else:
                actual_output[column_name].append(row[column_index])
    return dict(actual_output)


class BurstGenerationTest(unittest.TestCase):
    def test_no_bursts(self):
        df = pd.DataFrame({'ingoing': [True, True, True]})
        bursts, ranks = compute_bursts(df)
        self.assertEqual(bursts, [])

    def test_all_burst(self):
        df = pd.DataFrame({'ingoing': [False, False, False]})
        bursts, ranks = compute_bursts(df)
        self.assertEqual(bursts, [3])

    def test_two_bursts(self):
        df = pd.DataFrame({'ingoing': [True, True, False, False, True,
                                       True, False, False, False]})
        bursts, ranks = compute_bursts(df)
        self.assertEqual(bursts, [2, 3])


class RawFeatureGenerationTest(unittest.TestCase):
    """Tests for all the feature generation methods that start
    with the raw.frontpage_traces table"""
    def setUp(self):
        self.db = FeatureStorage(test_db=True)

        clean_up_features_schema = ("DROP SCHEMA IF EXISTS features CASCADE; ")
        self.db.engine.execute(clean_up_features_schema)

        instantiate_features_schema = ("CREATE SCHEMA features; ")
        self.db.engine.execute(instantiate_features_schema)

        insert_test_data_traces = ("INSERT INTO raw.frontpage_traces "
        "(cellid, exampleid, ingoing, circuit, stream, command, "
        "length, t_trace) VALUES "
        "(508, 9, 't', 3725647749, 0, 'EXTENDED2(15)', 66, 1472598678.735375),"
        "(509, 9, 'f', 3725647749, 0, 'EXTEND2(14)', 119, 1472598678.909463),"
        "(510, 9, 't', 3725647749, 0, 'EXTENDED2(15)', 66, 1472598679.262226),"
        "(922, 10, 'f', 3418218064, 59159, 'DATA(2)', 498, 1472598739.562103),"
        "(923, 10, 'f', 3418218064, 59159, 'DATA(2)', 424, 1472598739.562176),"
        "(924, 10, 'f', 3418218064, 59159, 'DATA(2)', 289, 1472598739.571273);")
        self.db.engine.execute(insert_test_data_traces)

        insert_test_data_examples = ("INSERT INTO raw.frontpage_examples "
        "(exampleid, hsid, crawlid, t_scrape) VALUES "
        "(9, 1, 1, '2016-08-30 19:11:38.869066'), "
        "(10, 2, 1, '2016-08-30 19:11:39.879066');")
        self.db.engine.execute(insert_test_data_examples)
        return None

    def test_aggregate_cell_numbers(self):
        table_name = self.db.generate_table_cell_numbers()
        expected_output = {'exampleid': [9, 10],
                           'total_number_of_incoming_cells': [2, 0],
                           'total_number_of_outgoing_cells': [1, 3],
                           'total_number_of_cells': [3, 3]}

        actual_output = db_helper(self.db, table_name,
            ['total_number_of_incoming_cells',
             'total_number_of_outgoing_cells', 'total_number_of_cells'])

        self.assertEqual(expected_output, actual_output)

    def test_aggregate_cell_timings(self):
        table_name = self.db.generate_table_cell_timings()
        expected_output = {'exampleid': [9, 10],
                           'total_elapsed_time': [0.526851, 0.00917]}

        actual_output = db_helper(self.db, table_name, ['total_elapsed_time'])

        self.assertEqual(expected_output, actual_output)

    def test_interpacket_timings(self):
        table_name = self.db.generate_table_interpacket_timings()
        expected_output = {'exampleid': [9, 10],
                           'mean_intercell_time': [0.2634255, 0.004585],
                           'standard_deviation_intercell_time': [0.1263423041285064,
                           0.006380931593427405]}

        actual_output = db_helper(self.db, table_name,
            ['mean_intercell_time', 'standard_deviation_intercell_time'])

        self.assertEqual(expected_output, actual_output)

    def test_initial_cell_directions(self):
        table = self.db.generate_table_initial_cell_directions(num_cells=2)
        expected_output = {'exampleid': [9, 10],
                           'direction_cell_1': [0, 1],
                           'direction_cell_2': [1, 1]}

        actual_output = db_helper(self.db, table,
                                  ['direction_cell_1',
                                   'direction_cell_2'])

        self.assertEqual(expected_output, actual_output)

    def test_outgoing_cell_positions(self):
        table_name = self.db.generate_table_outgoing_cell_positions(num_cells=2)
        expected_output = {'exampleid': [9, 10],
                           'outgoing_cell_position_1': [2, 1],
                           'outgoing_cell_position_2': [None, 2]}

        actual_output = db_helper(self.db, table_name,
                                  ['outgoing_cell_position_1',
                                   'outgoing_cell_position_2'])

        self.assertEqual(expected_output, actual_output)

    def test_outgoing_cell_positions_differences(self):
        table_name = self.db.generate_table_outgoing_cell_positions_differences(num_cells=2)
        expected_output = {'exampleid': [9, 10],
                           'outgoing_cell_position_difference_1': [None, 1],
                           'outgoing_cell_position_difference_2': [None, 1]}

        actual_output = db_helper(self.db, table_name,
                                  ['outgoing_cell_position_difference_1',
                                   'outgoing_cell_position_difference_2'])

        self.assertEqual(expected_output, actual_output)

    def test_binned_counts(self):
        table_name = self.db.generate_table_binned_counts(num_features=2,
                                                          size_window=2)
        expected_output = {'exampleid': [9, 10],
                           'num_outgoing_packet_in_window_1_of_size_2': [1, 2],
                           'num_outgoing_packet_in_window_2_of_size_2': [None, 1]}

        actual_output = db_helper(self.db, table_name,
                                  ['num_outgoing_packet_in_window_1_of_size_2',
                                   'num_outgoing_packet_in_window_2_of_size_2'])

        self.assertEqual(expected_output, actual_output)

    def test_burst_table_creation(self):
        self.db.create_bursts()
        query = "SELECT * FROM public.current_bursts ORDER BY exampleid; "
        result = self.db.engine.execute(query)
        expected_output = {'exampleid': [9, 10],
                           'burst_length': [1, 3],
                           'burst_rank': [1, 1]}
        actual_output = {'exampleid': [],
                         'burst_length': [],
                         'burst_rank': []}
        for row in result:
            actual_output['exampleid'].append(row[1])
            actual_output['burst_length'].append(row[2])
            actual_output['burst_rank'].append(row[3])
        self.assertEqual(expected_output, actual_output)

    def tearDown(self):
        clean_up_test_data_traces = ("DELETE FROM raw.frontpage_traces;")
        self.db.engine.execute(clean_up_test_data_traces)
        clean_up_test_data_examples = ("DELETE FROM raw.frontpage_examples;")
        self.db.engine.execute(clean_up_test_data_examples)
        clean_up_features_schema = ("DROP SCHEMA IF EXISTS features CASCADE; ")
        self.db.engine.execute(clean_up_features_schema)
        self.db.drop_table("public.current_bursts")
        return None


class BurstFeatureGeneration(unittest.TestCase):
    """Tests for the feature generation methods
    that begin with the bursts table"""
    def setUp(self):
        self.db = FeatureStorage(test_db=True)

        clean_up_features_schema = ("DROP SCHEMA IF EXISTS features CASCADE; ")
        self.db.engine.execute(clean_up_features_schema)

        instantiate_features_schema = ("CREATE SCHEMA features; ")
        self.db.engine.execute(instantiate_features_schema)

        create_bursts_table = ("CREATE TABLE public.current_bursts ("
                               "burstid SERIAL PRIMARY KEY, "
                               "burst BIGINT, "
                               "exampleid BIGINT, "
                               "rank BIGINT);")
        self.db.engine.execute(create_bursts_table)

        insert_test_bursts = ("INSERT INTO public.current_bursts "
                              "(burstid, burst, exampleid, rank) VALUES "
                              "(33653, 1, 9, 22), "
                              "(33643, 9, 9, 12), "
                              "(33649, 1, 9, 18), "
                              "(33650, 3, 9, 19), "
                              "(2961, 2, 10, 11), "
                              "(2954, 8, 10, 4), "
                              "(2953, 1, 10, 3);")
        self.db.engine.execute(insert_test_bursts)
        return None

    def test_burst_length_aggregates(self):
        table_name = self.db.generate_table_burst_length_aggregates()
        expected_output = {'exampleid': [9.0, 10.0],
                           'mean_burst_length': [3.5, 3.6666666666666665],
                           'num_bursts': [4.0, 3.0],
                           'max_burst_length': [9.0, 8.0]}

        actual_output = db_helper(self.db, table_name,
                                  ['mean_burst_length', 'num_bursts',
                                   'max_burst_length'])
        self.assertEqual(expected_output, actual_output)

    def test_burst_length_binned_bursts(self):
        table_name = self.db.generate_table_binned_bursts(lengths=[2, 5])
        expected_output = {'exampleid': [9, 10],
                           'num_bursts_with_length_gt_2': [2, 1],
                           'num_bursts_with_length_gt_5': [1, 1]}

        actual_output = db_helper(self.db, table_name,
                                  ['num_bursts_with_length_gt_2',
                                   'num_bursts_with_length_gt_5'])
        self.assertEqual(expected_output, actual_output)

    def test_burst_lengths(self):
        table_name = self.db.generate_table_burst_lengths(num_bursts=2)
        expected_output = {'exampleid': [9, 10],
                           'length_burst_1': [1, 2],
                           'length_burst_2': [9, 8]}

        actual_output = db_helper(self.db, table_name,
                                  ['length_burst_1', 'length_burst_2'])
        self.assertEqual(expected_output, actual_output)

    def tearDown(self):
        self.db.drop_table("public.current_bursts")
        clean_up_features_schema = ("DROP SCHEMA IF EXISTS features CASCADE; ")
        self.db.engine.execute(clean_up_features_schema)
        return None
