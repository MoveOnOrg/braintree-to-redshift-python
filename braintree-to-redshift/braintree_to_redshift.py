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

from braintree_tools import create_transactions_import_file, upload_to_s3, update_redshift
from time import gmtime, strftime
from settings import (
    test, files_dir, s3_bucket, s3_bucket_dir, transactions)

def main(event='', context=''):
    print()
    print(strftime("%Y-%m-%d %H:%M:%S", gmtime()))
    print('Importing transactions')
    print('creating file')
    created_file = create_transactions_import_file(
        filename=transactions['filename'],
        columns=transactions['columns']
    )
    print("created %s " %(files_dir + transactions['filename']))
    upload_to_s3(transactions['filename'])
    print(
        "uploaded %s to s3 bucket s3://%s/%s"
        %(files_dir + transactions['filename'], s3_bucket, s3_bucket_dir))
    update_redshift(transactions['tablename'], transactions['columns'], transactions['primary_key'], transactions['filename'])
    print("updated redshift table " + transactions['tablename'])
    print("Done!")

if __name__=='__main__':
   main()
