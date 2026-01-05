import xarray as xr
from netCDF4 import Dataset
import pandas as pd
import numpy as np
from euliaa_proc.utils.conf_utils import get_conf, correct_dim_scalar_fields
from euliaa_proc.utils.data_utils import check_var_in_ds, compute_lat_lon, flag_var, get_noise_from_da, compute_ldr_and_err, correct_u_v_for_azimuth
from euliaa_proc.utils.cloud_detection import in_house_cloud_detection
from euliaa_proc.log import logger

class Measurement():
    def __init__(self, conf_file, data=None, conf_qc_file=None):
        self.conf = get_conf(conf_file)
        if data:
            self.data = data
        else:
            self.data = xr.Dataset()
        if conf_qc_file:
            self.qc_conf = get_conf(conf_qc_file)
            self.qc_conf_file = conf_qc_file
        if self.conf['dimensions']['unlimited'] and self.conf['dimensions']['fixed']:
            self.config_dims = self.conf['dimensions']['unlimited'] + self.conf['dimensions']['fixed']
        elif self.conf['dimensions']['unlimited']:
            self.config_dims = self.conf['dimensions']['unlimited']
        elif self.conf['dimensions']['fixed']:
            self.config_dims = self.conf['dimensions']['fixed']
        else:
            raise ValueError('No dimensions defined in the config file')
        correct_dim_scalar_fields(self.conf['variables'])


    def add_var(self, var_dict):
        """if additional var should be added separately
        Input:
            var_dict = {'var_name': (dim, data)} or {'var_name':(dim, data, {attrs})}
        """
        for var_name, var_data in var_dict.items():
            self.data[var_name] = var_data

    def correct_altitude(self):
        """
        Correct altitude variables by adding station altitude (what is provided in the L1 is height above ground)
        """
        if 'altitude_ray' in self.data.keys():
            self.data['altitude_ray'] = self.data['altitude_ray'] + self.data['station_altitude']
        if 'altitude_mie' in self.data.keys():
            self.data['altitude_mie'] = self.data['altitude_mie'] + self.data['station_altitude']
        if 'altitude' in self.data.keys():
            self.data['altitude'] = self.data['altitude'] + self.data['station_altitude']

    def add_lat_lon(self):
        self.data['latitude_mie'], self.data['longitude_mie'] = compute_lat_lon(lat_station=self.data.station_latitude, lon_station=self.data.station_longitude, altitude=self.data.altitude_mie)
        self.data['latitude_ray'], self.data['longitude_ray'] = compute_lat_lon(lat_station=self.data.station_latitude, lon_station=self.data.station_longitude, altitude=self.data.altitude_ray)

    def add_time_bnds(self):
        if ('time_bnds' in self.data.keys()):
            logger.info('Time bounds variable already in dataset')
        elif ('time_integration' in self.data.keys()):
            time_start = self.data['time'].values - self.data['time_integration'].values#/2
            time_stop = self.data['time'].values #+ self.data['time_integration'].values/2
            self.data['time_bnds'] = (('time', 'bnds'), np.stack([time_start, time_stop], axis=-1))
            logger.info('Time bounds added to the dataset')
        else:
            dt = np.mean(self.data['time'].values[1:]-self.data['time'].values[:-1])
            time_start = self.data['time'].values - dt#/2
            time_stop = self.data['time'].values #+ dt/2
            self.data['time_bnds'] = (('time', 'bnds'), np.stack([time_start, time_stop], axis=-1))
            self.data['time_integration'] = dt
            logger.warning('Time bounds inferred from time resolution. Time integration missing in original dataset, setting it with time increment')
        
    def add_height_bnds(self):
        """
        TO DO check this with final data format, depending on how the altitude var / dim is etc some bits should be changed / removed
        """
        if 'height_bnds' not in self.conf['variables']:
            logger.info('height_bnds not defined in configuration, skipping')
            return
        if 'height_bnds' in self.data.keys():
            logger.info('Height bounds variable already in dataset')
            return
        
        altitude = self.data['altitude'] if 'altitude' in self.data.keys() else self.data['altitude_mie']
        hb_dims = ('altitude', 'bnds') if 'altitude' in self.data.keys() else ('altitude_mie', 'bnds')
            
        if 'range_integration' in self.data.keys(): # Method 1: Use range_integration if available
            range_int = self.data['range_integration']
            # Handle different dimension scenarios
            if 'line_of_sight' in range_int.dims:
                if 'line_of_sight' in altitude.dims:
                    # Altitude also varies by line of sight - direct calculation
                    alt_start = altitude - range_int / 2
                    alt_stop = altitude + range_int / 2
                else:
                    # Altitude doesn't vary by line of sight - use mean range integration
                    range_int_mean = range_int.mean('line_of_sight') 
                    alt_start = altitude - range_int_mean / 2
                    alt_stop = altitude + range_int_mean / 2
            else:
                # Range integration is scalar or doesn't vary by line of sight
                alt_start = altitude - range_int / 2
                alt_stop = altitude + range_int / 2
            
            # Create the bounds array
            self.data['height_bnds'] = (hb_dims, np.stack([alt_start, alt_stop], axis=-1))
            logger.info('Height bounds added to the dataset using range_integration')
        
        # Method 2: Infer from altitude resolution
        else:
            alt_values = altitude.values    
            if len(alt_values) > 1:
                # Calculate mean altitude difference
                dh = np.mean(alt_values[1:] - alt_values[:-1])
                alt_start = alt_values - dh / 2
                alt_stop = alt_values + dh / 2
                
                # Create the bounds array
                self.data['height_bnds'] = (hb_dims, np.stack([alt_start, alt_stop], axis=-1))
                self.data['range_integration'] = dh
                logger.warning('Height bounds inferred from altitude resolution. Range integration missing in original dataset, setting it with height increment.')
                # print(self.data['height_bnds'].dims)
            else:
                logger.error('Cannot create height_bnds: insufficient altitude points and no range_integration available')
                return
        

    def add_noise_and_snr(self):
        for scat in ['mie', 'ray', 'mie_depol']:
            if f'signal_{scat}' in self.data.keys():
                self.data[f'noise_background_{scat}'], self.data[f'noise_stdv_{scat}']  = get_noise_from_da(self.data[f'signal_{scat}'], calc_stdv=1)
                self.data[f'snr_{scat}'] = (self.data[f'signal_{scat}']-self.data[f'noise_background_{scat}'])/self.data[f'noise_stdv_{scat}']

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
                cloud_ds_list.append(in_house_cloud_detection(data_zen.isel(line_of_sight=i),**kwargs))
            self.data = xr.merge([self.data, xr.concat(cloud_ds_list, dim='line_of_sight')])
        else:
            cloud_ds = in_house_cloud_detection(data_zen,**kwargs)
            self.data = xr.merge([self.data, cloud_ds])

    def add_depolarization_ratio(self, **kwargs):
        # self.data['aerosol_depolarization_ratio'] = self.data['backscatter_coef_depol']/self.data['backscatter_coef'].isel(line_of_sight=0)
        # self.data['aerosol_depolarization_ratio_err'] = 
        if not(('backscatter_coef_depol' in self.data.keys()) and ('backscatter_coef' in self.data.keys())):
            logger.warning('Cannot compute aerosol depolarization ratio: backscatter_coef_depol or backscatter_coef missing')
            return
        logger.info('Computing aerosol depolarization ratio and error')
        bsc_depol = self.data["backscatter_coef_depol"].to_numpy()        # cross-polar
        bsc = self.data["backscatter_coef"].isel(line_of_sight=0).to_numpy()              # co-polar
        bsc_depol_err = self.data["backscatter_coef_depol_err"].to_numpy()    # cross-polar error
        bsc_err = self.data["backscatter_coef_err"].isel(line_of_sight=0).to_numpy()          # co-polar error
        ldr, ldr_err = compute_ldr_and_err(bsc_depol, bsc, bsc_depol_err, bsc_err)
        self.data['aerosol_depolarization_ratio'] = xr.zeros_like(self.data['backscatter_coef_depol'])
        self.data['aerosol_depolarization_ratio_err'] = xr.zeros_like(self.data['backscatter_coef_depol_err'])
        self.data['aerosol_depolarization_ratio'].values = ldr
        self.data['aerosol_depolarization_ratio_err'].values = ldr_err
        self.data['aerosol_depolarization_ratio_flag'] = xr.ufuncs.maximum(self.data['backscatter_coef_depol_flag'], self.data['backscatter_coef_flag'].isel(line_of_sight=0)) 

    
    def correct_azimuth_offset(self):
        """
        Correct the u and v components for the azimuth angle of the line of sight
        """
        logger.info('Correcting u/v for azimuth offset')
        if 'azimuth_offset' in self.data.keys():
            azimuth_deg = self.data['azimuth_offset'].values
        elif 'azimuth_offset' in self.conf['attributes'].keys():
            azimuth_deg = self.conf['attributes']['azimuth_offset']
        else:
            logger.warning('No azimuth_offset found in data or config, cannot correct u/v for azimuth')
            return
        for var_ending in ['_mie', '_ray', '']:
            u_var = f'u{var_ending}'
            v_var = f'v{var_ending}'
            u_err_var = f'u{var_ending}_err'
            v_err_var = f'v{var_ending}_err'
            u_flag_var = f'u{var_ending}_flag'
            v_flag_var = f'v{var_ending}_flag'
            if (u_var in self.data.keys()) and (v_var in self.data.keys()) and (u_err_var in self.data.keys()) and (v_err_var in self.data.keys()):
                self.data[u_var], self.data[v_var], self.data[u_err_var], self.data[v_err_var] = correct_u_v_for_azimuth(azimuth_deg, self.data[u_var], self.data[v_var], self.data[u_err_var], self.data[v_err_var])
                logger.info(f'Corrected {u_var} and {v_var} for azimuth offset of {azimuth_deg} degrees')
                if azimuth_deg % 90 != 0:
                    self.data[u_flag_var] = xr.ufuncs.maximum(self.data[u_flag_var], self.data[v_flag_var])
                    self.data[v_flag_var] = self.data[u_flag_var]
                elif azimuth_deg % 180 == 0:
                    logger.info(f'Azimuth offset is multiple of 180 degrees, no flag update needed for {u_var} and {v_var}')
                elif azimuth_deg % 90 == 0:
                    self.data[u_flag_var], self.data[v_flag_var] = self.data[v_flag_var], self.data[u_flag_var]
            else:
                logger.warning(f'Cannot correct {u_var} and {v_var} for azimuth offset: missing variable(s): {[var for var in [u_var, v_var, u_err_var, v_err_var] if var not in self.data.keys()]}')            
        
    
    def correct_velocity_offset(self, var_list = ['u_mie', 'v_mie', 'w_mie', 'u', 'v', 'w', 'u_ray', 'v_ray', 'w_ray'] ):
        """
        L1 data is corrected for a velocity offset specified in the qc config file (same offset for u, v, w)
        Inputs:
            var_list: list of variables to correct
        """
        for var in var_list:
            if var in self.data:
                if 'CORRECTION' in self.qc_conf: # This is a general correction applied to all campaigns, so should be in the qc config file
                    self.data[var] = self.data[var] - self.qc_conf['CORRECTION'] # certain files from iap has a velocity bias
                    # logger.info(f'Corrected {var} for velocity offset of {self.qc_conf["CORRECTION"]}')
                # if 'correction_w_offset' in self.conf['attributes']: # This is campaign-dependent so should be in the campaign config, and stored in attributes (relevant to users)
                #     self.data[var] = self.data[var] - self.conf['attributes']['correction_w_offset'] # remove mean w after correction
                #     logger.info(f'Corrected {var} for mean w offset of {self.conf["attributes"]["correction_w_offset"]}')
                if var in ['w_mie', 'w', 'w_ray']:
                    logger.info(f'Corrected {var} for velocity offset of {self.qc_conf["CORRECTION"]}')
                    continue
                self.data[var] = self.data[var]*self.qc_conf['MULTIPLY_BY']# 2 # off-zenith slant # This is a general correction applied to all campaigns, so should be in the qc config file
                logger.info(f'Corrected {var} for velocity offset of {self.qc_conf["CORRECTION"]} and multiplied by {self.qc_conf["MULTIPLY_BY"]}')

    def add_quality_flag(self, var_list = ['u_mie', 'v_mie', 'w_mie', 'temperature_int', 'backscatter_coef', 'backscatter_coef_depol']):
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
            if not (var in self.data.keys()):
                logger.warning(f'Variable {var} not found in dataset, skipping quality flag for this variable')
                continue
            scat = 'mie' if any('_mie' in d for d in self.data[var].dims) else 'ray'
            flag_invalid = flag_var(self.data, var, var_min_thres=self.qc_conf['THRES_MIN'][var], var_max_thres=self.qc_conf['THRES_MAX'][var]) # -> flag = 1
            if not ('line_of_sight' in self.data[var].dims):
                # if 'line_of_sight' in self.conf['variables'][var]['attributes']:
                #     snr_los = self.conf['variables'][var]['attributes']['line_of_sight']
                if var in ['w_mie', 'w_ray', 'w']:
                    snr_los = 0
                elif var in ['u_mie', 'u_ray', 'u']:
                    snr_los = 1
                elif var in ['v_mie', 'v_ray', 'v']:
                    snr_los = 2
                else:
                    logger.warning(f'Warning: line_of_sight not found in {var} attributes nor dimensions, setting SNR flag to 0')
                    # flag_snr = xr.zeros_like(self.data[var])
                    snr_los = None
            else:
                snr_los = 'all'
            flag_snr = flag_var(self.data, var, snr_key=f'snr_{scat}',snr_thres=self.qc_conf['SNR_THRES'][var], snr_los=snr_los) # -> flag = 2
            flag_err = flag_var(self.data, var, err_key=f'{var}_err', var_err_thres=self.qc_conf['ERR_THRES'][var])  # -> flag = 4
            flag_low_range = xr.zeros_like(self.data[var])
            if var in self.qc_conf['MIN_RANGE_FOR_FLAG'].keys(): # add low altitude flag -> flag = 8)
                if 'altitude' in self.data.keys():
                    alt_0 = self.data['altitude'].values[0]
                    flag_low_range = xr.where(self.data['altitude']-alt_0 < self.qc_conf['MIN_RANGE_FOR_FLAG'][var], 8, 0)
                elif 'altitude_mie' in self.data.keys():
                    alt_0 = self.data['altitude_mie'].values[0]
                    flag_low_range = xr.where(self.data['altitude_mie']-alt_0 < self.qc_conf['MIN_RANGE_FOR_FLAG'][var], 8, 0)
            
            self.data[f'{var}_flag'] = flag_err + flag_snr + flag_invalid + flag_low_range

    def add_flag_missing_data(self):
        for var in self.data.data_vars.keys():
            if f'{var}_flag' in self.data.keys():
                self.data[f'{var}_flag'] = self.data[f'{var}_flag'].where(~xr.ufuncs.isnan(self.data[var]), -9) # flag = -9 if NaN


    def add_flag_inside_cloud(self, var_list = ['w_mie']):
        """
        Add cloud flag to the variables in var_list
        The flag is computed as follows:
        - flag_cloud: 16 if the cloud mask is > 0
        """
        if not ('cloud_mask' in self.data.keys()):
            logger.warning('No cloud mask data available, skipping cloud flag')
            return
        cloud_flag = xr.where(self.data['cloud_mask'] > 0, 16, 0)
        for var in var_list:
            if var=='w_mie' or var=='w_ray' or var=='w':
                self.data[f'{var}_flag'] += cloud_flag.isel(line_of_sight=0) # -> flag = 16
            elif var=='v_mie' or var=='v_ray' or var=='v' or var=='u_mie' or var=='u_ray' or var=='u':
                # self.data[f'{var}_flag'] += cloud_flag.isel(line_of_sight=2)
                logger.warning(f'Cloud flag for horizontal wind component {var} not implemented yet, this is easy if los is aligned with N or E but not in general case')
            elif var=='backscatter_coef' or var=='backscatter_coef_depol' or var=='aerosol_depolarization_ratio':
                self.data[f'{var}_flag']+= cloud_flag
        return


    def add_flag_below_cloud_top(self, var_list = ['temperature_int']):
        """
        Add cloud flag to the variables in var_list
        The flag is computed as follows:
        - flag_cloud: 32 if the cloud mask is > 0
        """
        if not ('below_cloud_top' in self.data.keys()):
            logger.warning('No cloud top data available, skipping cloud flag')
            return
        cloud_flag = xr.where(self.data['below_cloud_top'] > 0, 32, 0)
        for var in var_list:
            self.data[f'{var}_flag'] += cloud_flag # -> flag = 8
        return
    
    # def add_flag_above_cloud_base(self, var_list = ['backscatter_coef', 'backscatter_coef_depol', 'aerosol_depolarization_ratio']):
    #     """
    #     Add cloud flag to the variables in var_list
    #     The flag is computed as follows:
    #     - flag_cloud: 64 if the cloud mask is > 0
    #     """
    #     if not ('above_cloud_base' in self.data.keys()):
    #         logger.warning('No cloud top data available, skipping cloud flag')
    #         return
    #     cloud_flag = xr.where(self.data['above_cloud_base'] > 0, 64, 0)
    #     for var in var_list:
    #         self.data[f'{var}_flag'] += cloud_flag # -> flag = 64
    #     return
    

    def set_invalid_to_nan(self):
        """
        Set the variables to NaN if the flag is > 0
        """
        for var in self.data.variables.keys():
            if not (f'{var}_flag' in self.data.variables.keys()):
                continue
            # logger.info(f'Setting invalid data to NaN for variable {var}')
            self.data[var] = self.data[var].where(self.data[var+'_flag']==0, np.nan)

    def combine_ray_mie(self): # TO DO complete / refine this when both Ray and Mie are available
        """
        Combine the ray and mie variables into a single variable
        The ray variables are averaged with the mie variables, and the flag is set to the maximum of the two
        """        
        for var in self.data.variables.keys():
            if not ('ray' in var or 'mie' in var):
                continue
            if ('flag' in var or 'err' in var):
                continue
            if f'{var}_flag' in self.data.keys():
                flag_var_exists = True
            else:
                flag_var_exists = False
            
            if 'ray' in var:
                mie_var = var.replace('ray', 'mie')
                combined_var = var.replace('_ray', '')
                combined_flag_var = combined_var + '_flag'
                if mie_var in self.data.keys(): # both ray and mie exist -> average
                    combined_data = (self.data[var].values + self.data[mie_var].values) / 2
                    if flag_var_exists:
                        combined_flag = xr.ufuncs.maximum(self.data[var+'_flag'], self.data[mie_var+'_flag']).values
                else: # only ray exists -> use ray only
                    combined_data = self.data[var].values
                    if flag_var_exists:
                        combined_flag = self.data[var+'_flag'].values
                new_dims = tuple(d.replace('_ray', '') for d in self.data[var].dims)
            elif 'mie' in var:
                ray_var = var.replace('mie', 'ray')
                if ray_var in self.data.keys():
                    continue # skip if ray variable exists, as it would have been combined with mie in the loop above
                # otherwise, only mie exists -> use mie only
                combined_var = var.replace('_mie', '')
                combined_flag_var = combined_var + '_flag'
                combined_data = self.data[var].values
                if flag_var_exists:
                    combined_flag = self.data[var+'_flag'].values
                new_dims = tuple(d.replace('_mie', '') for d in self.data[var].dims)
            
            logger.info(f'Combining {var} and {combined_var} into {combined_var}')
            self.data[combined_var] = (new_dims, combined_data)
            if flag_var_exists:
                self.data[combined_flag_var] = (new_dims, combined_flag)

    def combine_int_broad(self):
        """
        Combine the integrated and broadened variables into a single variable
        The integrated variables are averaged with the broadened variables, and the flag is set to the maximum of the two
        """
        for var in ['temperature_int', 'temperature_broad']:
            if f'{var}_flag' in self.data.keys():
                flag_var_exists = True
            else:
                flag_var_exists = False

            if 'int' in var:
                broad_var = var.replace('int', 'broad')
                combined_var = var.replace('_int', '')
                combined_flag_var = combined_var + '_flag'
                if broad_var in self.data.keys():
                    combined_data = (self.data[var].values + self.data[broad_var].values) / 2
                    if flag_var_exists:
                        combined_flag = xr.ufuncs.maximum(self.data[var+'_flag'], self.data[broad_var+'_flag']).values
                else: # broad_var not in data -> use int var only
                    combined_data = self.data[var].values
                    if flag_var_exists:
                        combined_flag = self.data[var+'_flag'].values    
            elif 'broad' in var:
                int_var = var.replace('broad', 'int')
                if int_var in self.data.keys():
                    continue
                combined_var = var.replace('_broad', '')
                combined_data = self.data[var].values
                if flag_var_exists:
                    combined_flag_var = combined_var + '_flag'
                    combined_flag = self.data[var+'_flag'].values
            new_dims = tuple(d.replace('altitude_mie', 'altitude') for d in self.data[var].dims)
            new_dims = tuple(d.replace('altitude_ray', 'altitude') for d in new_dims)

            logger.info(f'Combining INT/BROAD {var} and {combined_var} into {combined_var}')
            self.data[combined_var] = (new_dims, combined_data)
            if flag_var_exists:
                self.data[combined_flag_var] = (new_dims, combined_flag)

    def subsel_stripped_profile(self, los=0, i_to_subsel=[-1]):
        """
        Subset the data to keep only a profile in one field of view and the altitude range + variable list specified in the qc config
        Used to create L2B
        """
        self.data 
        self.data = self.data.sel(line_of_sight=los)
        self.data = self.data.sel(altitude_mie=slice(0,self.qc_conf['MAX_ALTITUDE']))
        self.data = self.data.sel(altitude=slice(0,self.qc_conf['MAX_ALTITUDE']))   
        # if inds_to_subsel is not None:
        #     self.data = self.data.isel(time=inds_to_subsel)     
        self.data = self.data.isel(time=i_to_subsel) # TO DO or -1 ? or mean ?
        # mean_time = self.data['time'].mean()
        # self.data = self.data.mean(dim='time', keep_attrs=True).expand_dims(time=[mean_time])
        # self.data = self.data[self.qc_conf['VARS_TO_KEEP']] # -> this crashes if missing variables
        
        # Check which variables from VARS_TO_KEEP actually exist in the dataset
        vars_to_keep = self.qc_conf['VARS_TO_KEEP']
        existing_vars = []
        missing_vars = []
        
        for var in vars_to_keep:
            if var in self.data.data_vars or var in self.data.coords:
                existing_vars.append(var)
            else:
                missing_vars.append(var)
        # Log warnings for missing variables
        if missing_vars:
            logger.warning(f"Variables specified in VARS_TO_KEEP but not found in dataset: {missing_vars}")
        
        # Keep only the variables that exist
        if existing_vars:
            self.data = self.data[existing_vars]
        else:
            logger.error("None of the variables in VARS_TO_KEEP exist in the dataset!")
            raise ValueError("No valid variables found in VARS_TO_KEEP")


    def set_var_attrs_from_conf(self):
        """
        Set the attributes of the variables in the dataset from the config file
        """
        for var in self.conf['variables'].keys():
            var_attrs = {}
            for key in self.conf['variables'][var].keys():
                if (key=='type') | (key=='_FillValue') | (key=='dim'):
                    continue
                else:
                    var_attrs[key] = self.conf['variables'][var][key]
            self.data[var].attrs.update(var_attrs)

    def set_global_attrs_from_conf(self):
        """
        Set the global attributes of the dataset from the config file
        """
        global_attrs = self.conf['attributes']
        self.data.attrs.update(global_attrs)

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
        print(f'Loading hdf5 file {self.data_file}')
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
            if var in ['station_latitude', 'station_longitude', 'station_altitude']:
                if var in self.conf['attributes'].keys():
                    self.data[var] = (specs['dim'], self.conf['attributes'][var])
                    logger.info(f'Setting {var} from attributes')
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

            if var in ['u_mie', 'u_ray', 'u', 'v_mie', 'v_ray', 'v', 'w_mie', 'w_ray', 'w']:
                self.data[var] = -self.data[var]
                logger.info(f'Inverting sign of {var}')








if __name__=='__main__':
    import os
    cwd = os.getcwd()

    hdf5file = '/tmp/BankExport_20250522_1638.h5' #'/data/euliaa-test/TESTS/BankExport.h5'
    config = os.path.join(cwd,'config/config_nc.yaml')
    config_qc = os.path.join(cwd,'config/config_qc.yaml')
    meas = H5Reader(config,hdf5file, conf_qc_file = config_qc)
    meas.read_hdf5_file()
    meas.load_attrs()
    meas.load_data()
