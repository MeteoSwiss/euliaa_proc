import boto3
from botocore.client import Config

import yaml

config_credentials_file = '../euliaa_proc/config/credentials.yaml'
with open(config_credentials_file, 'r') as file:
    config = yaml.safe_load(file)

# Extract the necessary values from the configuration
access_key = config['access_key_id']
secret_key = config['secret_access_key']
ceph_endpoint = 'https://object-store.os-api.cci1.ecmwf.int'
region_name = 'default' # required by boto3, any value works
topic_name = config['topic_name']  # The topic name you want to create
endpoint = config['endpoint']  # The HTTP endpoint for notifications
ceph_endpoint = config['ceph_endpoint']  # The Ceph endpoint
region_name = config['region_name']  # The region name for the SNS client
bucket_name = config['bucket_name']  # The bucket name for S3 notifications


arn = 'arn:aws:sns:default::'+topic_name
 
sns = boto3.client('sns',
  region_name=region_name,
  endpoint_url= ceph_endpoint,
  aws_access_key_id=access_key,
  aws_secret_access_key=secret_key,
  config=Config(signature_version='s3'))
 
# Delete the SNS topic
response = sns.delete_topic(TopicArn=arn)



client = boto3.client('s3',
        endpoint_url=endpoint,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key)


client.put_bucket_notification_configuration(
        Bucket=bucket_name,
        NotificationConfiguration={}) 
