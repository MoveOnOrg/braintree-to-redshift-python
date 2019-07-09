import unittest
from braintree_connection import *

class BraintreeConnection(unittest.TestCase):
    def setUp(self):
        self.gateway = connect_to_braintree()
        self.start_date = date.today()
        self.day_diff = 1
        self.transactions = [{
                'amount': '12',
                'nonce': 'fake-valid-nonce'
            },
            {
                'amount': '18',
                'nonce': 'fake-valid-nonce'
            }
        ]

        self.initial_transactions_count = len(list(get_transactions(start_date = self.start_date, days = self.day_diff)))
        self.current_transactions_count = self.initial_transactions_count

    def test_create_transaction(self):
        for transaction in self.transactions:
            create_transaction(transaction['amount'], transaction['nonce'])
        self.current_transactions_count = len(list(get_transactions(start_date = self.start_date, days = self.day_diff)))
        self.assertEqual(self.current_transactions_count, self.initial_transactions_count + 2)

    def test_make_transactions_dictionary(self):
        dict = make_transactions_dictionary(start_date = self.start_date, days = self.day_diff)
        self.assertEqual(len(dict), self.current_transactions_count)

    def test_get_transactions(self):
        transactions = len(list(get_transactions(start_date = self.start_date, days = self.day_diff)))
        self.assertEqual(transactions, self.current_transactions_count)



if __name__ == '__main__':
    unittest.main()
