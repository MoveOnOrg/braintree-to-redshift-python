#!/usr/bin/python
# coding: utf-8
""" Download data and create CSV. Upload CSV to S3. Import to Redshift.
"""

import sys
import os
import boto
from itertools import islice

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
        filename='braintree_import.csv',
        columns=False,
        type='transactions'):
    print('create import file called')
    import_file = open(files_dir + filename, 'w')
    print('import file opened')
    if type == 'transactions':
        print('starting transactions dictionary call')
        data_dict = make_transactions_dictionary(date.today())
        print('data dict created')
        if not data_dict:
            print("Could not retrieve transaction data")
            return False
    elif type == 'disputes':
        data_dict = make_disputes_dictionary(date.today(), days)
        if not data_dict:
            print("Could not retrieve transaction data")
            return False


    csv_file = csv.writer(import_file, delimiter="|")
    csv_file.writerow(columns)
    for key, value in data_dict.items():
        csv_file.writerow(value)
    import_file.close()
    return True

def chunks(data, SIZE=10000):
    it = iter(data)
    for i in xrange(0, len(data), SIZE):
        yield {k:data[k] for k in islice(it, SIZE)}

def upload_to_s3(filename='braintree_import.csv'):
    conn = boto.connect_s3(aws_access_key, aws_secret_key)
    bucket = conn.lookup(s3_bucket)
    k = boto.s3.key.Key(bucket)
    k.key = '/' + s3_bucket_dir + '/' + filename
    k.set_contents_from_filename(files_dir + filename)
    print("s3 destination is")
    print(k.key)

def update_redshift(table_name, columns, primary_key, filename):
    global rsm
    if rsm is None:
        rsm = RedShiftMediator(settings)
    staging_table_name = table_name + "_staging"
    column_names = ", ".join(columns)
    columns_to_stage = ", ".join([(column + " = s." + column) for column in columns])
    table_key = table_name + "." + primary_key
    staging_table_key = "s." + primary_key

    command = """-- Create a staging table
    DROP TABLE IF EXISTS %s;
    CREATE TABLE %s (LIKE %s);

    -- Load data into the staging table
    COPY %s (%s)
    FROM 's3://%s/%s/%s'
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
        staging_table_name, staging_table_name, table_name, staging_table_name, column_names,
        s3_bucket, s3_bucket_dir, filename, aws_access_key, aws_secret_key,
        table_name, columns_to_stage, staging_table_name, table_key,
        staging_table_key, table_name, staging_table_name, table_name,
        staging_table_key, table_key, table_key, staging_table_name)

    rsm.db_query(command)
