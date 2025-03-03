import xarray as xr
import numpy as np
import matplotlib.pyplot as plt
from utils import flag_var

# MAX_ALTITUDE = 60e3
W_ABS_THRES = 40.96 # m/s
W_ERR_THRES = 1 # m/s
FLAG_BSC_FROM_W = True
VARS_TO_KEEP = ['backscatter_coef',
                'station_latitude', 'station_longitude', 'station_altitude',
                'vertical_resolution', 'vertical_integration', 'time_integration', 'time_resolution']
WAVELENGTH = 386 # nm


input_file = '/home/bia/euliaa_postproc/data/TestNC2.nc'
output_file = '/home/bia/euliaa_postproc/data/L2Test_NC_for_Aprofiles.nc' # File name must start with L2

ds = xr.open_dataset(input_file)
# ds = ds.sel(altitude_mie=slice(0,MAX_ALTITUDE))
ds_z = ds.sel(field_of_view='zenith')

# to do flag for reserved data?
w_mie_flag = flag_var(ds_z, 'w_mie', 'w_mie_err', var_min_thres=-W_ABS_THRES, var_max_thres=W_ABS_THRES, var_err_thres=W_ERR_THRES)
ds_z['backscatter_coef'] = ds_z['backscatter_coef'].where(w_mie_flag<1, np.nan)

ds_z_subsel = ds_z[VARS_TO_KEEP]

ds_z_subsel = ds_z_subsel.rename({'backscatter_coef':'attenuated_backscatter_0', 'altitude_mie':'altitude'})
ds_z_subsel['attenuated_backscatter_0']['long_name'] = 'Attenuated backscatter coefficient at wavelength 0'

ds_z_subsel['l0_wavelength'] = ((),WAVELENGTH)
ds_z_subsel['latitude'] = (('time',),np.zeros((len(ds_z_subsel.time)))+ds_z_subsel.station_latitude.item())
ds_z_subsel['longitude'] = (('time',),np.zeros((len(ds_z_subsel.time)))+ds_z_subsel.station_longitude.item())
ds_z_subsel.to_netcdf(output_file)
