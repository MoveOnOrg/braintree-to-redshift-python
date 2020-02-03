""" Functions that connect to Braintree and pull transaction and dispute data.
"""
import sys, os, re, braintree, decimal
from datetime import date, datetime, timedelta
from time import gmtime, strftime, time
import json
from settings import braintree_merchant_id, braintree_public_key, braintree_private_key
local_settings_path = os.path.join(os.getcwd(), 'settings.py')
if os.path.exists(local_settings_path):
    import imp
    settings = imp.load_source('settings', local_settings_path)

def add_items_to_transactions_dictionary(dictionary, transactions):
    for transaction in transactions:
        credit_card = transaction.credit_card
        disbursement = transaction.disbursement_details
        dictionary[transaction.id] = [
             credit_card['bin'],
             credit_card['card_type'],
             credit_card['cardholder_name'],
             credit_card['commercial'],
             credit_card['country_of_issuance'],
             credit_card['customer_location'],
             credit_card['debit'],
             credit_card['durbin_regulated'],
             credit_card['expiration_month'],
             credit_card['expiration_year'],
             credit_card['healthcare'],
             credit_card['image_url'],
             credit_card['issuing_bank'],
             credit_card['last_4'],
             credit_card['payroll'],
             credit_card['prepaid'],
             credit_card['product_id'],
             credit_card['token'],
             credit_card['venmo_sdk'],
             disbursement.disbursement_date,
             disbursement.funds_held,
             disbursement.settlement_amount,
             disbursement.settlement_currency_exchange_rate,
             disbursement.settlement_currency_iso_code,
             disbursement.success,
             transaction.additional_processor_response,
             transaction.amount,
             transaction.avs_error_response_code,
             transaction.avs_postal_code_response_code,
             transaction.avs_street_address_response_code,
             transaction.channel,
             transaction.created_at,
             transaction.currency_iso_code,
             transaction.cvv_response_code,
             transaction.discount_amount,
             transaction.escrow_status,
             transaction.gateway_rejection_reason,
             transaction.id,
             transaction.master_merchant_account_id,
             transaction.merchant_account_id,
             transaction.order_id,
             transaction.payment_instrument_type,
             transaction.plan_id,
             transaction.processor_authorization_code,
             transaction.processor_response_code,
             transaction.processor_response_text,
             transaction.processor_settlement_response_code,
             transaction.processor_settlement_response_text,
             transaction.purchase_order_number,
             transaction.recurring,
             transaction.refund_id,
             transaction.refunded_transaction_id,
             transaction.service_fee_amount,
             transaction.settlement_batch_id,
             transaction.shipping_amount,
             transaction.ships_from_postal_code,
             transaction.status,
             transaction.sub_merchant_account_id,
             transaction.subscription_id,
             transaction.tax_amount,
             transaction.tax_exempt,
             transaction.type,
             transaction.updated_at,
             transaction.voice_referral_number,
        ]
def connect_to_braintree():
    print('connect to braintree called')
    gateway = braintree.BraintreeGateway(braintree.Configuration(environment=braintree.Environment.Production, merchant_id=braintree_merchant_id, public_key=braintree_public_key, private_key=braintree_private_key, timeout=200))
    return gateway


def create_transaction(amount, nonce):
    gateway = connect_to_braintree()
    result = gateway.transaction.sale({'amount': amount,
       'payment_method_nonce': nonce,
       'options': {'submit_for_settlement': True}})
    if result.is_success:
        print ('success!: ' + result.transaction.id)
    elif result.transaction:
        print ('Error processing transaction:')
        print ('  code: ' + result.transaction.processor_response_code)
        print ('  text: ' + result.transaction.processor_response_text)
    else:
        for error in result.errors.deep_errors:
            error_string = 'attribute: %s \tcode: %s \t message: %s' % (error.attribute, error.code, error.message)
            log_error(error_string, './errors.txt')


def log_error(content, logfile):
    error_log = open(logfile, 'a')
    error_log.write(strftime('%Y-%m-%d %H:%M:%S', gmtime()))
    json.dump(content, error_log, indent=4)
    error_log.close()


def get_disputes(end_date=date.today(), days=5):
    gateway = connect_to_braintree()
    start_date = end_date + timedelta(days=-days)
    collection = gateway.dispute.search(braintree.DisputeSearch.effective_date.between(start_date, end_date))
    return collection

def get_disbursed_transactions(today=date.today()):
    gateway = connect_to_braintree()
    start_date = today + timedelta(days=-5)
    end_date = today + timedelta(days=-1)
    print('disbursed transactions date range')
    print(start_date)
    print(end_date)
    collection = gateway.transaction.search(
        braintree.TransactionSearch.disbursement_date.between(start_date, end_date)
    )
    print("disbursed:")

    # each iteration is a network request; default is batching with 50 and is SLOW
    #collection._ResourceCollection__page_size = 1000
    print(' search result count', len(collection._ResourceCollection__ids))
    #import pdb; pdb.set_trace()
    transactions = list(collection.items)  # flatten to local data
    size = len(transactions)
    print(' disbursed count', size)
    return transactions

def get_new_transactions(end_date=date.today()):
    gateway = connect_to_braintree()
    end_date = end_date
    start_date = end_date + timedelta(days=-1)
    print('new transactions date range')
    print(start_date)
    print(end_date)
    collection = gateway.transaction.search(
        braintree.TransactionSearch.created_at.between(start_date, end_date)
    )
    print("new transactions:")
    # each iteration is a network request; default is batching with 50 and is SLOW
    # however making this 1000 yields 'connection timed out' errors
    # -- probably because the query is trying to load too much data
    #collection._ResourceCollection__page_size = 300
    print(' search result count', len(collection._ResourceCollection__ids))
    transactions = list(collection.items)  # flatten to local data
    size = len(transactions)
    print(' transaction count', size)
    return transactions

def make_disputes_dictionary(end_date=date.today(), days=5):
    result = get_disputes(end_date, days)
    dispute_dict = {}
    for dispute in result.disputes:
        dispute_dict[dispute.id] = [
            dispute.amount_disputed,
            dispute.amount_won,
            dispute.case_number,
            dispute.currency_iso_code,
            dispute.id,
            dispute.kind,
            dispute.merchant_account_id,
            dispute.original_dispute_id,
            dispute.processor_comments,
            dispute.reason,
            dispute.reason_code,
            dispute.reason_description,
            dispute.received_date,
            dispute.reference_number,
            dispute.reply_by_date,
            dispute.status,
            dispute.transaction.id,
        ]
    return dispute_dict

def make_transactions_dictionary(end_date=date.today()):
    transaction_dict = {}
    disbursed_transactions = get_disbursed_transactions(end_date)
    add_items_to_transactions_dictionary(transaction_dict, disbursed_transactions)
    #new_transactions = get_new_transactions(end_date)
    #add_items_to_transactions_dictionary(transaction_dict, new_transactions)
    print('returned from get transactions')
    print('transaction dictionary done')
    return transaction_dict
