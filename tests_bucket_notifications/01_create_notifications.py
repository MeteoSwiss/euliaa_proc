import boto3
from botocore.config import Config
import yaml 


with open('credentials.yaml', 'r') as file:
    config = yaml.safe_load(file)
# Extract the necessary values from the configuration
access_key_id = config['access_key_id']
secret_access_key = config['secret_access_key']
topic_name = config['topic_name']

ceph_endpoint = 'https://object-store.os-api.cci1.ecmwf.int'
region_name = 'default' # required by boto3, any value works
 
bucket_name = "euliaa-l2"
 
s3 = boto3.client('s3',
                endpoint_url=ceph_endpoint ,
                aws_access_key_id=access_key_id,
                aws_secret_access_key=secret_access_key,
)
 
# Create notification configuration
response = s3.put_bucket_notification_configuration(
    Bucket=bucket_name,
    NotificationConfiguration={
        'TopicConfigurations': [
            {
                'Id': 'http-listener',
                'TopicArn': f'arn:aws:sns:default::{topic_name}',
                'Events': ['s3:ObjectCreated:*']
            }
        ]
    }
)

print("Notification configuration set:", response)
