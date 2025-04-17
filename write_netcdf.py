import xarray as xr
from netCDF4 import Dataset
import pandas as pd
import yaml
import numpy as np
from utils import get_conf, correct_dim_scalar_fields
ENC_NO_FILLVALUE = None

class Writer():

    def __init__(self, measurement, output_file, conf_file):
        self.output_file = output_file
        self.conf = measurement.conf
        self.data = measurement.data
        self.config_dims = self.conf['dimensions']['unlimited'] + self.conf['dimensions']['fixed']
        correct_dim_scalar_fields(self.conf['variables'])

    def set_fillvalue(self, var, specs):
        """set the fill value of var by taking care not to remove any fill value for dimensions for CF compliance

        Args:
            var (str): the name of the variable of whom the dimension shall be checked
            specs: specifications for this variable from config. Must contain the key 'dim' with a list of dimensions.
        """
        if var in self.config_dims or specs['_FillValue'] is None:  # using None in fillna (else clause) destroys dtype
            self.data[var].encoding.update(_FillValue=ENC_NO_FILLVALUE)
        else:
            self.data[var] = self.data[var].fillna(specs['_FillValue'])  # don't use with _FillValue=None, dtype problem
            self.data[var].encoding.update(_FillValue=specs['_FillValue'])

    def write_nc(self):
        """write netCDF file - copied from mwr_raw2l1, for clean nc writing"""
        self.data.encoding.update(
            unlimited_dims=self.conf['dimensions']['unlimited']
        )
        for var in list(self.data.data_vars)+list(self.data.coords):
            if not(var in self.conf['variables'].keys()):
                print(f'Warning, {var} not in config keys')
                continue
            specs = self.conf['variables'][var]
            self.set_fillvalue(var,specs)
            if 'type' in specs.keys():
                self.data[var].encoding.update(dtype=specs['type']) # TO DO does this really work
            if 'attributes' in specs.keys():
                self.data[var].attrs.update(specs['attributes'])
        self.data.to_netcdf(self.output_file)



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
    args = parser.parse_args()

    # hdf5file = '/data/s3euliaa/TESTS/BankExport3.h5'
    # config = os.path.join(cwd,'configs/config_nc.yaml')
    # config_qc = os.path.join(cwd,'configs/config_qc.yaml')
    # output_nc_l2A = os.path.join(cwd,'data/TestNC_L2A.nc')
    # output_nc_l2B = os.path.join(cwd,'data/TestNC_L2B.nc')

    from measurement import H5Reader
    print('Reading measurement from hdf5 file...')
    meas = H5Reader(args.config, args.hdf5_file,conf_qc_file=args.config_qc)
    meas.read_hdf5_file()
    meas.load_attrs()
    meas.load_data()

    print('Adding altitude-dependent lat and lon arrays')
    meas.add_lat_lon()

    print('Computing noise level and SNR...')
    meas.add_noise_and_snr()

    print('Adding basic quality flag...')
    meas.add_quality_flag()

    print('Cloud detection...')
    meas.add_clouds()

    print('Completing quality flag...')
    meas.add_flag_below_cloud_top()
    meas.add_flag_missing_data()

    print('Writing L2A...')
    nc_writer = Writer(meas,output_file=args.output_nc_l2A,conf_file=args.config)
    nc_writer.write_nc()
    print('Wrote L2A successfully\n')

    print('Writing L2B...')
    meas.subsel_stripped_profile()
    nc_writer_l2b = Writer(meas,output_file=args.output_nc_l2B,conf_file=args.config)
    nc_writer_l2b.write_nc()
    print('Wrote L2B successfully\n')
