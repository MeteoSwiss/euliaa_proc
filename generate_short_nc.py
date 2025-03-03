import xarray as xr
import numpy as np
import matplotlib.pyplot as plt
from utils import flag_var

MAX_ALTITUDE = 60e3
W_ABS_THRES = 40.96 # m/s
W_ERR_THRES = 1 # m/s
U_V_ABS_THRES = 409.6 # m/s
U_V_ERR_THRES = 1 # m/s
TEMP_ERR_THRES = 5 # K
TEMP_MIN_THRES = 0 # K
TEMP_MAX_THRES = 409.5 # K
INVALID_TO_NAN = True

VARS_TO_KEEP = ['temperature_int', 'w_mie', 'v_mie', 'u_mie',
                'temperature_int_flag', 'w_mie_flag', 'v_mie_flag', 'u_mie_flag', 'u_v_flag',
                'station_latitude', 'station_longitude', 'station_altitude',
                'vertical_resolution', 'vertical_integration', 'time_integration', 'time_resolution']
CORRECTION = 28.98 # temporary correction to do remove when fixed by IAP



input_file = '/home/bia/euliaa_postproc/data/TestNC2.nc'
output_file = '/home/bia/euliaa_postproc/data/Test_profile_NC.nc'
ds = xr.open_dataset(input_file)
ds = ds.sel(altitude_mie=slice(0,MAX_ALTITUDE))
ds.w_mie.values = ds.w_mie.values-CORRECTION # first file from iap has a velocity bias
ds_z = ds.sel(field_of_view='zenith')

# to do flag for reserved data?
ds_z['w_mie_flag'] = flag_var(ds_z, 'w_mie', 'w_mie_err', var_min_thres=-W_ABS_THRES, var_max_thres=W_ABS_THRES, var_err_thres=W_ERR_THRES)
ds_z['u_mie_flag'] = flag_var(ds_z, 'u_mie', 'u_mie_err', var_min_thres=-U_V_ABS_THRES, var_max_thres=U_V_ABS_THRES, var_err_thres=U_V_ERR_THRES)
ds_z['v_mie_flag'] = flag_var(ds_z, 'v_mie', 'v_mie_err', var_min_thres=-U_V_ABS_THRES, var_max_thres=U_V_ABS_THRES, var_err_thres=U_V_ERR_THRES)
ds_z['temperature_int_flag'] = flag_var(ds_z, 'temperature_int', 'temperature_int_err', var_min_thres=TEMP_MIN_THRES, var_max_thres=TEMP_MAX_THRES, var_err_thres=TEMP_ERR_THRES)
ds_z['u_v_flag']= xr.ufuncs.maximum(ds_z.u_mie_flag,ds_z.v_mie_flag)

if INVALID_TO_NAN:
    for var in ['u_mie', 'v_mie', 'w_mie', 'temperature_int']:
        ds_z[var] = ds_z[var].where(ds_z[var+'_flag']<1, np.nan)

ds_z_subsel = ds_z[VARS_TO_KEEP]
ds_z_subsel_t0 = ds_z_subsel.isel(time=0)

ds_z_subsel_t0.to_netcdf(output_file)
