import unittest
from braintree_connection import *

class BraintreeConnection(unittest.TestCase):
    @classmethod
    def setUpClass(self):
        self.gateway = connect_to_braintree()
        self.now = datetime.now()
        self.new_transactions = get_new_transactions(end_time = self.now)
        self.disbursed_transactions = get_disbursed_transactions(now = self.now)
        self.new_transactions_length = sum(1 for _ in self.new_transactions.items)
        self.disbursed_transactions_length = sum(1 for _ in self.disbursed_transactions.items)
        self.disputes = get_disputes(self.now, 5)

    def test_add_items_to_transactions_dictionary(self):
        dict = {}
        transactions_count = sum(1 for _ in self.new_transactions.items)
        add_items_to_transactions_dictionary(dict, self.new_transactions)
        self.assertEqual(transactions_count, len(dict))

    def test_get_disputes(self):
        disputes_count = sum(1 for _ in self.disputes.disputes)
        self.assertGreater(disputes_count, 0)

    def test_get_transactions(self):
        self.assertGreater(self.new_transactions_length, 0)
        self.assertGreater(self.disbursed_transactions_length, 0) #may return 0 on weekend

    def test_make_disputes_dictionary(self):
        dispute_dict = make_disputes_dictionary(end_date=date.today())
        disputes_count = sum(1 for _ in self.disputes.disputes)
        self.assertEqual(len(dispute_dict), disputes_count)

    def test_make_transactions_dictionary(self):
        dict = make_transactions_dictionary(end_time = self.now)
        self.assertEqual(len(dict), self.new_transactions_length + self.disbursed_transactions_length)

if __name__ == '__main__':
    unittest.main()
