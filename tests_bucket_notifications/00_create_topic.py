import boto3
from botocore.config import Config
import yaml

# Load the configuration file
with open('credentials.yaml', 'r') as file:
    config = yaml.safe_load(file)
# Extract the necessary values from the configuration
access_key_id = config['access_key_id']
secret_access_key = config['secret_access_key']
topic_name = config['topic_name']  # The topic name you want to create

endpoint = "http://136.156.133.85:8080/" # your own http endpoint, should be http://<your-cloud-vm-ip>:8080/ or another appropriate port (which should be included in the security group of your cloud VM, https://morpheus.ecmwf.int/infrastructure/networks/securityGroups)
ceph_endpoint = 'https://object-store.os-api.cci1.ecmwf.int' 
region_name = 'default' # required by boto3, any value works

client = boto3.client('sns',
                     endpoint_url= ceph_endpoint,
                     aws_access_key_id=access_key_id,
                     aws_secret_access_key=secret_access_key,
                     region_name=region_name,
                     config=Config(signature_version='s3'))
 
client.create_topic(Name=topic_name, Attributes={'persistent': 'True', 'push-endpoint': endpoint})
