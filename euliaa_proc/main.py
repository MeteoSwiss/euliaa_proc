from euliaa_proc.measurement import H5Reader
from euliaa_proc.write_netcdf import Writer
from euliaa_proc.log import logger
from euliaa_proc.nc2bufr import write_bufr
from euliaa_proc.quicklooks import plot_quicklooks

class Runner:

    def __init__(self, args):
        self.args = args
        self.meas = None

    def run_processing(self):
        logger.info(f'Reading measurement from hdf5 file {self.args.hdf5_file}')
        self.meas = H5Reader(self.args.config, self.args.hdf5_file,conf_qc_file=self.args.config_qc)
        self.meas.read_hdf5_file()
        self.meas.load_attrs()
        self.meas.load_data()
        self.meas.add_lat_lon()
        self.meas.add_time_bnds()

        logger.info('Computing noise level and SNR')
        self.meas.add_noise_and_snr()

        logger.info('Adding basic quality flag')
        self.meas.add_quality_flag()

        logger.info('Cloud detection (for now, only transparent clouds)')
        self.meas.add_clouds()

        logger.info('Completing quality flag')
        self.meas.add_flag_below_cloud_top()
        self.meas.add_flag_missing_data()

    def make_quicklooks(self):
        """
        Plot quicklooks for L2A and L2B
        """
        logger.info('Plotting quicklooks')
        fig_name = self.args.fig_prefix+self.args.output_nc_l2A.split('/')[-1].replace('.nc', '')
        plot_quicklooks(self.args.output_nc_l2A, self.args.fig_dir, fig_name)
        # plot_quicklooks(self.args.output_nc_l2B, self.args.fig_dir, self.args.fig_name, self.args.ylim)
        logger.info('Plotted quicklooks successfully\n')

    def write_l2a_and_l2b(self):
        """
        Write L2A and L2B netCDF files
        """
        logger.info(f'Writing L2A {self.args.output_nc_l2A}')
        nc_writer = Writer(self.meas,output_file=self.args.output_nc_l2A,conf_file=self.args.config)
        nc_writer.write_nc()
        logger.info('Wrote L2A successfully\n')

        logger.info(f'Writing L2B {self.args.output_nc_l2B}')
        self.meas.subsel_stripped_profile()
        self.meas.set_invalid_to_nan() # set invalid data to NaN for L2B
        nc_writer_l2b = Writer(self.meas,output_file=self.args.output_nc_l2B,conf_file=self.args.config)
        nc_writer_l2b.write_nc()
        logger.info('Wrote L2B successfully\n')


    def encode_bufr(self):
        """
        Encode BUFR file (if specified)
        """
        if self.args.output_bufr is None:
            logger.warning('No BUFR file specified, skipping encoding')
            return
        elif not (self.args.output_bufr[-5:] == '.bufr'):
            logger.warning(f'BUFR file name must end with ".bufr", skipping encoding')
            return
        self.meas.set_invalid_to_nan() # set invalid data to NaN for BUFR  TO DO refine this, change quality flags for BUFR
        for bufr_type in self.args.bufr_types:
            bufr_name=self.args.output_bufr.replace('.bufr', f'_{bufr_type}.bufr')
            logger.info(f'Writing BUFR message {bufr_name}')
            write_bufr(self.meas.data, bufr_name, bufr_type=bufr_type)
        logger.info('Wrote BUFR message successfully\n')

if __name__=='__main__':
    import os
    cwd = os.getcwd()

    import argparse
    parser = argparse.ArgumentParser(description='Write netCDF file')
    parser.add_argument('--hdf5_file', type=str, help='Path to the HDF5 file', default='/data/euliaa-l1/TESTS/BankExport_2025-05-07_10-28-28.h5')
    parser.add_argument('--config', type=str, help='Path to the config file', default=os.path.join(cwd,'config/config_nc.yaml'))
    parser.add_argument('--config_qc', type=str, help='Path to the config file for quality control', default=os.path.join(cwd,'config/config_qc1.yaml'))
    parser.add_argument('--output_nc_l2A', type=str, help='Path to the output netCDF file for L2A', default=os.path.join(cwd,'data/TestNC_L2A.nc'))
    parser.add_argument('--output_nc_l2B', type=str, help='Path to the output netCDF file for L2B', default=os.path.join(cwd,'data/TestNC_L2B.nc'))
    parser.add_argument('--bufr_types', nargs='+', default=['wind', 'temperature'])
    parser.add_argument('--output_bufr', type=str, help='Path to the output BUFR file', default=os.path.join(cwd,'data/Test_BUFR.bufr'))
    parser.add_argument('--fig_dir', type=str, help='Path to the directory where quicklooks are saved', default=os.path.join(cwd,'quicklooks/'))
    parser.add_argument('--fig_prefix', type=str, help='Prefix of the quicklook figure', default='quicklook')
    args = parser.parse_args()

    runner = Runner(args)
    runner.run_processing()
    runner.write_l2a_and_l2b()
    runner.encode_bufr()
    runner._plot_quicklooks()
