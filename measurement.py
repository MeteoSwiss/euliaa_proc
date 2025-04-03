import xarray as xr
from netCDF4 import Dataset
import pandas as pd
import yaml
import numpy as np
from utils import get_conf, correct_dim_scalar_fields, check_var_in_ds, compute_lat_lon, flag_var
from cloud_detection import in_house_cloud_detection

class Measurement():
    def __init__(self, conf_file, data=None, conf_qc_file=None):
        self.conf = get_conf(conf_file)
        if data:
            self.data = data
        else:
            self.data = xr.Dataset()
        if conf_qc_file:
            self.qc_conf = get_conf(conf_qc_file)
        self.config_dims = self.conf['dimensions']['unlimited'] + self.conf['dimensions']['fixed']
        correct_dim_scalar_fields(self.conf['variables'])


    def add_var(self, var_dict):
        """if additional var should be added separately
        Input:
            var_dict = {'var_name': (dim, data)} or {'var_name':(dim, data, {attrs})}
        """
        for var_name, var_data in var_dict.items():
            self.data[var_name] = var_data

    def add_lat_lon(self):
        self.data['latitude_mie'], self.data['longitude_mie'] = compute_lat_lon(lat_station=self.data.station_latitude, lon_station=self.data.station_longitude, altitude=self.data.altitude_mie)
        self.data['latitude_ray'], self.data['longitude_ray'] = compute_lat_lon(lat_station=self.data.station_latitude, lon_station=self.data.station_longitude, altitude=self.data.altitude_ray)

    def add_clouds(self,method='in_house',**kwargs):
        if 'field_of_view' in self.data.keys() and len(self.data.field_of_view)>1:
            data_zen = self.data.sel(field_of_view='zenith')
        else:
            data_zen = self.data
        cloud_ds = in_house_cloud_detection(data_zen,**kwargs)
        self.data = xr.merge([self.data, cloud_ds])

    def add_quality_flag(self):
        self.data.w_mie.values = self.data.w_mie.values-self.qc_conf['CORRECTION'] # first file from iap has a velocity bias
        self.data['w_mie_flag'] = flag_var(self.data, 'w_mie', 'w_mie_err', var_min_thres=-self.qc_conf['W_ABS_THRES'], var_max_thres=self.qc_conf['W_ABS_THRES'], var_err_thres=self.qc_conf['W_ERR_THRES'])
        self.data['u_mie_flag'] = flag_var(self.data, 'u_mie', 'u_mie_err', var_min_thres=-self.qc_conf['U_V_ABS_THRES'], var_max_thres=self.qc_conf['U_V_ABS_THRES'], var_err_thres=self.qc_conf['U_V_ERR_THRES'])
        self.data['v_mie_flag'] = flag_var(self.data, 'v_mie', 'v_mie_err', var_min_thres=-self.qc_conf['U_V_ABS_THRES'], var_max_thres=self.qc_conf['U_V_ABS_THRES'], var_err_thres=self.qc_conf['U_V_ERR_THRES'])
        self.data['temperature_int_flag'] = flag_var(self.data, 'temperature_int', 'temperature_int_err', var_min_thres=self.qc_conf['TEMP_MIN_THRES'], var_max_thres=self.qc_conf['TEMP_MAX_THRES'], var_err_thres=self.qc_conf['TEMP_ERR_THRES'])
        self.data['u_v_flag']= xr.ufuncs.maximum(self.data.u_mie_flag,self.data.v_mie_flag)

        if self.qc_conf['INVALID_TO_NAN']:
            for var in ['u_mie', 'v_mie', 'w_mie', 'temperature_int']:
                self.data[var] = self.data[var].where(self.data[var+'_flag']<1, np.nan)


    def subsel_stripped_profile(self):
        self.data = self.data.sel(altitude_mie=slice(0,self.qc_conf['MAX_ALTITUDE']),field_of_view='zenith')
        self.data = self.data.isel(time=0)
        self.data = self.data[self.qc_conf['VARS_TO_KEEP']]





class H5Reader(Measurement):

    def __init__(self, conf_file, h5_data_file,**kwargs):
        super().__init__(conf_file,**kwargs)
        self.data_file = h5_data_file


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
        nc2 = Dataset(self.data_file.replace('.h5','2.h5'), diskless=True, persist=False) # For now I had to hardcode this because of an error in the first file - to be removed
        self.rec = xr.open_dataset(xr.backends.NetCDF4DataStore(nc.groups.get('rec')))
        self.glo = xr.open_dataset(xr.backends.NetCDF4DataStore(nc2.groups.get('glo')))
        if load_units:
            self.units_glo = xr.open_dataset(xr.backends.NetCDF4DataStore(nc.groups.get('units').groups.get('glo')))
            self.units_rec = xr.open_dataset(xr.backends.NetCDF4DataStore(nc.groups.get('units').groups.get('rec')))


    def load_attrs(self):
        """prepare list of attributes; checks whether value should be fetched in hdf5"""
        ds_attrs = self.conf['attributes'].copy()
        for attr in ds_attrs:
            if self.conf['attributes'][attr] is None:
                ds_attrs[attr] = ''
            if type(self.conf['attributes'][attr])==dict:
                if 'original_hdf5' in self.conf['attributes'][attr].keys():
                    hdf5_group = self.conf['attributes'][attr]['original_hdf5']['hdf5_group']
                    if hdf5_group == 'rec':
                        hdf5_ds = self.rec
                    elif hdf5_group == 'glo':
                        hdf5_ds = self.glo
                    ds_attrs[attr] = hdf5_ds[self.conf['attributes'][attr]['original_hdf5']['hdf5_var_name']].data.item()
        self.data.attrs = ds_attrs


    def load_data(self):
        """load the data from the hdf5 file or config"""

        for var, specs in self.conf['variables'].items():
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








if __name__=='__main__':

    hdf5file = '/home/bia/Data/IAP/BankExport.h5'
    config = '/home/bia/euliaa_postproc/config_nc.yaml'
    # output_nc = 'TestNC_var_per_fov2.nc'
    output_nc = '/home/bia/euliaa_postproc/data/TestNC2.nc'
    meas = Measurement_L2A(config,hdf5file)
    meas.read_hdf5_file()
    meas.load_attrs()
    meas.load_data()
