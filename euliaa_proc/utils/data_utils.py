import numpy as np
import xarray as xr
import warnings


def check_var_in_ds(ds, var):
    if type(var)==list:
        return np.all([v in ds.keys() for v in var])
    else:
        return (var in ds.keys())


def compute_lat_lon(lat_station = 0, lon_station = 0, altitude = np.zeros(1), theta_slant_deg = 30, azimuth_offset=0):
    lat_coef = 110.574 # 1 deg = 110.574 km
    lon_coef = 111.320 # 1 deg = 111.320 * cos(lat) km
    theta_slant_rad = theta_slant_deg*np.pi/180
    
    longitude_arr_3los = ((altitude.dims[0], 'line_of_sight'), np.stack((lon_station + 0*altitude,
                                                        lon_station + altitude*np.tan(theta_slant_rad)*np.sin(azimuth_offset*np.pi/180+np.pi/2)*1e-3/(lon_coef*np.cos(lat_station*np.pi/180)), # "eastward" 
                                                        lon_station + altitude*np.tan(theta_slant_rad)*np.sin(azimuth_offset*np.pi/180)*1e-3/(lon_coef*np.cos(lat_station*np.pi/180)) # "northward"
                                                        ), axis = -1))

    latitude_arr_3los = ((altitude.dims[0], 'line_of_sight'), np.stack((lat_station + 0*altitude,
                                                       lat_station + altitude*np.tan(theta_slant_rad)*np.cos(azimuth_offset*np.pi/180+np.pi/2)*1e-3/lat_coef, # "eastward"
                                                       lat_station + altitude*np.tan(theta_slant_rad)*np.cos(azimuth_offset*np.pi/180)*1e-3/lat_coef # "northward"
                                                       ),  axis=-1))

    
    return (latitude_arr_3los, longitude_arr_3los)


def flag_var(dsz,var_key, err_key=None, snr_key=None, var_min_thres = -np.inf, var_max_thres = np.inf, var_err_thres = np.inf, snr_thres = 1., snr_los='all'):
    da_flag = xr.zeros_like(dsz[var_key])
    if (var_min_thres > -np.inf) or (var_max_thres < np.inf): # Invalid data flag -> 1
        data_invalid = (dsz[var_key]<var_min_thres ) | (dsz[var_key]>var_max_thres)# | (xr.ufuncs.isnan(dsz[var_key]))
        da_flag = da_flag.where(~data_invalid,1)
    if snr_key: # Low SNR flag -> 2
        # if not (snr_los):
        #     da_flag = da_flag*0.
        # else:
        da_flag_snr = xr.zeros_like(dsz[var_key])
        if snr_los is not None:
            if snr_los == 'all':
                snr = dsz[snr_key]
            elif snr_los in ['zenith', 'eastward', 'northward']:
                los_to_index = {'zenith':0, 'eastward':1, 'northward':2}
                snr = dsz[snr_key].sel(line_of_sight=los_to_index[snr_los])
            elif snr_los in [0, 1, 2]:
                snr = dsz[snr_key].sel(line_of_sight=snr_los)
            else:
                raise NameError(f'snr_los must be "zenith", "eastward", "northward" or "all", or None, not {snr_los}')
            data_low_snr = snr < snr_thres
            da_flag_snr = da_flag_snr.where(~data_low_snr,2)
            da_flag = da_flag+da_flag_snr
    if err_key: # High error flag -> 4
        da_flag_err = xr.zeros_like(dsz[var_key])
        data_high_err = dsz[err_key] > var_err_thres
        da_flag_err = da_flag_err.where(~data_high_err,4)
        da_flag = da_flag+da_flag_err

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


def get_los_var(da):
    los_var = None
    if 'line_of_sight' in da.dims:
        los_var = 'line_of_sight'
    elif 'los' in da.dims:
        los_var = 'los'
    else:
        warnings.warn('Did not find field of view dimension ("los" or "line_of_sight"). Assuming no such field.', UserWarning)
    return los_var


def get_noise_vect_from_da(power_in,n_avg=1, calc_stdv = False,perc_npts_min = 0.25,perc_to_rm=0.05):

    alt_var = get_alt_var(power_in)
    los_var = get_los_var(power_in)
    axis_alt = power_in.dims.index(alt_var)
    axis_time = power_in.dims.index('time')
    axis_los = power_in.dims.index(los_var)

    if not axis_los:
        lnoise = np.zeros((len(power_in['time'])))+np.nan
        var = np.zeros((len(power_in['time'])))+np.nan
    else:
        lnoise = np.zeros((len(power_in['time']), len(power_in[los_var])))+np.nan
        var = np.zeros((len(power_in['time']), len(power_in[los_var])))+np.nan

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
        return (('time', los_var),lnoise), (('time', los_var),var)
    else:
        return (('time', los_var),lnoise)



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

