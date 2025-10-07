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
 
sns = boto3.client('sns',
  region_name=region_name,
  endpoint_url= ceph_endpoint,
  aws_access_key_id=access_key,
  aws_secret_access_key=secret_key,
  config=Config(signature_version='s3'))
 
response = sns.list_topics()
 
# Print the Topic ARNs
print('All topics:')
for topic in response['Topics']:
  print(' -'+topic['TopicArn'])
