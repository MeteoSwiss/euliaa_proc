import xarray as xr
from netCDF4 import Dataset
import pandas as pd
import yaml
import numpy as np
from utils import get_conf, correct_dim_scalar_fields, check_var_in_ds, compute_lat_lon, flag_var, get_noise_vect_from_da
from cloud_detection import in_house_cloud_detection
from log import logger

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

    def add_time_bnds(self):
        if not ('time_bnds' in self.data.keys()) and ('time_integration' in self.data.keys()):
            time_start = self.data['time'].values - self.data['time_integration'].values/2
            time_stop = self.data['time'].values + self.data['time_integration'].values/2
            self.data['time_bnds'] = (('time', 'bnds'), np.stack([time_start, time_stop], axis=-1))
            logger.info('Time bounds added to the dataset')

    def add_noise_and_snr(self):
        for scat in ['mie', 'ray']:
            if f'signal_{scat}' in self.data.keys():
                self.data[f'noise_level_{scat}'] = get_noise_vect_from_da(self.data[f'signal_{scat}'])
                self.data[f'snr_{scat}'] = self.data[f'signal_{scat}']/self.data[f'noise_level_{scat}']

    def add_clouds(self,**kwargs):
        """
        Add cloud detection to the dataset
        The cloud detection is done by default using the in-house method (others not implemented yet)
        The self.data dataset is modified in place, with new data_vars corresponding to the cloud fields (cloud_mask, below_cloud_top, above_cloud_base, cloud_base, cloud_top)
        """
        # if 'line_of_sight' in self.data.keys() and len(self.data.line_of_sight)>1:
        #     data_zen = self.data.backscatter_coef.sel(line_of_sight='zenith').copy(deep=True)
        # else:
        data_zen = self.data.backscatter_coef.copy(deep=True)
        if 'backscatter_coef_flag' in self.data.keys():
            data_zen = data_zen.where(self.data.backscatter_coef_flag==0, np.nan)
        # self.data['bscnew'] = data_zen
        if 'line_of_sight' in self.data.keys() and len(self.data.line_of_sight)>1:
            cloud_ds_list = []
            for i, los in enumerate(self.data.line_of_sight.values):
                cloud_ds_list.append(in_house_cloud_detection(data_zen[:,:,i],**kwargs))
            self.data = xr.merge([self.data, xr.concat(cloud_ds_list, dim='line_of_sight')])
        else:
            cloud_ds = in_house_cloud_detection(data_zen,**kwargs)
            self.data = xr.merge([self.data, cloud_ds])



    def add_quality_flag(self, var_list = ['u_mie', 'v_mie', 'w_mie', 'temperature_int', 'backscatter_coef']):
        """
        Add quality flag to the variables in var_list
        The flag is computed as follows:
        - flag_invalid: 1 if the variable is outside the min/max threshold
        - flag_snr: 2 if the SNR is below the threshold
        - flag_err: 4 if the error is above the threshold
        Total flag = flag_invalid + flag_snr + flag_err
        0 = no flag
        -9 = missing data
        """
        for var in var_list:
            scat = 'mie' if any('_mie' in d for d in self.data[var].dims) else 'ray'
            flag_invalid = flag_var(self.data, var, var_min_thres=self.qc_conf['THRES_MIN'][var], var_max_thres=self.qc_conf['THRES_MAX'][var]) # -> flag = 1
            if not ('line_of_sight' in self.data[var].dims):
                if 'line_of_sight' in self.conf['variables'][var]['attributes']:
                    snr_los = self.conf['variables'][var]['attributes']['line_of_sight']
                else:
                    logger.warning(f'Warning: line_of_sight not found in {var} attributes nor dimensions, setting SNR flag to 0')
                    # flag_snr = xr.zeros_like(self.data[var])
                    snr_los = None
            else:
                snr_los = 'all'
            flag_snr = flag_var(self.data, var, snr_key=f'snr_{scat}',snr_thres=self.qc_conf['SNR_THRES'][var], snr_los=snr_los) # -> flag = 2
            flag_err = flag_var(self.data, var, err_key=f'{var}_err', var_err_thres=self.qc_conf['ERR_THRES'][var])  # -> flag = 4
            self.data[f'{var}_flag'] = flag_err + flag_snr + flag_invalid


    def add_flag_below_cloud_top(self, var_list = ['temperature_int']):
        """
        Add cloud flag to the variables in var_list
        The flag is computed as follows:
        - flag_cloud: 8 if the cloud mask is > 0
        """
        if not ('below_cloud_top' in self.data.keys()):
            logger.warning('No cloud top data available, skipping cloud flag')
            return
        cloud_flag = xr.where(self.data['below_cloud_top'] > 0, 8, 0)
        for var in var_list:
            self.data[f'{var}_flag'] += cloud_flag
        return

    def add_flag_missing_data(self):
        for var in self.data.data_vars.keys():
            if f'{var}_flag' in self.data.keys():
                self.data[f'{var}_flag'] = self.data[f'{var}_flag'].where(~xr.ufuncs.isnan(self.data[var]), -9) # flag = -9 if NaN


    def add_quality_flag_old(self):
        """
        Add quality flag
        The flag is computed as follows, for each variable (with some var-specific adjustments): high error + invalid value + no data + low snr
        Then if 'INVALID_TO_NAN' is set to True, the variable is set to NaN if the flag is > 0.
        """
        # self.data.w_mie.values = self.data.w_mie.values-self.qc_conf['CORRECTION'] # first file from iap has a velocity bias
        self.data['w_mie_flag'] = flag_var(self.data, 'w_mie', err_key='w_mie_err', var_min_thres=-self.qc_conf['W_ABS_THRES'], var_max_thres=self.qc_conf['W_ABS_THRES'], var_err_thres=self.qc_conf['W_ERR_THRES'])
        self.data['u_mie_flag'] = flag_var(self.data, 'u_mie', err_key='u_mie_err', var_min_thres=-self.qc_conf['U_V_ABS_THRES'], var_max_thres=self.qc_conf['U_V_ABS_THRES'], var_err_thres=self.qc_conf['U_V_ERR_THRES'])
        self.data['v_mie_flag'] = flag_var(self.data, 'v_mie', err_key='v_mie_err', var_min_thres=-self.qc_conf['U_V_ABS_THRES'], var_max_thres=self.qc_conf['U_V_ABS_THRES'], var_err_thres=self.qc_conf['U_V_ERR_THRES'])
        self.data['temperature_int_flag'] = flag_var(self.data, 'temperature_int', err_key='temperature_int_err', var_min_thres=self.qc_conf['TEMP_MIN_THRES'], var_max_thres=self.qc_conf['TEMP_MAX_THRES'], var_err_thres=self.qc_conf['TEMP_ERR_THRES'])
        self.data['u_v_flag']= xr.ufuncs.maximum(self.data.u_mie_flag,self.data.v_mie_flag)
        self.data['backscatter_coef_flag'] = flag_var(self.data, 'backscatter_coef', var_min_thres=self.qc_conf['BSC_MIN_THRES'],snr_key='snr_mie',snr_thres=self.qc_conf['SNR_THRES'])
        if self.qc_conf['INVALID_TO_NAN']:
            for var in ['u_mie', 'v_mie', 'w_mie', 'temperature_int', 'backscatter_coef']:
                self.data[var] = self.data[var].where(self.data[var+'_flag']<1, np.nan)

    def set_invalid_to_nan(self):
        """
        Set the variables to NaN if the flag is > 0
        """
        for var in self.data.data_vars.keys():
            if not (f'{var}_flag' in self.data.keys()):
                continue
            self.data[var] = self.data[var].where(self.data[var+'_flag']==0, np.nan)


    def subsel_stripped_profile(self, los=0):
        """
        Subset the data to keep only a profile in one field of view and the altitude range + variable list specified in the qc config
        Used to create L2B
        """
        self.data = self.data.sel(altitude_mie=slice(0,self.qc_conf['MAX_ALTITUDE']),line_of_sight=los)
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

        # nc2 = Dataset(self.data_file.replace('3.h5','2.h5'), diskless=True, persist=False) # For now I had to hardcode this because of an error in the first file - to be removed
        nc2 = nc #Dataset('/home/bia/Data/IAP/BankExport2.h5', diskless=True, persist=False)
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
                logger.info('lat/lon computed at the end')
                continue
            # Load value from config if exists
            if 'value' in specs and not(specs['value'] is None):
                self.data[var] = (specs['dim'], specs['value'])

            # Find hdf5 group
            if (not ('original_hdf5' in specs.keys())) or (not ('hdf5_group' in specs['original_hdf5'].keys())) or \
                not(specs['original_hdf5']) or not (specs['original_hdf5']['hdf5_group']) or not (specs['original_hdf5']['hdf5_var_name']):
                # logger.info(f'{var}: this variable is not part of the hdf5')
                continue
            if (not (specs['original_hdf5']['hdf5_group'] in ['rec', 'glo'])) or (not ('hdf5_var_name' in specs['original_hdf5'].keys())) :
                logger.warning(f'{var}: the hdf5_group or hdf5_var_name is invalid, skipping')
                continue
            hdf5_ds = self.rec if specs['original_hdf5']['hdf5_group'] == 'rec' else self.glo

            hdf5_var = specs['original_hdf5']['hdf5_var_name']
            if not check_var_in_ds(hdf5_ds, hdf5_var):
                logger.warning(f'{var}: No corresponding variable in original hdf5 file')
                continue
            if type(hdf5_var)==list:
                self.data[var] = (specs['dim'], np.stack([hdf5_ds[var_los].data for var_los in hdf5_var],axis=-1))
            elif hdf5_ds[hdf5_var].ndim == 0 and len(specs['dim'])>0:
                self.data[var] = (specs['dim'], np.full(tuple([len(self.data[d]) for d in specs['dim']]), hdf5_ds[hdf5_var].data))
            else:
                self.data[var] = (specs['dim'],  hdf5_ds[hdf5_var].data)








if __name__=='__main__':
    import os
    cwd = os.getcwd()

    hdf5file = '/data/euliaa-test/TESTS/BankExport.h5'
    config = os.path.join(cwd,'configs/config_nc.yaml')
    config_qc = os.path.join(cwd,'configs/config_qc.yaml')
    meas = H5Reader(config,hdf5file, conf_qc_file = config_qc)
    meas.read_hdf5_file()
    meas.load_attrs()
    meas.load_data()
