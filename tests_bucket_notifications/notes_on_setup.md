# Notes on pipeline adjustments to avoid mounting S3 buckets

## Setting up bucket notifications
The basic setup is shown in these dummy files:
- Settings should be stored in a file named credentials.yaml, containing same fields as dummy_cred.yaml
- Start by creating topic: `00_create_topic.py`
- Then associated notifications: `01_create_notifications.py`
- Then listen to incoming notifications: `02_http_listener.py` 

For this to work we need to go through some preliminary steps:
### Instance configuration (EWC / Morpheus)
To run these code snippets on the European Weather Cloud, we must allow http access and use of the 8080 port.
- Adding 8080 port: this is done here https://morpheus.ecmwf.int/infrastructure/networks/securityGroups , select ssh-https, add rule : Name=8080 / ingress / Network / 0.0.0.0/0 / Custom / TCP / 8080
- Then this security group must be chosen @ setup of your VM.

### Nginx server 
I found this useful but might not be completely necessary.
```
sudo apt install nginx
sudo nano /etc/nginx/sites-available/flask_app
        server {
            listen 80;
            server_name 136.156.xxx.xxx; # --> Your VM IP
        
            location / {
                proxy_pass http://127.0.0.1:8080;  # Flask app running on port 8080
                proxy_set_header Host $host;
                proxy_set_header X-Real-IP $remote_addr;
                proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
                proxy_set_header X-Forwarded-Proto $scheme;
            }
        }
        
sudo ln -s /etc/nginx/sites-available/flask_app /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
sudo systemctl reload nginx
sudo systemctl enable nginx
```


## Adjustments to R/W on S3 buckets (semi-)directly
- Needs to have s3fs and boto3 installed in your environment
    - NB: for some reason poetry finds conflicts, install using pip
- Not sure if necessary: `export AWS_RESPONSE_CHECKSUM_VALIDATION=when_required` and `export AWS_REQUEST_CHECKSUM_CALCULATION=when_required`
- AWS CLI should be installed (s3cmd / s3fs not enough). Modify deployment scripts to include:
    ```
    sudo apt install -y awscli

    mkdir -p /$HOME/.aws
    cat >/$HOME/.aws/config <<EOT
    [default]
    endpoint_url = $S3_HOST_BASE
    EOT

    cat >/$HOME/.aws/credentials <<EOT
    [default]
    aws_access_key_id = $S3_ACCESS_KEY
    aws_secret_access_key = $S3_SECRET_KEY
    EOT
    ```
- NetCDF files can then be opened with xarray, specifying the h5netcdf engine: `xr.open_dataset('netcdf_file.nc', engine="h5netcdf")`
    - NB: hdf5 files containing different groups can however not be opened properly (requires netCDF4 library which is not compatible with S3 reading; need to save a local file copy.)
- Writing a NetCDF file directly in the S3 bucket is not always possible.
    - First option, seems to work with light files, but crashes with bigger ones: using simple cache
        ```
        import fsspec
        outfile = fsspec.open('simplecache::s3://bucket/test_nc_file.nc',
                      mode='wb',s3=dict(profile='default'))
        with outfile as f:
            ds.to_netcdf(f)
        ```
    - Second option, works more stably, requires writing a temporary file:
        ```
        import fsspec
        import tempfile
        
        with tempfile.NamedTemporaryFile(suffix=".nc") as tmp:
            ds.to_netcdf(tmp.name, engine="netcdf4")  # Write the dataset to local disk 
            tmp.seek(0) # Rewind the file pointer to the beginning
        
            with fsspec.open('s3://euliaa-l2/TESTS/TestNC_L2A_testbucketwrite.nc', # Open the S3 file for writing
                             mode='wb', s3=dict(profile='default')) as s3file:
                s3file.write(tmp.read())
            tmp.flush()
        ```
    