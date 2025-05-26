from euliaa_proc.utils.conf_utils import correct_dim_scalar_fields
import datetime
from euliaa_proc.log import logger
import tempfile
ENC_NO_FILLVALUE = None

class Writer():

    def __init__(self, measurement, output_file, conf_file):
        self.output_file = output_file
        self.conf = measurement.conf
        self.data = measurement.data
        self.config_dims = self.conf['dimensions']['unlimited'] + self.conf['dimensions']['fixed']
        correct_dim_scalar_fields(self.conf['variables'])


    def get_encoding_dict(self):
        encoding_dict = {}
        for var in list(self.data.data_vars)+list(self.data.coords):
            encoding_dict[var] = {}
            specs = self.conf['variables'][var]
            # prepare encoding
            if 'type' in specs.keys():
                encoding_dict[var]['dtype']=specs['type']
            if '_FillValue' in specs.keys():
                encoding_dict[var]['_FillValue'] = specs['_FillValue']
            if not (any(encoding_dict[var])):
                del encoding_dict[var]

    def add_history_attr(self):
        """add global attribute 'history' with date and version of code run"""
        import getpass
        import socket
        # get current time in UTC
        current_time_str = datetime.datetime.now(tz=datetime.timezone.utc).strftime('%Y-%m-%d %H:%M:%S')  # ensure UTC
        username = getpass.getuser()
        host = socket.gethostname()
        version = self.conf["attributes"]["version"]
        hist_str = f'Created {current_time_str} by user {username} on {host}, with euliaa_proc-V{version}'
        self.data.attrs['history'] = hist_str


    def write_nc(self):
        """write netCDF file - for clean nc writing"""
        self.data.encoding.update(
            unlimited_dims=self.conf['dimensions']['unlimited']
        )

        for var in list(self.data.data_vars)+list(self.data.coords):
            # check if var is in config, if not, remove it from data
            if not(var in self.conf['variables'].keys()):
                logger.warning(f'{var} not in config keys, removing from data')
                self.data = self.data.drop_vars(var)
                continue

            specs = self.conf['variables'][var]
            # add attributes from config file
            if 'attributes' in specs.keys():
                self.data[var].attrs.update(specs['attributes'])

        # add history
        self.add_history_attr()

        # load encoding dict
        encoding_dict = self.get_encoding_dict()
        if self.output_file.startswith('s3://'):
            import fsspec
            with tempfile.NamedTemporaryFile(suffix=".nc") as tmpfile:
                self.data.to_netcdf(tmpfile.name, encoding=encoding_dict)
                tmpfile.seek(0)
                # write to S3 using fsspec
                with fsspec.open(self.output_file, mode='wb',s3=dict(profile='default')) as outfile:
                    outfile.write(tmpfile.read())
                tmpfile.flush()
        else:
            # write to local file
            self.data.to_netcdf(self.output_file, encoding=encoding_dict) # valid encodings: {'least_significant_digit', 'endian', 'compression', 'quantize_mode', 'blosc_shuffle', 'shuffle', 'szip_pixels_per_block', 'contiguous', 'significant_digits', 'zlib', 'fletcher32', 'dtype', 'complevel', 'chunksizes', 'szip_coding', '_FillValue'}


if __name__=='__main__':
    import os
    cwd = os.getcwd()

    import argparse
    parser = argparse.ArgumentParser(description='Write netCDF file')
    parser.add_argument('--hdf5_file', type=str, help='Path to the HDF5 file', default=os.path.join(cwd,'data/BankExport3.h5'))
    parser.add_argument('--config', type=str, help='Path to the config file', default=os.path.join(cwd,'config/config_nc.yaml'))
    parser.add_argument('--config_qc', type=str, help='Path to the config file for quality control', default=os.path.join(cwd,'config/config_qc1.yaml'))
    parser.add_argument('--output_nc_l2A', type=str, help='Path to the output netCDF file for L2A', default=os.path.join(cwd,'data/TestNC_L2A.nc'))
    parser.add_argument('--output_nc_l2B', type=str, help='Path to the output netCDF file for L2B', default=os.path.join(cwd,'data/TestNC_L2B.nc'))
    args = parser.parse_args()

    # hdf5file = '/data/s3euliaa/TESTS/BankExport3.h5'
    # config = os.path.join(cwd,'config/config_nc.yaml')
    # config_qc = os.path.join(cwd,'config/config_qc.yaml')
    # output_nc_l2A = os.path.join(cwd,'data/TestNC_L2A.nc')
    # output_nc_l2B = os.path.join(cwd,'data/TestNC_L2B.nc')

    from measurement import H5Reader
    logger.info('Reading measurement from hdf5 file...')
    meas = H5Reader(args.config, args.hdf5_file,conf_qc_file=args.config_qc)
    meas.read_hdf5_file()
    meas.load_attrs()
    meas.load_data()

    logger.info('Adding altitude-dependent lat and lon arrays')
    meas.add_lat_lon()

    logger.info('Computing noise level and SNR...')
    meas.add_noise_and_snr()

    logger.info('Adding basic quality flag...')
    meas.add_quality_flag()

    logger.info('Cloud detection (for now, only transparent clouds)...')
    meas.add_clouds()

    logger.info('Completing quality flag...')
    meas.add_flag_below_cloud_top()
    meas.add_flag_missing_data()

    logger.info('Writing L2A...')
    nc_writer = Writer(meas,output_file=args.output_nc_l2A,conf_file=args.config)
    nc_writer.write_nc()
    logger.info('Wrote L2A successfully\n')

    logger.info('Writing L2B...')
    meas.subsel_stripped_profile()
    meas.set_invalid_to_nan() # set invalid data to NaN for L2B
    nc_writer_l2b = Writer(meas,output_file=args.output_nc_l2B,conf_file=args.config)
    nc_writer_l2b.write_nc()
    logger.info('Wrote L2B successfully\n')
