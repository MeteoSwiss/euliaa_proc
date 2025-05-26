import boto3
from botocore.client import Config 

access_key_id = 'qPVDHAuft23j3RIlsXV8Iy1mYOzijSqg' # stored in Morpheus Cypher
secret_access_key = 'zav3TgHh968PyH29FJ3nBc5dj6x99PGA' # stored in  Morpheus Cypher
ceph_endpoint = 'https://object-store.os-api.cci1.ecmwf.int'
region_name = 'default' # required by boto3, any value works
 
sns = boto3.client('sns',
  region_name=region_name,
  endpoint_url= ceph_endpoint,
  aws_access_key_id=access_key_id,
  aws_secret_access_key=secret_access_key,
  config=Config(signature_version='s3'))
 
response = sns.list_topics()
 
# Print the Topic ARNs
print('All topics:')
for topic in response['Topics']:
  print(' -'+topic['TopicArn'])