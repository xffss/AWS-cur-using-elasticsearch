#!/usr/bin/env python3
import os
import csv
import boto3
import json
import base64
import datetime
import gzip
import shutil
from dateutil import parser, relativedelta
from requests_aws4auth import AWS4Auth
from elasticsearch import Elasticsearch, RequestsHttpConnection, helpers


def csvFields(row, fields):
    
    for f in json.loads(fields):
        vtype = f['type']
        if vtype.endswith('DateTime'):
            if f['field'] in row and row[f['field']]:
                row[f['field']] = parser.parse(row[f['field']])
            else:
                row[f['field']] = parser.parse(row['lineItem/UsageEndDate']) # set default DateTime to bill item time
        elif vtype.endswith('BigDecimal'):
            if f['field'] in row and row[f['field']]:
                row[f['field']] = float(row[f['field']])
            else:
                row[f['field']] = 0.0 # default value 0.0
        else: # bugfixs for optionalstring but recognized as data or other bugs
            if 'savingsPlan/StartTime' in row and row['savingsPlan/StartTime']: # make it string
                row['savingsPlan/StartTime'] = '"' + row['savingsPlan/StartTime'] + '"'
            if 'savingsPlan/EndTime' in row and row['savingsPlan/EndTime']: # make it string
                row['savingsPlan/EndTime'] = '"' + row['savingsPlan/EndTime'] + '"'


def csvLoad(filename, fields):
    lineitems = []
    with open(filename) as csvf:
        reader = csv.DictReader(csvf)
        for row in reader:
            csvFields(row, fields)
            lineitems.append(row)
    return lineitems

def csvESize(lineitems, index):
    return [{'_op_type': 'update', '_index': index, '_type': 'document', '_id': i['identity/LineItemId']+str(i['lineItem/UsageEndDate'].timestamp()), "doc": i, 'doc_as_upsert': True} for i in lineitems]

def s3download(bucket,prefix, s3dir):
    s3 = boto3.client("s3")
    files = []
    resp = s3.list_objects_v2(Bucket=bucket, Prefix=prefix+s3dir)
    i=0
    for o in resp['Contents']:
        if o['Key'].endswith('.gz'):
            save2 = '/tmp/'+str(i)+'-'+os.path.basename(o['Key'])
            s3.download_file(bucket, o['Key'], save2)
            with gzip.open(save2, 'rb') as f_in:
                with open(save2.rstrip('.gz'), 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
            os.remove(save2)
            files.append(save2.rstrip('.gz'))
            i+=1
    return files

def lambda_handler(a, b):
    now = datetime.datetime.utcnow()
    s3dir = now.strftime("%Y%m")+"01-"+(now+relativedelta.relativedelta(months=1)).strftime("%Y%m")+"01"
    if now.day <= 5: # may change after month day
        s3dir = (now-relativedelta.relativedelta(months=1)).strftime("%Y%m")+"01-"+now.strftime("%Y%m")+"01"
    print(os.environ.get("eshost"))
    credentials = boto3.Session().get_credentials()
    aws_auth = AWS4Auth(
        credentials.access_key,
        credentials.secret_key,
        "us-east-1",
        "es",
        session_token=credentials.token,
    )
    es = Elasticsearch(os.environ.get("eshost"),use_ssl=True,
            verify_certs=True,
            http_auth=aws_auth,
            connection_class=RequestsHttpConnection)

    files = s3download(os.environ.get("bucket"),os.environ.get("prefix"), s3dir)
    for f in files:
        docs = csvESize(csvLoad(f, os.environ.get('fields')), 'es-index')
        helpers.bulk(es, docs)
        os.remove(f)
