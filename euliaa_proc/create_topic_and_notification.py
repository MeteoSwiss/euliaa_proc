import boto3
from botocore.config import Config
import yaml
import os

# Load the configuration file
cwd = os.getcwd()
config_credentials_file = os.path.join(cwd,'config/credentials.yaml')

with open(config_credentials_file, 'r') as file:
    config = yaml.safe_load(file)

# Extract the necessary values from the configuration
access_key_id = config['access_key_id']
secret_access_key = config['secret_access_key']
topic_name = config['topic_name']  # The topic name you want to create
endpoint = config['endpoint']  # The HTTP endpoint for notifications
ceph_endpoint = config['ceph_endpoint']  # The Ceph endpoint
region_name = config['region_name']  # The region name for the SNS client
bucket_name = config['bucket_name']  # The bucket name for S3 notifications

# ------------------------------------------
# 1 - Create SNS topic pushing to HTTP endpoint
# ------------------------------------------
# Create client object to interact with the SNS (Simple Notification Service) API, adjusted to use the EWC's Ceph-based S3 system
# It is used to create a topic 
client = boto3.client('sns',
                     endpoint_url= ceph_endpoint,
                     aws_access_key_id=access_key_id,
                     aws_secret_access_key=secret_access_key,
                     region_name=region_name,
                     config=Config(signature_version='s3') # Forces use of S3-style signing for requests — Ceph needs this to accept the API calls
                     )

# Check if the topic already exists
existing_topics = client.list_topics()
topic_arn = None
for topic in existing_topics.get('Topics', []):
    existing_topic_name = topic['TopicArn'].split(':')[-1]  # Extract the topic name from the ARN
    if topic_name==existing_topic_name:
        print(f"Topic '{topic_name}' already exists with ARN: {topic['TopicArn']}")
        continue

if not topic_arn:
    print(f"Topic '{topic_name}' does not exist. Proceeding to create it.")
    client.create_topic(Name=topic_name, 
                    Attributes={'persistent': 'True', # means notifications are not just fire-and-forget; good for resilience — you won’t miss events due to momentary downtime.
                                'push-endpoint': endpoint # the HTTP endpoint for notifications
                                }
                    )


# ------------------------------------------
# 2 - Create notifications for the S3 bucket
# ------------------------------------------
# Create S3 client object to interact with the S3 API 
s3 = boto3.client('s3',
                endpoint_url=ceph_endpoint ,
                aws_access_key_id=access_key_id,
                aws_secret_access_key=secret_access_key,
)
 
# Create notification configuration for the S3 bucket
response = s3.put_bucket_notification_configuration(
    Bucket=bucket_name,
    NotificationConfiguration={
        'TopicConfigurations': [
            {
                'Id': 'http-listener', # A unique identifier for the notification configuration, internal ref
                'TopicArn': f'arn:aws:sns:{region_name}::{topic_name}',
                'Events': ['s3:ObjectCreated:*'], # The event type to listen for; in this case, any object creation event
                'Filter': {
                    'Key': {
                        'FilterRules': [
                            {
                                'Name': 'suffix',
                                'Value': '.h5'
                            }
                        ]
                    }
                }
            }
        ]
    }
)

print("Notification configuration set:", response)
