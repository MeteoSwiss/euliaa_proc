import yaml
import numpy as np
import xarray as xr
import warnings

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
                                                       lat_station + altitude*np.tan(theta_slant_rad)*1e-3/lat_coef
                                                       ),
                                                       axis=-1))

    longitude_arr_3fov = ((altitude.dims[0], 'field_of_view'), np.stack((lon_station + 0*altitude,
                                                        lon_station + altitude*np.tan(theta_slant_rad)*1e-3/(lon_coef*np.cos(lat_station*np.pi/180)),
                                                        lon_station + 0*altitude
                                                        ), axis = -1))

    return (latitude_arr_3fov, longitude_arr_3fov)


def flag_var(dsz,var_key, err_key=None, snr_key=None, var_min_thres = -np.inf, var_max_thres = np.inf, var_err_thres = np.inf, snr_thres = 1., snr_fov='all'):
    da_flag = xr.zeros_like(dsz[var_key])
    if (var_min_thres > -np.inf) or (var_max_thres < np.inf): # Invalid data flag -> 1
        data_invalid = (dsz[var_key]<var_min_thres ) | (dsz[var_key]>var_max_thres)# | (xr.ufuncs.isnan(dsz[var_key]))
        da_flag = da_flag.where(~data_invalid,1)
    if snr_key: # Low SNR flag -> 2
        if not (snr_fov):
            da_flag = da_flag*0.
        else:
            if snr_fov == 'all':
                snr = dsz[snr_key]
            elif snr_fov in ['zenith', 'eastward', 'northward']:
                fov_to_index = {'zenith':0, 'eastward':1, 'northward':2}
                snr = dsz[snr_key].sel(field_of_view=fov_to_index[snr_fov])
            else:
                raise NameError(f'snr_fov must be "zenith", "eastward", "northward" or "all", or None, not {snr_fov}')
            data_low_snr = snr < snr_thres
            da_flag = da_flag.where(~data_low_snr,2)
    if err_key: # High error flag -> 4
        data_high_err = dsz[err_key] > var_err_thres
        da_flag = da_flag.where(~data_high_err,4)

    return da_flag



def get_alt_var(da):
    alt_var = None
    if 'altitude' in da.dims:
        alt_var = 'altitude'
    elif 'altitude_mie' in da.dims:
        alt_var = 'altitude_mie'
    elif 'altitude_ray' in da.dims:
        alt_var = 'altitude_ray'
    else:
        raise NameError('Did not find altitude dimension. Must be "altitude", "altitude_mie" or "altitude_ray"')
    return alt_var


def get_fov_var(da):
    fov_var = None
    if 'field_of_view' in da.dims:
        fov_var = 'field_of_view'
    elif 'fov' in da.dims:
        fov_var = 'fov'
    else:
        warnings.warn('Did not find field of view dimension ("fov" or "field_of_view"). Assuming no such field.', UserWarning)
    return fov_var


def get_noise_vect_from_da(power_in,n_avg=1, calc_stdv = False,perc_npts_min = 0.25,perc_to_rm=0.05):

    alt_var = get_alt_var(power_in)
    fov_var = get_fov_var(power_in)
    axis_alt = power_in.dims.index(alt_var)
    axis_time = power_in.dims.index('time')
    axis_fov = power_in.dims.index(fov_var)

    if not axis_fov:
        lnoise = np.zeros((len(power_in['time'])))+np.nan
        var = np.zeros((len(power_in['time'])))+np.nan
    else:
        lnoise = np.zeros((len(power_in['time']), len(power_in[fov_var])))+np.nan
        var = np.zeros((len(power_in['time']), len(power_in[fov_var])))+np.nan

    power = power_in.values*1.

    power[power==0]=np.nan
    power[power<=np.expand_dims(np.nanquantile(power,perc_to_rm,axis=axis_alt),1)]=np.nan
    power[power!=power]=0
    sorted_power = np.sort(power,axis=axis_alt)
    npts_min = np.int64(np.zeros_like(lnoise)+int(len(power_in[alt_var])*perc_npts_min)+np.sum(power==0,axis=axis_alt))

    nsamples = np.nancumsum(sorted_power>0,axis=axis_alt)+1

    # Compute partial averages and variances
    mean_rolling = np.nancumsum(sorted_power, axis=axis_alt)/nsamples
    mean2_rolling = np.nancumsum(sorted_power**2, axis=axis_alt)/nsamples
    var_rolling = mean2_rolling - mean_rolling**2
    condi = var_rolling * n_avg <= mean_rolling**2.


    # Get occurence of first non white noise gate
    first_notwn = np.nanargmin(condi, axis=axis_alt) - 1
    first_notwn[~np.any(condi == 0)] = 0

    condi_npts = first_notwn < npts_min
    for i in range(3): # to do -> this could probably be vectorized
        lnoise[:,i] = mean_rolling[np.arange(len(power_in['time'])),first_notwn[:,i],i]
        lnoise[condi_npts[:,i],i] = mean_rolling[condi_npts[:,i],npts_min[condi_npts[:,i],i]-1,i]
        if calc_stdv:
            var[:,i] = var_rolling[np.arange(len(power_in['time'])),first_notwn[:,i],i]
            var[condi_npts[:,i],i] = var_rolling[condi_npts[:,i],npts_min[condi_npts[:,i],i]-1,i]

    if calc_stdv:
        return (('time', fov_var),lnoise), (('time', fov_var),var)
    else:
        return (('time', fov_var),lnoise)



def get_noise_vect(power_in,n_avg=1, calc_stdv = False, perc = 0.15):
    power = power_in.copy()
    power[power!=power]=0
    sorted_power = np.sort(power,axis=1)
    npts_min = int(len(power[0])*perc)
    lnoise = np.zeros((len(power)))+np.nan
    nsamples = np.cumsum(sorted_power>0,axis=1)+1

    # Compute partial averages and variances
    mean_rolling = np.cumsum(sorted_power, axis=1)/nsamples
    mean2_rolling = np.cumsum(sorted_power**2, axis=1)/nsamples
    var_rolling = mean2_rolling - mean_rolling**2
    condi = var_rolling * n_avg <= mean_rolling**2.


    # Get occurence of first non white noise gate
    first_notwn = np.argmin(condi, axis=1) - 1
    first_notwn[~np.any(condi == 0)] = 0

    condi_npts = first_notwn < npts_min


    lnoise = mean_rolling[np.arange(len(first_notwn)),first_notwn]
    lnoise[condi_npts] = mean_rolling[condi_npts,npts_min-1]

    return lnoise

def get_noise(power_in,n_avg=1, calc_stdv = False, perc = 0.1):
    power = power_in*1.
    power[power==0]=np.nan
    power = power[power==power]
    sorted_spectrum = np.sort(power)
    npts_min = int(len(power)*perc)

    nnoise = len(power)  # default to all points in the spectrum as noise
    for npts in range(1, len(sorted_spectrum)+1):
        partial = sorted_spectrum[:npts]
        mean = np.nanmean(partial)
        var = np.nanvar(partial)
        if var * n_avg <= mean**2.:
            nnoise = npts
        else:
            # partial spectrum no longer has characteristics of white noise
            break
    if nnoise < npts_min:
        nnoise = npts_min
    noise_spectrum = sorted_spectrum[0:nnoise]
    lnoise = np.nanmean(noise_spectrum)
    stdv = np.nanstd(noise_spectrum)

    if calc_stdv:
        return lnoise, stdv
    else:
        return lnoise
