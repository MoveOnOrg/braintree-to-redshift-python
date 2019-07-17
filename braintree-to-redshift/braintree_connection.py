#!/usr/bin/python
# -*- coding: utf-8 -*-
""" Functions that connect to Braintree and pull transaction and dispute data.
"""

import sys
import os
import re
import braintree
import decimal
from datetime import date, datetime, timedelta
from time import gmtime, strftime, time
import json
from settings import (braintree_merchant_id, braintree_public_key, braintree_private_key, braintree_env)

local_settings_path = os.path.join(os.getcwd(),"settings.py")
if os.path.exists(local_settings_path):
    import imp
    settings = imp.load_source('settings', local_settings_path)


def decimal_default(obj):
    if isinstance(obj, decimal.Decimal):
        return float(obj)
    raise TypeError

def datetime_default(o):
    if isinstance(o, datetime):
        return o.__str__()

def connect_to_braintree():
    gateway = braintree.BraintreeGateway(
        braintree.Configuration(
            environment=braintree.Environment.Sandbox,
            merchant_id=braintree_merchant_id,
            public_key=braintree_public_key,
            private_key=braintree_private_key,
        )
    )
    return gateway

def create_transaction(amount, nonce):
    gateway = connect_to_braintree()
    result = gateway.transaction.sale({
        "amount": amount,
        "payment_method_nonce": nonce,
        "options": {
            "submit_for_settlement": True
        }
    })

    if result.is_success:
        print("success!: " + result.transaction.id)
    elif result.transaction:
        print("Error processing transaction:")
        print("  code: " + result.transaction.processor_response_code)
        print("  text: " + result.transaction.processor_response_text)
    else:
        for error in result.errors.deep_errors:
            error_string = "attribute: %s \tcode: %s \t message: %s" % (error.attribute, error.code, error.message)
            log_error(error_string, './errors.txt')

def log_error(content,logfile):
    error_log = open(logfile,'a')
    error_log.write(strftime("%Y-%m-%d %H:%M:%S", gmtime()))
    json.dump(content, error_log, indent=4)
    error_log.close()

def get_transactions(start_date = date.today(), days = 1):
    gateway = connect_to_braintree()
    end_date = start_date + timedelta(days=days)
    collection = gateway.transaction.search(
        braintree.TransactionSearch.created_at.between(start_date, end_date)
    )
    return collection

def make_transactions_dictionary(start_date = date(2019, 6, 25), days = 3):
# def make_transactions_dictionary(start_date = date.today(), days = 1):
    transactions = get_transactions(start_date, days)
    transaction_dict = {}
    for transaction in transactions.items:
        formatted_amount = json.dumps(transaction.amount, default=decimal_default)
        formatted_created_at = json.dumps(transaction.created_at, default=datetime_default).replace("\"", "")
        formatted_recurring = "TRUE" if transaction.recurring else "FALSE"
        formatted_updated_at = json.dumps(transaction.updated_at, default=datetime_default).replace("\"", "")
        formatted_order_id = transaction.order_id if transaction.order_id else ''
        formatted_subscription_id = transaction.subscription_id if transaction.subscription_id else ''
        transaction_dict[transaction.id] = [
            formatted_amount,
            formatted_created_at,
            formatted_order_id,
            transaction.payment_instrument_type,
            formatted_recurring,
            transaction.status,
            transaction.id,
            formatted_updated_at
        ]
    return transaction_dict

def get_disputes():
    print('disputes')
