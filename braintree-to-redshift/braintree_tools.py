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
        filename='braintree_import.csv',
        columns=False,
        type='transactions',
        end_date=date.today()):
    print('create import file called')
    import_file = open(files_dir + filename, 'w')
    print('import file opened')
    if type == 'transactions':
        print('starting transactions dictionary call')
        data_dict = make_transactions_dictionary(end_date)
        print('data dict created')
        if not data_dict:
            print("Could not retrieve transaction data")
            return False
    elif type == 'disputes':
        data_dict = make_disputes_dictionary(end_date, days)
        # print('data dict created')
        if not data_dict:
            print("Could not retrieve transaction data")
            return False
    csv_file = csv.writer(import_file, delimiter="|")
    csv_file.writerow(columns)
    for key, value in data_dict.items():
        csv_file.writerow(value)
    import_file.close()
    return True

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
    -- Drop the staging table
    DROP TABLE IF EXISTS %(staging_table_name)s;

    CREATE TABLE %(staging_table_name)s (LIKE %(table_name)s);

    -- Load data into the staging table
    COPY %(staging_table_name)s (%(column_names)s)
    FROM 's3://%(s3_bucket)s/%(s3_bucket_dir)s/%(filename)s'
    CREDENTIALS 'aws_access_key_id=%(aws_access_key)s;aws_secret_access_key=%(aws_secret_key)s'
    FILLRECORD
    delimiter '|'
    IGNOREHEADER 1;

    -- Update records
    UPDATE %(table_name)s
    SET %(columns_to_stage)s
    FROM %(staging_table_name)s s
    WHERE %(table_key)s = %(staging_table_key)s;

    -- Insert records
    INSERT INTO %(table_name)s
    SELECT s.* FROM %(staging_table_name)s s LEFT JOIN %(table_name)s
    ON %(staging_table_key)s = %(table_key)s
    WHERE %(table_key)s IS NULL;

    -- End transaction
    END;""" % {
        'staging_table_name': staging_table_name,
        'table_name': table_name,
        'staging_table_key': staging_table_key,
        'table_key': table_key,
        'column_names': column_names,
        'columns_to_stage': columns_to_stage,
        's3_bucket': s3_bucket,
        's3_bucket_dir': s3_bucket_dir,
        'filename': filename,
        'aws_access_key': aws_access_key,
        'aws_secret_key': aws_secret_key,
    }
    if getattr(settings, 'DEBUG', False):
        print(command)
    rsm.db_query(command)
