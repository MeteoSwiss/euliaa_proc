from euliaa_proc.measurement import H5Reader
from euliaa_proc.write_netcdf import Writer
from euliaa_proc.log import logger
from euliaa_proc.nc2bufr import write_bufr
from euliaa_proc.quicklooks import plot_quicklooks, plot_daily_quicklooks

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
        self.meas.add_height_bnds()
        self.meas.correct_velocity()
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
        fig_title = self.args.output_nc_l2A.split('/')[-1].replace('.nc', '')
        plot_daily_quicklooks([self.args.output_nc_l2A], self.args.fig_dir, fig_title, fig_prefix=self.args.fig_prefix)
        # plot_quicklooks(self.args.output_nc_l2B, self.args.fig_dir, self.args.fig_name, self.args.ylim)
        logger.info('Plotted quicklooks successfully\n')

    def write_l2a(self):
        """
        Write L2A netCDF files
        """
        logger.info(f'Writing L2A {self.args.output_nc_l2A}')
        nc_writer = Writer(self.meas,output_file=self.args.output_nc_l2A)#,conf_file=self.args.config)
        nc_writer.write_nc()
        logger.info('Wrote L2A successfully\n')

    def write_l2b(self):
        """
        Write L2B netCDF files
        """
        logger.info(f'Writing L2B {self.args.output_nc_l2B}')
        self.meas.combine_ray_mie()
        self.meas.combine_int_broad()
        self.meas.subsel_stripped_profile()
        # self.meas.set_invalid_to_nan() # set invalid data to NaN for L2B
        nc_writer_l2b = Writer(self.meas,output_file=self.args.output_nc_l2B)
        nc_writer_l2b.write_nc()
        logger.info('Wrote L2B successfully\n')

    # def write_l2a_and_l2b(self):
    #     """
    #     Write L2A and L2B netCDF files
    #     """
    #     logger.info(f'Writing L2A {self.args.output_nc_l2A}')
    #     nc_writer = Writer(self.meas,output_file=self.args.output_nc_l2A)#,conf_file=self.args.config)
    #     nc_writer.write_nc()
    #     logger.info('Wrote L2A successfully\n')

    #     logger.info(f'Writing L2B {self.args.output_nc_l2B}')
    #     self.meas.subsel_stripped_profile()
    #     # self.meas.set_invalid_to_nan() # set invalid data to NaN for L2B
    #     nc_writer_l2b = Writer(self.meas,output_file=self.args.output_nc_l2B)#,conf_file=self.args.config)
    #     nc_writer_l2b.write_nc()
    #     logger.info('Wrote L2B successfully\n')

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


    def write_dwl_eprofile(self):
        """
        Write DWL eprofile file
        """
        from euliaa_proc.eprofile_wind import EProfileWindMeasurement
        logger.info('Writing DWL eprofile file')
        if not hasattr(self.args, 'config_eprofile_wind') or self.args.config_eprofile_wind is None:
            logger.error('No config_eprofile_wind specified, exiting')
            return

        eprofile_meas = EProfileWindMeasurement(self.args.config_eprofile_wind, self.meas.data, conf_qc_file=self.args.config_qc)
        eprofile_meas.load_data()
        eprofile_meas.set_var_attrs_from_conf()
        eprofile_meas.set_global_attrs_from_conf()
        eprofile_meas.subsel_altitude_range()
        eprofile_writer = Writer(eprofile_meas, output_file=self.args.output_nc_eprofile_wind)
        eprofile_writer.write_nc()
        logger.info(f'Wrote DWL-EPROFILE file successfully to {self.args.output_nc_eprofile_wind}\n')


    def write_alc_eprofile(self):
        """
        Write ALC eprofile file (CHM-like format with backscatter data)
        """
        from euliaa_proc.eprofile_bsc import EProfileBSCMeasurement
        logger.info('Writing ALC eprofile file')
        if not hasattr(self.args, 'config_eprofile_bsc') or self.args.config_eprofile_bsc is None:
            logger.error('No config_eprofile_bsc specified, exiting')
            exit()
        if not hasattr(self.args, 'chm_template_file') or self.args.chm_template_file is None:
            logger.error('No chm_template_file specified, exiting')
            exit()

        eprofile_bsc_meas = EProfileBSCMeasurement(
            config_eprofile_bsc_path=self.args.config_eprofile_bsc, 
            l2a_data=self.meas.data, 
            chm_template_path=self.args.chm_template_file,
            line_of_sight_idx=getattr(self.args, 'line_of_sight_idx', 0),
            conf_qc_file=self.meas.qc_conf_file
        )
        eprofile_bsc_meas.load_data()
        eprofile_bsc_writer = Writer(eprofile_bsc_meas, output_file=self.args.output_nc_eprofile_bsc,use_encoding=False)
        eprofile_bsc_writer.write_nc()
        logger.info(f'Wrote ALC-EPROFILE file successfully to {self.args.output_nc_eprofile_bsc}\n')


