import boto3
import yaml
# bucket name as first argument
bucketname = 'euliaa-l2'

# endpoint and keys 
endpoint = 'https://object-store.os-api.cci1.ecmwf.int'
config_credentials_file = 'config/credentials.yaml'

with open(config_credentials_file, 'r') as file:
    config = yaml.safe_load(file)

# Extract the necessary values from the configuration
access_key = config['access_key_id']
secret_key = config['secret_access_key']
region='default'

client = boto3.client('s3',
        endpoint_url=endpoint,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key)


client.put_bucket_notification_configuration(
        Bucket=bucketname,
        NotificationConfiguration={}) 
