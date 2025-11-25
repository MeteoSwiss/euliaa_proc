from flask import Flask, request
import json
from waitress import serve
from euliaa_proc.log import logger
from euliaa_proc.main import Runner
from types import SimpleNamespace
from euliaa_proc.utils.conf_utils import get_conf
import os 
import time 
import re
import subprocess

app = Flask(__name__)

@app.route('/', methods=['POST']) # This is the endpoint that will receive the POST requests
def catch_root_post():
    try:
        raw_data = request.data.decode()
        print("RAW POST RECEIVED:", raw_data)

        # Try parsing JSON
        notification = json.loads(raw_data)
        logger.info("Parsed notification:", notification)

        # Extract the file name if the structure matches
        key = notification['Records'][0]['s3']['object']['key']
        bucket_name = notification['Records'][0]['s3']['bucket']['name']
        # process_uploaded_file(key)
        if not key.endswith('.h5'):
            logger.info(f"File {key} is not an HDF5 file, skipping processing.")
            return 'OK', 200
        filepath= f's3://{bucket_name}/{key}'
        curr_file_path = os.path.dirname(os.path.abspath(__file__))
        if '/Kuehlungsborn/' in filepath:
            config_main_s3 = os.path.join(curr_file_path,'config/config_main_s3_Kborn.yaml')
        elif '/Andoya/' in filepath:
            config_main_s3 = os.path.join(curr_file_path, 'config/config_main_s3_Andoya.yaml')
        elif '/OHP/' in filepath:
            config_main_s3 = os.path.join(curr_file_path, 'config/config_main_s3_OHP.yaml')
        elif '/Jungfraujoch/' in filepath:
            config_main_s3 = os.path.join(curr_file_path, 'config/config_main_s3_JFJ.yaml')
        elif '/Payerne/' in filepath:
            config_main_s3 = os.path.join(curr_file_path, 'config/config_main_s3_Payerne.yaml')
        elif '/Maido/' in filepath:
            config_main_s3 = os.path.join(curr_file_path, 'config/config_main_s3_Maido.yaml')    
        elif '/Test/' in filepath:
            config_main_s3 = os.path.join(curr_file_path,'config/config_main_s3_Test.yaml')
        elif '/Test_Kuehlungsborn/' in filepath:
            config_main_s3 = os.path.join(curr_file_path,'config/config_main_s3_Kborn2.yaml')
        else:
            config_main_s3 = os.path.join(curr_file_path,'config/config_main_s3.yaml')
        """
        TO DO Lines below should be adapted depending on choices made for operational products: e.g.,
        - 20MIN files: wind and backscatter profiles considered suitable for dissemination
        - 60MIN files: temperature profiles considered suitable for dissemination
        """
        if (('20MIN' in filepath) or ('20min' in filepath)):
            operational_product = {'wind': 1, 'temperature': 0, 'backscatter': 1}
            integration_time_str = '20MIN'
        elif (('60MIN' in filepath) or ('60min' in filepath)):
            operational_product = {'wind': 0, 'temperature': 1, 'backscatter': 0}
            integration_time_str = '60MIN'
        else:
            operational_product = {'wind': 1, 'temperature': 1, 'backscatter': 1}
            integration_time_str = ''

        logger.info(f'Using config file {config_main_s3}, operational processing of : {operational_product}')
        
        run_processing_pipeline(filepath, config_main_s3, operational_product, integration_time_str) #os.path.join(curr_file_path,'config/config_main_s3.yaml'))
        


    except Exception as e:
        logger.error("Error processing notification:", e)

    return 'OK', 200


