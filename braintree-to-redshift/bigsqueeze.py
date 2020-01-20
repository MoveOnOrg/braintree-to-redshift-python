"""
Big Squeeze is a Frank Zappa song
This library addresses the issue of trying to process a large number of items with some action
in an AWS Lambda instance, if the maximum lambda duration is not sufficient.
I.e. It SQUEEZES the processing into the constraints of AWS Lambda
It does this by first copying the results to S3 and then dispatching multiple
Lambda invocations to process different ranges of the csv -- only loading in the data range
required.
At time of writing:
* API calls from Lambda often are done around 2/second ~> maximum of 15*60*2 = 1800 max records processed
* SQS messages are sent around 1600/minute ~> maximum of 15*1600 = 24000 max records processed
* Lambda uploads to an S3 bucket (in the same region) at around 8M/second, suggesting if
  each 'row' of data is around 512 bytes then the same 24K items can be send in less than 2 seconds
  which suggests = 10million max records processed
                   ^^^^^^^^^ (This is better)
With a list of items and a function to process them, the list should be prepared in order of
the function's arguments so e.g. if the function has signature:
   `def foo_processor(lines, errors, header, context)`
then you want the data in 'rows' so [ [rec1arg1, rec1arg2, rec1arg3], [rec2arg1, rec2arg2, rec2arg3], ...]
where a subset of the records will be passed as the first `lines` argument. `errors` will be any errors
from processing, and the `header` argument will be an optional.  `context` can be a JSON-able datastructure
that needs to be small enough so that 100 records + the datastructure is less than 100Kb in JSON form
The argument data MUST accept string data -- it has just be deserialized from a CSV.
Then:
```
from bigsqueeze import distribute_task, distribute_task_csv
... distribute_task(list_data_to_process, foo_processor, s3bucket_name, context={'key1': 'jsonabledata'....})

```
You can also add a `catch=True` argument which will catch errors rather than allow Lambda to repeat tries.
This might be important if row-actions are not idempotent and your own function might fail causing repeats.
If your data is already a CSV file, then make sure it is type:bytes, and then you can just call:
    distribute_task_csv(csv_bytes_data, foo_processor, s3bucket_name, context....)
"""

import csv
import datetime
from io import TextIOWrapper, BytesIO
from six import StringIO
import sys
import traceback
import uuid

# local_settings_path = os.path.join(os.getcwd(),"settings.py")
# if os.path.exists(local_settings_path):
#     import imp
#     settings = imp.load_source('settings', local_settings_path)
#
# from settings import (
#     aws_access_key, aws_secret_key, s3_bucket, s3_bucket_dir, s3_region, files_dir,
#     test)
# import settings
import boto3
from zappa.asynchronous import get_func_task_path, import_and_get_task
from zappa.asynchronous import task as zappa_async_task

EXPIRATION_DURATION = {'days': 1}

class S3Storage:

    def __init__(self):
        self.s3 = boto3.client('s3')

    def put(self, bucket, key, data):
        return self.s3.put_object(
            Bucket=bucket,
            Key=key,
            Body=data,
            Expires=datetime.datetime.now() + datetime.timedelta(**EXPIRATION_DURATION))

    def get_range(self, bucket, key, rangestart, rangeend):
        get_args = {'Bucket': bucket, 'Key': key}
        if rangestart:
            # bytes is INCLUSIVE for the rangeend parameter, unlike python
            # so e.g. while python returns 2 bytes for data[2:4]
            # Range: bytes=2-4 will return 3!! So we subtract 1
            get_args['Range'] = 'bytes={}-{}'.format(rangestart, rangeend - 1)
        response = self.s3.get_object(**get_args)
        return response['Body'].read()


class TestStorage:

    def __init__(self):
        self.data = {}

    def put(self, bucket, key, data):
        self.data[key] = data

    def get_range(self, bucket, key, rangestart, rangeend):
        return self.data[key][rangestart:rangeend]


STORAGES = {
    's3': S3Storage(),
    'test': TestStorage()
}

def distribute_task_csv(csv_file_data, func_to_run,
                        bucket,
                        group_count=100, header=None,
                        storage='s3', context=None, catch=False):
    """
    TODO: Docs
    """
    func_name = get_func_task_path(func_to_run)
    # import_file = open(csv_file_data)
    # row_chunks = import_file.split(b'\n')
    row_chunks = csv_file_data.split('\n')
    cursor = 0
    row_ranges = []
    # gather start/end bytes for each row
    for rowc in row_chunks:
        rng = [cursor]
        cursor = cursor + len(rowc) + 1
        rng.append(cursor)
        row_ranges.append(rng)

    # group the rows and get start/end bytes for each group
    group_ranges = []
    for grpstep in range(1, len(row_ranges), group_count):
        end = min(len(row_ranges) - 1, grpstep + group_count -1)
        group_ranges.append((row_ranges[grpstep][0], row_ranges[end][1]))

    # upload data
    storagekey = str(uuid.uuid4())
    response = STORAGES[storage].put(bucket, storagekey, csv_file_data)

    # start processes
    for grp in group_ranges:
        process_task_portion(bucket, storagekey, grp[0], grp[1],
                             func_name, header, storage, context, catch)


def distribute_task(list_data, func_to_run, bucket,
                    group_count=100, header=None,
                    storage='s3', context=None, catch=False):
    csvdata = StringIO()
    outcsv = csv.writer(csvdata)
    if header:
        outcsv.writerow(header)
    else:
        outcsv.writerow([])
    outcsv.writerows(list_data)
    distribute_task_csv(csvdata.getvalue().encode(),
                        func_to_run,
                        bucket,
                        group_count=group_count, header=header,
                        storage=storage, context=context, catch=catch)


@zappa_async_task
def process_task_portion(bucket, storagekey, rangestart, rangeend, func_name, header,
                         storage='s3', context=None, catch=False):
    func = import_and_get_task(func_name)
    filedata = STORAGES[storage].get_range(bucket, storagekey, rangestart, rangeend)

    lines, errors = try_encodings(filedata)
    if catch:
        try:
            func(lines, errors, header, context)
        except Exception as err:
            # In Lambda you can search for '"BIGSQUEEZE Error"' in the logs
            type_, value_, traceback_ = sys.exc_info()
            err_traceback_str = '\n'.join(traceback.format_exception(type_, value_, traceback_))
            return {'Exception': 'BIGSQUEEZE Error',
                    'error': err_traceback_str,
                    'errors': errors,
                    'rangestart': rangestart,
                    'rangeend': rangeend,
                    'func_name': func_name,
                    'bucket': bucket,
                    'storagekey': storagekey}
    else:
        func(lines, errors, header, context)


def try_encodings(csvdata):
    encodings = ['utf-8-sig', 'latin1', 'Windows-1254']
    lines = False
    errors = []
    for enc in encodings:
        try:
            lines = list(csv.reader(TextIOWrapper(BytesIO(csvdata), encoding=enc)))
            break
        except Exception as err:
            errors.append(str(err))
            continue
    return lines, errors


def test():
    a = [(a, a+1, a+2) for a in range(21)]
    a[0:0] = [['a','b','c'], ] # header
    csvdata = StringIO()
    outcsv = csv.writer(csvdata)
    outcsv.writerows(a)
    distribute_task_csv(csvdata.getvalue().encode(), print, 'x',
                        group_count=5, storage='test', context={'foo': 'bar'})
