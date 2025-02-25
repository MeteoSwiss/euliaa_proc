import yaml
import numpy as np
import xarray as xr


def get_conf(file):
    """get config dictionary from yaml files"""
    with open(file) as f:
        conf = yaml.load(f, Loader=yaml.FullLoader)
    return conf

def correct_dim_scalar_fields(conf):
    """scalar fields are assigned dimension=()"""
    for var in conf.keys():
        if conf[var]['dim']=='':
            conf[var]['dim']=()

def check_var_in_ds(ds, var):
    if type(var)==list:
        return np.all([v in ds.keys() for v in var])
    else:
        return (var in ds.keys())


def compute_lat_lon(lat_station = 0, lon_station = 0, altitude = np.zeros(1), theta_slant_deg = 30):
    lat_coef = 110.574 # 1 deg = 110.574 km
    lon_coef = 111.320 # 1 deg = 111.320 * cos(lat) km
    theta_slant_rad = theta_slant_deg*np.pi/180

    latitude_arr_3fov = ((altitude.dims[0], 'field_of_view'), np.stack((lat_station + 0*altitude,
                                                       lat_station + 0*altitude,
                                                       lat_station + lat_coef*np.tan(theta_slant_rad)*altitude
                                                       ),
                                                       axis=-1))

    longitude_arr_3fov = ((altitude.dims[0], 'field_of_view'), np.stack((lon_station + 0*altitude,
                                                        lon_station + lon_coef*np.cos(lat_station*np.pi/180)*np.tan(theta_slant_rad)*altitude,
                                                        lon_station + 0*altitude
                                                        ), axis = -1))

    return (latitude_arr_3fov, longitude_arr_3fov)


def flag_var(dsz,var_key, var_err_key, var_min_thres = -999., var_max_thres = 999., var_err_thres = 999.):
    da_flag = xr.zeros_like(dsz[var_key])
    data_suspect = dsz[var_err_key] > var_err_thres
    data_invalid = (dsz[var_key]<var_min_thres ) | (dsz[var_key]>var_max_thres) | (xr.ufuncs.isnan(dsz[var_key]))
    da_flag = da_flag.where(~data_suspect,1)
    da_flag = da_flag.where(~data_invalid,2)
    return da_flag