def get_noise_from_da(power_in, calc_stdv = False, perc_npts_noise = 0.15, perc_to_rm=0.05):

    alt_var = get_alt_var(power_in)
    los_var = get_los_var(power_in)
    axis_alt = power_in.dims.index(alt_var)
    axis_los = power_in.dims.index(los_var)

    if not axis_los:
        lnoise = np.zeros((len(power_in['time'])))+np.nan
        std = np.zeros((len(power_in['time'])))+np.nan
    else:
        lnoise = np.zeros((len(power_in['time']), len(power_in[los_var])))+np.nan
        std = np.zeros((len(power_in['time']), len(power_in[los_var])))+np.nan

    power = power_in.values*1.

    power[power==0]=np.nan
    power[power<=np.expand_dims(np.nanquantile(power,perc_to_rm,axis=axis_alt),1)]=np.nan
    power[power!=power]=0
    npts_start = np.int64(np.sum(power==0,axis=axis_alt))

    npts_noise = int(len(power_in[alt_var])*perc_npts_noise)

    for i in range(len(power_in[los_var])):
        for j in range(len(power_in['time'])):
            lnoise[j,i] = np.nanmean(power[j,-(npts_start[j,i]+npts_noise):-npts_start[j,i], i])
            std[j,i] = np.nanstd(power[j,-(npts_start[j,i]+npts_noise):-npts_start[j,i], i])

    if calc_stdv:
        return (('time', los_var),lnoise), (('time', los_var),std)
    else:
        return (('time', los_var),lnoise)

def compute_wind_speed(u, v):
    """Compute wind speed from u and v components."""
    return np.sqrt(u**2 + v**2)

def compute_wind_direction(u, v):
    """Compute wind direction from u and v components."""
    return (180+np.arctan2(u, v) * (180 / np.pi))%360
    # Note: This returns the direction (from which the wind blows) in degrees from North (0°)

def compute_hor_width(height, theta=30):
    """Compute horizontal width of the area sampled by the 3 telescopes at a given height."""
    return height*np.tan(theta*np.pi/180)*np.sqrt(2)

def compute_beam_diameter(height, theta=3.25e-5, d_ini=10e-2):
    """Compute the diameter of the beam at a given height.

    Parameters:
    - height: Height at which to compute the beam diameter (in meters).
    - theta: Angle in radians (default is 3.25e-5, which is approximately 0.00186 degrees).
    - d_ini: Initial diameter of the beam at the telescope (default is 10 cm).

    Returns:
    - The diameter of the beam at the specified height.
    """    
    return d_ini + 2 * height * np.tan(theta)


def compute_ldr_and_err(bsc_depol, bsc, bsc_depol_err, bsc_err):
    # Extract variables
    
    # --- Step 1: Compute LDR (ratio)
    ldr = bsc_depol / bsc

    # --- Step 2: Estimate correlation (ρ) between channels
    #    If you have multiple samples (e.g. along time or range), estimate globally or per-bin.
    #    Here: compute overall Pearson correlation coefficient
    mask = np.isfinite(bsc) & np.isfinite(bsc_depol)
    rho = np.corrcoef(bsc_depol[mask], bsc[mask])[0, 1]

    print(f"Estimated correlation (ρ) = {rho:.3f}")

    # --- Step 3: Compute LDR uncertainty including covariance term
    ldr_rel_err = np.sqrt(
        (bsc_depol_err / bsc_depol) ** 2 +
        (bsc_err / bsc) ** 2 -
        2 * rho * (bsc_depol_err / bsc_depol) * (bsc_err / bsc)
    )

    ldr_err = ldr * ldr_rel_err

    # # --- Step 4: Store results back in DataFrame
    # data["ldr"] = ldr
    # data["ldr_err"] = ldr_err


    # Inspect
    # print(data[["ldr", "ldr_err"]].head())
    return ldr, ldr_err


def correct_u_v_for_azimuth(azimuth_deg, u, v, u_err, v_err):
    """
    Correct u0 and v0 wind components based on azimuth angle.
    In the original data, the u0/v0 components correspond to the instrument's frame, which is rotated by the azimuth angle w.r.t. geographical directions.
    Here we rotate the components back to geographical frame (Eastward/Northward).
    Parameters:
    - azimuth_deg: Azimuth angle in degrees (0° = North, 90° = East).
    - u: Wind component in the instrument frame (u0). If the instrument is pointing North, u corresponds to Eastward component.
    - v: Wind component in the instrument frame (v0). If the instrument is pointing North, v corresponds to Northward component.
    - u_err: Uncertainty in u0 component.
    - v_err: Uncertainty in v0 component.
    """
    azimuth_rad = np.deg2rad(azimuth_deg)
    u_geo = u * np.cos(azimuth_rad) + v * np.sin(azimuth_rad)
    v_geo = -u * np.sin(azimuth_rad) + v * np.cos(azimuth_rad)
    u_geo_err = np.sqrt((np.cos(azimuth_rad) * u_err) ** 2 + (np.sin(azimuth_rad) * v_err) ** 2)
    v_geo_err = np.sqrt((np.sin(azimuth_rad) * u_err) ** 2 + (np.cos(azimuth_rad) * v_err) ** 2)
    return u_geo, v_geo, u_geo_err, v_geo_err
