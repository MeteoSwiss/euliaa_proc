import xarray as xr
from netCDF4 import Dataset
import pandas as pd
import yaml
import numpy as np
from utils import get_conf, correct_dim_scalar_fields, compute_lat_lon
ENC_NO_FILLVALUE = None

class Writer():

    def __init__(self, data_in, output_file, conf_nc_file):
        self.output_file = output_file
        self.conf_nc = get_conf(conf_nc_file)
        self.data = data_in
        self.config_dims = self.conf_nc['dimensions']['unlimited'] + self.conf_nc['dimensions']['fixed']
        correct_dim_scalar_fields(self.conf_nc['variables'])

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
            unlimited_dims=self.conf_nc['dimensions']['unlimited']
        )
        for var in list(self.data.data_vars)+list(self.data.coords):
            if not(var in self.conf_nc['variables'].keys()):
                print('Warning, %s not in config keys'%var)
                continue
            specs = self.conf_nc['variables'][var]
            self.set_fillvalue(var,specs)
            if 'type' in specs.keys():
                self.data[var].encoding.update(dtype=specs['type']) # TO DO does this really work
            if 'attributes' in specs.keys():
                self.data[var].attrs.update(specs['attributes'])
        self.data.to_netcdf(self.output_file)



if __name__=='__main__':

    hdf5file = '/home/bia/Data/IAP/BankExport.h5'
    config = '/home/bia/euliaa_postproc/configs/config_nc.yaml'
    config_qc = '/home/bia/euliaa_postproc/configs/config_qc.yaml'
    output_nc_l2A = '/home/bia/euliaa_postproc/data/TestNC_L2A.nc'
    output_nc_l2B = '/home/bia/euliaa_postproc/data/TestNC_L2B.nc'

    from measurement import Measurement, H5Reader
    meas = H5Reader(config, hdf5file,conf_qc_file=config_qc)
    meas.read_hdf5_file()
    meas.load_attrs()
    meas.load_data()
    meas.add_lat_lon()
    meas.add_quality_flag()
    meas.add_clouds()
    nc_writer = Writer(meas.data,output_file=output_nc_l2A,conf_nc_file=config)
    nc_writer.write_nc()
    print('Wrote L2A successfully\n')

    meas.subsel_stripped_profile()
    nc_writer_l2b = Writer(meas.data,output_file=output_nc_l2B,conf_nc_file=config)
    nc_writer_l2b.write_nc()
    print('Wrote L2B successfully\n')