def run_processing_pipeline(filepath, config_template, operational_product={'wind': 1, 'temperature': 1, 'backscatter': 1}, integration_time_str=None):
    """
    Run the processing pipeline for the given file.
    """

    time.sleep(2)
    try:
        logger.info('####################################################################################')
        logger.info(f'Retrieval triggered for file: {filepath}')

        remove_file = False
        from pathlib import Path
        home_dir = str(Path.home())
        s3cfg_path = os.path.join(home_dir,'.s3cfg')
        if filepath.startswith('s3://'): # if we read from S3, then make a local copy because loading properly the h5 file from S3 is not working
            subprocess.call(['s3cmd', 'get', filepath, os.path.join(home_dir,'tmp/'), f'--config={s3cfg_path}'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            filepath = os.path.join(home_dir, 'tmp/', os.path.basename(filepath))
            logger.info(f'File downloaded to: {filepath}')
            remove_file = True
        

        config = get_conf(config_template)

        # TO DO this bit should be updated if the filenaming / date format in the L1 changes
        # date_str = re.search("([0-9]{4}[0-9]{2}[0-9]{2}\_[0-9]{2}[0-9]{2}[0-9]{2})", filepath) # extract date from filename, expecting format YYYYMMDD_HHMMSS
        date_str = re.search("([0-9]{4}\-[0-9]{2}\-[0-9]{2}\_[0-9]{2}\-[0-9]{2}\-[0-9]{2})", filepath) # extract date from filename, expecting format YYYY-MM-DD_HH-MM-SS
        date = date_str.group(1).split('_')[0]
        year = date[:4] # if date format is YYYYMMDD or YYYY-MM-DD
        # month = date[4:6] # if date format is YYYYMMDD
        month = date[5:7] # if date format is YYYY-MM-DD
        # day = date[6:8] # if date format is YYYYMMDD
        day = date[8:10] # if date format is YYYY-MM-DD
        ################
        config['hdf5_file'] = filepath
        if (('campaign_name' in config.keys()) and (config['campaign_name'] is not None)):
            campaign_name = f'{config["campaign_name"]}_'
        else:
            campaign_name = ''
        config['output_nc_l2A'] = os.path.join(config['output_nc_dir'], 'L2A', integration_time_str, year, month, day, f'L2A{integration_time_str}_' + campaign_name + date_str.group(1) + '.nc')
        config['output_nc_l2B'] = os.path.join(config['output_nc_dir'], 'L2B', integration_time_str, year, month, day, f'L2B{integration_time_str}_' + campaign_name + date_str.group(1) + '.nc')
        logger.info(f'HDF5 input file: {config["hdf5_file"]}')
        logger.info(f'Output directory: {config["output_nc_dir"]}')
        logger.info(f'Output L2A file will be: {config["output_nc_l2A"]}')
        logger.info(f'Output L2B file will be: {config["output_nc_l2B"]}')

        date_str_eprofile = date_str.group(1).replace('-', '')
        if ('output_nc_eprofile_wind_dir' in config.keys()) and ('eprofile_wind_prefix' in config.keys()):
            config['output_nc_eprofile_wind'] = os.path.join(config['output_nc_eprofile_wind_dir'], year, month, day, config['eprofile_wind_prefix'] + date_str_eprofile[:-2] + '.nc')
        if 'output_nc_eprofile_wind_dir_DL' in config.keys():
            config['output_nc_eprofile_wind_DL'] = os.path.join(config['output_nc_eprofile_wind_dir_DL'], config['eprofile_wind_prefix'] + date_str_eprofile[:-2] + '.nc')
        if ('output_nc_eprofile_bsc_dir' in config.keys()) and ('eprofile_bsc_prefix' in config.keys()) and ('eprofile_bsc_suffix' in config.keys()):
            config['output_nc_eprofile_bsc'] = os.path.join(config['output_nc_eprofile_bsc_dir'],year, month, day, config['eprofile_bsc_prefix'] + date_str_eprofile[:-2].replace('_', '') + config['eprofile_bsc_suffix']+'.nc')
        if 'output_bufr_dir' in config.keys():
            config['output_bufr'] = os.path.join(config['output_bufr_dir'], year, month, day, 'BUFR_' + date_str_eprofile + '.bufr')
        args = SimpleNamespace(**config)

        runner = Runner(args)
        runner.run_processing()
        logger.info("Run processing completed.")
        if (operational_product['wind'] == 1) and 'output_nc_eprofile_wind' in config.keys() and (config['output_nc_eprofile_wind'] is not None):
            runner.write_dwl_eprofile()
            logger.info("DWL E-Profile written.")
            if (('output_nc_eprofile_wind_DL' in config.keys()) and ('s3cfg_eprofile_path' in config.keys())):
                logger.info(f"Copying to E-Profile DL bucket, from {config['output_nc_eprofile_wind']} to {config['output_nc_eprofile_wind_DL']}")
                DWL_filename = os.path.basename(config['output_nc_eprofile_wind'])
                tmp_path = os.path.join(home_dir, 'tmp/', DWL_filename)
                subprocess.call(['s3cmd', 'get', config['output_nc_eprofile_wind'], os.path.join(home_dir,'tmp/') ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                s3cfg_path_eprofile = config['s3cfg_eprofile_path']
                subprocess.call(['s3cmd', 'put', tmp_path, config['output_nc_eprofile_wind_DL'], f'--config={s3cfg_path_eprofile}'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
        if (operational_product['backscatter'] == 1) and 'output_nc_eprofile_bsc' in config.keys() and (config['output_nc_eprofile_bsc'] is not None):
            runner.write_alc_eprofile()
            logger.info("ALC E-Profile written")
            if (('upload_to_UKMO_FTP' in config.keys()) and (config['upload_to_UKMO_FTP'])):
                logger.info(f"Upload to E-Profile FTP, {config['output_nc_eprofile_bsc']}")
                ALC_filename = os.path.basename(config['output_nc_eprofile_bsc'])
                tmp_path = os.path.join(home_dir, 'tmp/', ALC_filename)
                subprocess.call(['s3cmd', 'get', config['output_nc_eprofile_bsc'], os.path.join(home_dir,'tmp/') ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                subprocess.call(['bash', os.path.join(home_dir, 'euliaa_proc/euliaa_proc/scripts/ftp_upload_ukmo.sh'), tmp_path], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
        runner.write_l2a()
        logger.info("L2A file written.")
        runner.write_l2b()
        logger.info("L2B file written.")
        if (operational_product['temperature'] == 1):
            runner.encode_bufr()
        # a = 1/0  # This is just to test the error handling, remove this line in production
        logger.info('Processing completed successfully.')
        if remove_file:
            os.remove(filepath)
            logger.info(f'File removed: {filepath}')

    except Exception as e:
        logger.error(f"Error during processing: {str(e)}. This file will be ignored.")
        if remove_file and os.path.exists(filepath):
            os.remove(filepath)
            logger.info(f'File removed after error: {filepath}')
        return
    logger.info('####################################################################################')


# def process_uploaded_file(filename):
#     # Your custom processing logic here
#     logger.info(f"Processing file: {filename}")



if __name__ == '__main__':
    # app.run(debug=True, host='0.0.0.0', port=8080) # Uncomment this line to run the Flask app directly
    serve(app, host='0.0.0.0', port=8080) # Use Waitress to serve the app, this is more production-ready (waitress is a WSGI server)
    # run_processing_pipeline('s3://euliaa-l2/TESTS/BankExport_20250522_214000.h5', '/home/acbr/euliaa_proc/euliaa_proc/config/config_main_s3.yaml')
