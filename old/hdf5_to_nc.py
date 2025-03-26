import xarray as xr
from netCDF4 import Dataset
import pandas as pd
import yaml
import numpy as np
from utils import get_conf, correct_dim_scalar_fields, check_var_in_ds, compute_lat_lon
ENC_NO_FILLVALUE = None

class Measurement():

    def __init__(self, data_file, conf_nc_file):
        self.data_file = data_file
        self.conf_nc = get_conf(conf_nc_file)
        self.data = xr.Dataset()
        self.config_dims = self.conf_nc['dimensions']['unlimited'] + self.conf_nc['dimensions']['fixed']
        correct_dim_scalar_fields(self.conf_nc['variables'])


    def read_hdf5_file(self, load_units=False):
        """load hdf5 produced by IAP routine
        Inputs:
            hdf5_file: path to hdf5 file
            load_units: whether or not to load the units datasets (in principle not used, units stored in config file)
        Outputs:
            rec: xarray Dataset with data from 'rec' group of hdf5 file; contains measurement data
            glo: xarray Dataset with data from 'glo' group of hdf5 file; contains mostly metadata
        """
        nc = Dataset(self.data_file, diskless=True, persist=False)
        nc2 = Dataset('/home/bia/Data/IAP/BankExport2.h5', diskless=True, persist=False) # For now I had to hardcode this because of an error in the first file - to be removed
        self.rec = xr.open_dataset(xr.backends.NetCDF4DataStore(nc.groups.get('rec')))
        self.glo = xr.open_dataset(xr.backends.NetCDF4DataStore(nc2.groups.get('glo')))
        if load_units:
            self.units_glo = xr.open_dataset(xr.backends.NetCDF4DataStore(nc.groups.get('units').groups.get('glo')))
            self.units_rec = xr.open_dataset(xr.backends.NetCDF4DataStore(nc.groups.get('units').groups.get('rec')))


    def load_attrs(self):
        """prepare list of attributes; checks whether value should be fetched in hdf5"""
        ds_attrs = self.conf_nc['attributes'].copy()
        for attr in ds_attrs:
            if self.conf_nc['attributes'][attr] is None:
                ds_attrs[attr] = ''
            if type(self.conf_nc['attributes'][attr])==dict:
                if 'original_hdf5' in self.conf_nc['attributes'][attr].keys():
                    hdf5_group = self.conf_nc['attributes'][attr]['original_hdf5']['hdf5_group']
                    if hdf5_group == 'rec':
                        hdf5_ds = self.rec
                    elif hdf5_group == 'glo':
                        hdf5_ds = self.glo
                    ds_attrs[attr] = hdf5_ds[self.conf_nc['attributes'][attr]['original_hdf5']['hdf5_var_name']].data.item()
        self.data.attrs = ds_attrs


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


    def load_data(self):
        """load the data from the hdf5 file or config"""

        for var, specs in self.conf_nc['variables'].items():
            if var in ['latitude_mie', 'latitude_ray', 'longitude_mie', 'longitude_ray']:
                print('lat/lon computed at the end')
                continue
            # Load value from config if exists
            if 'value' in specs and not(specs['value'] is None):
                self.data[var] = (specs['dim'], specs['value'])

            # Find hdf5 group
            if (not ('original_hdf5' in specs.keys())) or (not ('hdf5_group' in specs['original_hdf5'].keys()))\
                  or (not (specs['original_hdf5']['hdf5_group'] in ['rec', 'glo'])) or (not ('hdf5_var_name' in specs['original_hdf5'].keys())) :
                print(var, ': this variable was not implemented in the hdf5 or the hdf5_group is invalid')
                continue
            hdf5_ds = self.rec if specs['original_hdf5']['hdf5_group'] == 'rec' else self.glo

            hdf5_var = specs['original_hdf5']['hdf5_var_name']
            if not check_var_in_ds(hdf5_ds, hdf5_var):
                print(var,': No corresponding variable in original hdf5 file')
                continue
            if type(hdf5_var)==list:
                self.data[var] = (specs['dim'], np.stack([hdf5_ds[var_fov].data for var_fov in hdf5_var],axis=-1))
            else:
                self.data[var] = (specs['dim'],  hdf5_ds[hdf5_var].data)


    def write_nc(self,out_file):
        """write netCDF file - copied from mwr_raw2l1, for clean nc writing"""
        self.data.encoding.update(
            unlimited_dims=self.conf_nc['dimensions']['unlimited']
        )
        for var in list(self.data.data_vars)+list(self.data.coords):
            specs = self.conf_nc['variables'][var]
            self.set_fillvalue(var,specs)
            if 'type' in specs.keys():
                self.data[var].encoding.update(dtype=specs['type']) # TO DO does this really work
            if 'attributes' in specs.keys():
                self.data[var].attrs.update(specs['attributes'])
        self.data.to_netcdf(out_file)

    def add_var(self, var_dict):
        """if additional var should be added separately
        Input:
            var_dict = {'var_name': (dim, data)} or {'var_name':(dim, data, {attrs})}
        """
        for var_name, var_data in var_dict.items():
            self.data[var_name] = var_data



if __name__=='__main__':

    hdf5file = '/home/bia/Data/IAP/BankExport.h5'
    config = '/home/bia/euliaa_postproc/config_nc.yaml'
    # output_nc = 'TestNC_var_per_fov2.nc'
    output_nc = '/home/bia/euliaa_postproc/data/TestNC2.nc'
    meas = Measurement(hdf5file,config)
    meas.read_hdf5_file()
    meas.load_attrs()
    meas.load_data()

    meas.data['latitude_mie'], meas.data['longitude_mie'] = compute_lat_lon(lat_station=meas.data.station_latitude, lon_station=meas.data.station_longitude, altitude=meas.data.altitude_mie)
    meas.data['latitude_ray'], meas.data['longitude_ray'] = compute_lat_lon(lat_station=meas.data.station_latitude, lon_station=meas.data.station_longitude, altitude=meas.data.altitude_ray)
    meas.write_nc(output_nc)
