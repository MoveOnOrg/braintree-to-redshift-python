#!/usr/bin/python
# -*- coding: utf-8 -*-
""" Loop through the data types and run the other functions to
    download, format, upload and import data for each data type.
"""

import sys
import os
local_settings_path = os.path.join(os.getcwd(),"settings.py")
if os.path.exists(local_settings_path):
    import imp
    settings = imp.load_source('settings', local_settings_path)

from braintree_tools import create_import_file, upload_to_s3, update_redshift
from bigsqueeze import distribute_task_csv

from time import gmtime, strftime
from datetime import datetime
from settings import (
    test, disputes, files_dir, s3_bucket, s3_bucket_dir, transactions)

def main(event='', context=''):
    print(strftime("%Y-%m-%d %H:%M:%S", gmtime()))
    # 'disputes', 'new_transactions', 'disbursed'
    transaction_type = 'disbursed'
    if transaction_type == 'new_transactions':
        created_file = create_import_file(
            days=4,
            date=datetime.now(),
            filename=transactions['filename'],
            columns=transactions['columns'],
            hours=1,
            type='new_transactions'
        )
        print("created %s " %(files_dir + transactions['filename']))
        upload_to_s3(transactions['filename'])
        print(
            "uploaded %s to s3 bucket s3://%s/%s"
            %(files_dir + transactions['filename'], s3_bucket, s3_bucket_dir))
        update_redshift(transactions['tablename'], transactions['columns'], transactions['primary_key'], transactions['filename'])
        print("updated redshift table " + transactions['tablename'])
        print("Done with transactions!")

        print(strftime("%Y-%m-%d %H:%M:%S", gmtime()))
    elif transaction_type == 'disbursed':
        created_file = create_import_file(
            days=4,
            date=datetime.now(),
            filename=transactions['filename'],
            columns=transactions['columns'],
            hours=1,
            type='disbursed'
        )
        print("created %s " %(files_dir + transactions['filename']))
        # print(
        #     "uploaded %s to s3 bucket s3://%s/%s"
        #     %(files_dir + transactions['filename'], s3_bucket, s3_bucket_dir))
        distribute_task_csv(created_file, update_redshift, s3_bucket, catch=True)
        # update_redshift(transactions['tablename'], transactions['columns'], transactions['primary_key'], transactions['filename'])
        print("updated redshift table " + transactions['tablename'])
        print("Done with transactions!")
        print(strftime("%Y-%m-%d %H:%M:%S", gmtime()))
    elif transaction_type == 'disputes':
        print('Importing disputes')
        print('creating file')
        created_file = create_import_file(
            date=datetime.now(),
            filename=disputes['filename'],
            columns=disputes['columns'],
            type='disputes',
            hours=1
        )
        print("created %s " %(files_dir + disputes['filename']))
        upload_to_s3(disputes['filename'])
        print(
            "uploaded %s to s3 bucket s3://%s/%s"
            %(files_dir + disputes['filename'], s3_bucket, s3_bucket_dir))
        update_redshift(disputes['tablename'], disputes['columns'], disputes['primary_key'], disputes['filename'])
        print("updated redshift table " + disputes['tablename'])
        print("Done with disputes!")

if __name__=='__main__':
   main()
