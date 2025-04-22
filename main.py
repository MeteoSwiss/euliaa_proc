from measurement import H5Reader
from write_netcdf import Writer
from log import logger
from nc2bufr import write_bufr

class Runner:

    def __init__(self, args):
        self.args = args
        self.meas = None

    def run_processing(self):
        logger.info(f'Reading measurement from hdf5 file {args.hdf5_file}')
        self.meas = H5Reader(args.config, args.hdf5_file,conf_qc_file=args.config_qc)
        self.meas.read_hdf5_file()
        self.meas.load_attrs()
        self.meas.load_data()
        self.meas.add_lat_lon()

        logger.info('Computing noise level and SNR')
        self.meas.add_noise_and_snr()

        logger.info('Adding basic quality flag')
        self.meas.add_quality_flag()

        logger.info('Cloud detection (for now, only transparent clouds)')
        self.meas.add_clouds()

        logger.info('Completing quality flag')
        self.meas.add_flag_below_cloud_top()
        self.meas.add_flag_missing_data()
        

    def write_l2a_and_l2b(self):

        logger.info(f'Writing L2A {self.args.output_nc_l2A}')
        nc_writer = Writer(self.meas,output_file=self.args.output_nc_l2A,conf_file=self.args.config)
        nc_writer.write_nc()
        logger.info('Wrote L2A successfully\n')

        logger.info(f'Writing L2B {self.args.output_nc_l2B}')
        self.meas.subsel_stripped_profile()
        self.meas.set_invalid_to_nan() # set invalid data to NaN for L2B
        nc_writer_l2b = Writer(self.meas,output_file=args.output_nc_l2B,conf_file=args.config)
        nc_writer_l2b.write_nc()
        logger.info('Wrote L2B successfully\n')


    def encode_bufr(self):
        if self.args.output_bufr is None:
            logger.warning('No BUFR file specified, skipping encoding')
            return
        elif not (self.args.output_bufr[-5:] == '.bufr'):
            logger.warning(f'BUFR file name must end with ".bufr", skipping encoding')
            return
        logger.info(f'Writing BUFR message {self.args.output_bufr}')
        self.meas.set_invalid_to_nan() # set invalid data to NaN for BUFR  TO DO refine this, change quality flags for BUFR
        write_bufr(self.meas.data, self.args.output_bufr)


if __name__=='__main__':
    import os
    cwd = os.getcwd()

    import argparse
    parser = argparse.ArgumentParser(description='Write netCDF file')
    parser.add_argument('--hdf5_file', type=str, help='Path to the HDF5 file', default=os.path.join(cwd,'data/BankExport3.h5'))
    parser.add_argument('--config', type=str, help='Path to the config file', default=os.path.join(cwd,'configs/config_nc.yaml'))
    parser.add_argument('--config_qc', type=str, help='Path to the config file for quality control', default=os.path.join(cwd,'configs/config_qc1.yaml'))
    parser.add_argument('--output_nc_l2A', type=str, help='Path to the output netCDF file for L2A', default=os.path.join(cwd,'data/TestNC_L2A.nc'))
    parser.add_argument('--output_nc_l2B', type=str, help='Path to the output netCDF file for L2B', default=os.path.join(cwd,'data/TestNC_L2B.nc'))
    parser.add_argument('--output_bufr', type=str, help='Path to the output BUFR file', default=os.path.join(cwd,'data/Test_BUFR.bufr'))
    args = parser.parse_args()
    
    runner = Runner(args)
    runner.run_processing()
    runner.write_l2a_and_l2b()
    runner.encode_bufr()
    # hdf5file = '/data/s3euliaa/TESTS/BankExport3.h5'
    # config = os.path.join(cwd,'configs/config_nc.yaml')
    # config_qc = os.path.join(cwd,'configs/config_qc.yaml')
    # output_nc_l2A = os.path.join(cwd,'data/TestNC_L2A.nc')
    # output_nc_l2B = os.path.join(cwd,'data/TestNC_L2B.nc')

