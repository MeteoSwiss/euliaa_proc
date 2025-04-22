import os
import sys
import time
import datetime
import pandas as pd
from threading import Thread
from pathlib import Path
from queue import Queue
from multiprocessing import Pool

#from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from watchdog.observers.polling import PollingObserver

# from dl_toolbox_runner.main import Runner
# from dl_toolbox_runner.errors import LogicError, DLFileError
# from dl_toolbox_runner.utils.file_utils import abs_file_path, round_datetime, find_file_time_windcube, get_instrument_id_and_scan_type, create_batch, get_insttype, read_halo
from log import logger
from main import Runner
from types import SimpleNamespace
from utils import get_conf
import re


class RealTimeWatcher(FileSystemEventHandler):
    """
    Watchdog event handler for real-time file processing.
    Inherits from FileSystemEventHandler (requires on_created and on_modified methods), from watchdog.events.
    """
    
    def __init__(self, queue, input_file_extension):
        logger.info('Initializing RealTimeWatcher')
        # self.x = Runner(abs_file_path('dl_toolbox_runner/config/main_config.yaml'), single_process=False)
        self.input_file_extension = input_file_extension
        self.queue = queue
            
    def check_file(self, filename):
        """
        Check if the filename contains the prefix defined in the config file.
        """
        if filename.endswith(self.input_file_extension):
            logger.info(f'Valid filename: {filename}')
            return True
        else:
            logger.critical(f'Invalid filename: {filename} must end with {self.input_file_extension}')
            return False

    def on_created(self, event):
        """
        Called when a file is created.
        """
        file = event.src_path
        filename = Path(file).name
            
        print('####################')
        logger.info(f'file: {filename} from: {file}')
        print(f'file: {filename} from: {file} - created')

        check = self.check_file(filename)
        if check:
            self.queue.put(file)
        
    def on_modified(self, event):
        """
        Called when a file is modified.
        ! Files should not get modified -> log error
        """
        logger.critical(f'event type: {event.event_type}  path : {event.src_path}')
        print(f'event type: {event.event_type}  path : {event.src_path} - modified')
        pass
    

def run_pipeline(filepath, config_template):
    """
    Run the processing pipeline for the given file.
    """

    time.sleep(2)
    try:
        logger.info('####################################################################################')
        logger.info(f'Retrieval triggered for file: {filepath}')

        config = get_conf(config_template)
        date_str = re.search("([0-9]{4}\-[0-9]{2}\-[0-9]{2}\_[0-9]{2}\-[0-9]{2}\-[0-9]{2})", filepath)
        config['hdf5_file'] = filepath
        config['output_nc_l2A'] = os.path.join(config['output_nc_dir'], 'L2A_' + date_str.group(1) + '.nc')
        config['output_nc_l2B'] = os.path.join(config['output_nc_dir'], 'L2B_' + date_str.group(1) + '.nc')
        config['output_bufr'] = os.path.join(config['output_bufr_dir'], 'BUFR_' + date_str.group(1) + '.bufr')
        print(config)
        args = SimpleNamespace(**config)

        runner = Runner(args)
        runner.run_processing()
        runner.write_l2a_and_l2b()
        runner.encode_bufr()
        
    except Exception as error:
        logger.error(f"{str(error)}, Ignoring this file: {filepath}")
        return
    

def process_load_queue(queue, config_template):
    while True:
        if not queue.empty():
            batch = queue.get()
            pool = Pool(processes=4)
            print(batch)
            # run_pipeline(batch, config_template) # -> for testing in single process
            pool.apply_async(run_pipeline, (batch, config_template))   
        else:
            time.sleep(5)
            
    
def start_watchdog_queue(watch_path, config_template):
    logger.info(f"Starting Watchdog Observer\n")
    watchdog_queue = Queue()
    
    # x = Runner(abs_file_path('dl_toolbox_runner/config/main_config.yaml'), single_process=False)
    # file_prefix = x.conf['input_file_prefix']
    file_extension = '.h5'
        
    event_handler = RealTimeWatcher(watchdog_queue, file_extension)
    observer = PollingObserver()
    observer.schedule(event_handler, watch_path, recursive=True)
    observer.start()

    worker = Thread(target=process_load_queue, args=(watchdog_queue, config_template))
    worker.daemon = True
    worker.start()
    
    try:
        while True:
            time.sleep(2)
    except Exception as error:
        observer.stop()
        print(f"Error: {str(error)}")
    observer.join()
    
if __name__ == '__main__':
    watch_path = '/data/euliaa-l1/TESTS/'  # Directory to watch
    main_path = '/home/acbr/euliaa_postproc/'
    config_template = os.path.join(main_path, 'configs/config_main.yaml')
    #watch_path = "s3://eprofile-dl-raw/"
    start_watchdog_queue(watch_path, config_template)