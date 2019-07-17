# Braintree to Redshift

This project connects to the Braintree API (v2.7), downloads the latest data about transactions within a specified date range, and formats and outputs the data as CSVs. It uploads the CSVs into an Amazon S3 bucket and imports the data into a corresponding table into Redshift using the `copy` command.

Here is the architecture proposal, signed off by tech team on 6/26/2019: https://docs.google.com/document/d/1b6yDeCh0v4RMiZ8KGhYyCL1YR3gEtECQGKMxo3Tc6c0/edit?usp=sharing

This is designed to replace: https://github.com/MoveOnOrg/braintree-to-redshift

It is heavily based on https://github.com/MoveOnOrg/fb-to-redshift

## Requirements

* Python3
* Amazon S3 bucket and Redshift user with ability to create tables in a given schema

## Installation and use

### 1. Clone this repo
### 2. Create a virtualenv and activate it.

If Python 3 is not your default Python version, you'll need to tell virtualenv which version of Python to use.

  `virtualenv venv` or `virtualenv -p /path/to/python3 venv`

  `. venv/bin/activate`

### 3. Install requirements

  `pip install -r requirements.txt`

  * If you don't already have postgresql-devel installed, you'll need to run `yum install python-devel postgresql-devel` first or else you'll get an error like `pg_config executable not found` when pip tries to install psycopg2.

### 4. Create settings.py (using settings.py.example as a template).

### 5. Create or copy a parameter dictionary for each data CSV, using examples in settings.py. Add each dictionary to the list of `data_types` in settings.py.

### 6. Set up Redshift import.
  * If you don't already have one, [create a bucket in S3](http://docs.aws.amazon.com/gettingstarted/latest/swh/getting-started-create-bucket.html) and add its unique name to `s3_bucket` in settings.py.
  * [Create a Redshift database](http://docs.aws.amazon.com/redshift/latest/dg/t_creating_database.html), and get your [AWS IAM credentials](https://aws.amazon.com/iam/). Add database connection info and IAM credentials to settings.py.
  * Create tables in the schema `ventures` that correspond to the tablename and columns defined in your parameter dictionaries. The Redshift user whose credentials are in settings.py should own those tables and have the ability to add tables to that schema.

### 5. Run the script!

  `python braintree_to_redshift.py`

  * If you set `test` to `True`, your CSVs will have '_test' appended to the filename and the script will append '_test' to the tablenames - so you must create tables in advance of running the script in test mode for import to work. E.g. `CREATE TABLE ventures.transactions_test`.
