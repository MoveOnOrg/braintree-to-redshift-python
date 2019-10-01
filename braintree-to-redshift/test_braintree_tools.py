import unittest
from settings import (
    test, files_dir, s3_bucket, s3_bucket_dir, transactions)
from braintree_tools import *

class BraintreeTools(unittest.TestCase):
    def setUp(self):
        self.filename = 'braintree-to-redshift-test.csv'

    def test_create_import_file(self):
        import_creator = create_import_file(filename=self.filename, columns=transactions['columns'])
        self.assertTrue(import_creator)

    def test_upload_to_s3(self):
        upload_to_s3(filename=self.filename)

    def test_update_redshift(self):
        update_redshift(transactions['tablename'], transactions['columns'], transactions['primary_key'], self.filename) #should make set of test columns etc

if __name__ == '__main__':
    unittest.main()
