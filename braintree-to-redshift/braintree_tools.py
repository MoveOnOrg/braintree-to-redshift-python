#!/usr/bin/python
# coding: utf-8
""" Download data and create CSV. Upload CSV to S3. Import to Redshift.
"""

import sys
import os
import boto
from datetime import date, datetime, timedelta
from boto.s3.connection import Location
local_settings_path = os.path.join(os.getcwd(),"settings.py")
if os.path.exists(local_settings_path):
    import imp
    settings = imp.load_source('settings', local_settings_path)

from redshift import RedShiftMediator

from braintree_connection import (
    make_disputes_dictionary, make_transactions_dictionary)
from settings import (
    aws_access_key, aws_secret_key, s3_bucket, s3_bucket_dir, s3_region, files_dir,
    test)
import settings
import csv

rsm = None

def create_import_file(
        days=5,
        date=datetime.now(),
        hours=6,
        filename='braintree_import.csv',
        columns=False,
        type='new_transactions'):
    # import_file = open(files_dir + filename, 'w')
    # print('import file opened')
    print('number of days')
    print(days)
    if type == 'new_transactions' or type == 'disbursed':
        print('starting transactions dictionary call')
        data_dict = make_transactions_dictionary(end_time = date, days =  days, hours = hours, type = type)
        print('data dict created')
        if not data_dict:
            print("Could not retrieve transaction data")
            return False
    elif type == 'disputes':
        data_dict = make_disputes_dictionary(end_date = date, days = days)
        # print('data dict created')
        if not data_dict:
            print("Could not retrieve transaction data")
            return False
    return data_dict
    # csv_file = csv.writer(import_file, delimiter="|")
    # csv_file.writerow(columns)
    # for key, value in data_dict.items():
    #     csv_file.writerow(value)
    # import_file.close()
    # return import_file

def upload_to_s3(filename='braintree_import.csv'):
    conn = boto.connect_s3(aws_access_key, aws_secret_key)
    bucket = conn.lookup(s3_bucket)
    k = boto.s3.key.Key(bucket)
    k.key = '/' + s3_bucket_dir + '/' + filename
    k.set_contents_from_filename(files_dir + filename)
    print("s3 destination is")
    print(k.key)

def update_redshift(lines, errors, header, context):
    global rsm
    if rsm is None:
        rsm = RedShiftMediator(settings)
    table_name = transactions['tablename']
    columns = transactions['columns']
    primary_key = transactions['primary_key']
    staging_table_name = table_name + "_staging"
    filename = transactions['filename']
    column_names = ", ".join(columns)
    columns_to_stage = ", ".join([(column + " = s." + column) for column in columns])
    table_key = table_name + "." + primary_key
    staging_table_key = "s." + primary_key

    command = """-- Create a staging table
    CREATE TABLE %s (LIKE %s);

    -- Load data into the staging table
    COPY %s (%s)
    FROM %s
    CREDENTIALS 'aws_access_key_id=%s;aws_secret_access_key=%s'
    FILLRECORD
    delimiter '|'
    IGNOREHEADER 1;

    -- Update records
    UPDATE %s
    SET %s
    FROM %s s
    WHERE %s = %s;

    -- Insert records
    INSERT INTO %s
    SELECT s.* FROM %s s LEFT JOIN %s
    ON %s = %s
    WHERE %s IS NULL;

    -- Drop the staging table
    DROP TABLE %s;

    -- End transaction
    END;"""%(
        staging_table_name, table_name, staging_table_name, column_names,
        lines, aws_access_key, aws_secret_key,
        table_name, columns_to_stage, staging_table_name, table_key,
        staging_table_key, table_name, staging_table_name, table_name,
        staging_table_key, table_key, table_key, staging_table_name)

    rsm.db_query(command)