if __name__=='__main__':
    import os
    cwd = os.getcwd()

    import argparse
    parser = argparse.ArgumentParser(description='Write netCDF file')
    parser.add_argument('--hdf5_file', type=str, help='Path to the HDF5 file', default='/home/oper/euliaa_proc/data/BankExport3.h5')
    parser.add_argument('--config', type=str, help='Path to the config file', default=os.path.join(cwd,'config/config_nc.yaml'))
    parser.add_argument('--config_qc', type=str, help='Path to the config file for quality control', default=os.path.join(cwd,'config/config_qc.yaml'))
    parser.add_argument('--config_eprofile_wind', type=str, help='Path to the config file for DWL eprofile', default=os.path.join(cwd,'config/config_eprofile_wind.yaml'))
    parser.add_argument('--config_eprofile_bsc', type=str, help='Path to the config file for ALC eprofile', default=os.path.join(cwd,'config/config_eprofile_bsc.yaml'))
    parser.add_argument('--chm_template_file', type=str, help='Path to CHM template file for ALC eprofile', default=os.path.join('../data/20251001_pay_CHM200110_0920_000.nc'))
    parser.add_argument('--line_of_sight_idx', type=int, help='Line of sight index for ALC eprofile (0=zenith)', default=0)
    parser.add_argument('--output_nc_l2A', type=str, help='Path to the output netCDF file for L2A', default=os.path.join(cwd,'../data/TestNC_L2A.nc'))
    parser.add_argument('--output_nc_l2B', type=str, help='Path to the output netCDF file for L2B', default=os.path.join(cwd,'../data/TestNC_L2B.nc'))
    parser.add_argument('--output_nc_eprofile_wind', type=str, help='Path to the output netCDF file for DWL eprofile', default=os.path.join(cwd,'../data/TestNC_EPROFILE.nc'))
    parser.add_argument('--output_nc_eprofile_bsc', type=str, help='Path to the output netCDF file for ALC eprofile', default=os.path.join(cwd,'../data/TestNC_EPROFILE_BSC.nc'))
    parser.add_argument('--bufr_types', nargs='+', default=['wind', 'temperature'])
    parser.add_argument('--output_bufr', type=str, help='Path to the output BUFR file', default=os.path.join(cwd,'../data/Test_BUFR.bufr'))
    parser.add_argument('--fig_dir', type=str, help='Path to the directory where quicklooks are saved', default=os.path.join(cwd,'quicklooks/'))
    parser.add_argument('--fig_prefix', type=str, help='Prefix of the quicklook figure', default='quicklook_')
    args = parser.parse_args()

    runner = Runner(args)
    runner.run_processing()
    runner.write_dwl_eprofile()
    runner.write_alc_eprofile()
    runner.write_l2a()
    runner.write_l2b()
    runner.encode_bufr()
    # runner.make_quicklooks()
