import unittest
from datetime import date, datetime, timedelta

from braintree_connection import *

# FOR THIS TEST TO WORK:
# You have to comment out the braintree production creds and uncomment the braintree sandbox creds in settings.property
# You have to replace this in braintree_connection.py: connect_to_braintree
# gateway = braintree.BraintreeGateway(braintree.Configuration(environment=braintree.Environment.Production, merchant_id=braintree_merchant_id, public_key=braintree_public_key, private_key=braintree_private_key, timeout=200))
# with this:
# gateway = braintree.BraintreeGateway(braintree.Configuration(environment='sandbox', merchant_id=braintree_merchant_id, public_key=braintree_public_key, private_key=braintree_private_key, timeout=200))

class BraintreeConnection(unittest.TestCase):
    def setUp(self):
        self.end_date = date.today() + timedelta(days=+1)
        self.disbursement_date = self.end_date + timedelta(days=-2)
        self.day_diff = 1
        self.transactions = [{
                'amount': '12',
                'nonce': 'fake-valid-no-billing-address-nonce'
            },
            {
                'amount': '18',
                'nonce': 'fake-valid-no-billing-address-nonce'
            }
        ]

        self.initial_transactions_count = len(list(get_new_transactions(end_date = self.end_date)))
        self.transactions_list = {}
        self.current_transactions_count = 0

    def test_create_transaction(self):
        for transaction in self.transactions:
            print('inside of for each transaction')
            create_transaction(transaction['amount'], transaction['nonce'])
        self.transactions_list = get_new_transactions(end_date = self.end_date)
        self.current_transactions_count = len(list(self.transactions_list))
        self.assertEqual(self.current_transactions_count, self.initial_transactions_count + 2)

    def test_make_transactions_dictionary(self):
        self.transactions_list = get_new_transactions(end_date = self.end_date)
        self.current_transactions_count = len(list(self.transactions_list))
        dict = make_transactions_dictionary(end_date = self.end_date)

        self.assertEqual(len(dict), self.current_transactions_count)

    # def test_get_disbursed_transactions(self):
        #can't test this because it does not appear to be possible to set disbursement date on sandbox transactions.

    def test_add_items_to_transactions_dictionary(self):
        dict = {}
        add_items_to_transactions_dictionary(dict, self.transactions_list)
        self.assertEqual(len(dict), self.current_transactions_count)


if __name__ == '__main__':
    unittest.main()
