import xarray as xr
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as colors
from scipy import signal
from scipy import special
import aprofiles as apro
from log import logger

def cloud_aprofiles(path, zmin=0, thr_noise = 1.5, thr_clouds = 2, verbose = False, time_avg = 0):
    """
    Function to detect clouds in a profile using the aprofiles library.
    The cloud detection is based on the variance gradient method. (see aprofiles documentation);
    other option in a-profiles is deep embedded clustering, which doesn't seem to work

    Inputs:
        path: path to the file, needs to comply to A-profiles format
        z_min: minimum altitude for cloud detection (in m)
        thr_noise: SNR threshold, see aprofiles documentation
        thr_clouds: threshold for cloud identification, see aprofiles documentation
        verbose: if True, prints the cloud detection process
        time_avg: time average for the cloud detection (minutes)

    Output:
        clouds: xarray.DataArray, array with the cloud detection, 1 if cloud, 0 if not cloud

    """

    profile = apro.reader.ReadProfiles(path).read()
    profile.clouds(method="vg",zmin=zmin, thr_noise=thr_noise,
                   thr_clouds=thr_clouds, verbose=verbose,time_avg=time_avg)
    return profile.data.clouds


def savgol(x,F,K):
    xf = xr.zeros_like(x)*np.nan
    y = xr.zeros_like(x)*np.nan

    # if F%2==0:
    #     F+=1
    xf = signal.savgol_filter(x,F,K,deriv = 0) # smoothed backscatter
    y = signal.savgol_filter(xf,F,K,deriv = 1) # smoothed gradient

    return xf, y


def detect_cloud_edge(bsc, alt, F = 5, K = 3, bsc_thres = 1e-8, vg_thres = 0.3,base_or_top='base', return_height = False):
    """
    Function to detect cloud base and cloud top. Uses vertical gradient on smoothed signal (Savitzky-Golay).

    Inputs:
        K: degree of polynomial for SavGol filter
        F: filter window for SavGol filte. NB in RALMO: int(dz/ds.vertical_resolution), dz = 15 m, but doesn't make sense with EULIAA resolution
    Outputs:
        cloud_edge: xarray.DataArray, array with the cloud detection, 1 if cloud, 0 if not cloud
        cloud_edge_height: xarray.DataArray, array with the cloud detection, height of the cloud base, 0 if not cloud

    """
    x = np.log(bsc)#ds.attenuated_backscatter_0)
    if base_or_top == 'top':
        if x.ndim == 1:
            x = x[::-1]
        else:
            x = x[:,::-1]
    elif base_or_top != 'base':
        raise ValueError('base_or_top must be either "base" or "top"')

    xf, y = savgol(x,F,K)

    cloud_edge = xr.where((y[:,2:]-y[:,1:-1]<0) & (y[:,:-2]-y[:,1:-1]<0) # local maximum in the gradient
                          & (y[:,1:-1]>vg_thres)  # threshold on gradient
                          & (xf[:,:-2]>np.log(bsc_thres)), # threshold on backscatter, to do check indexing
                          1,0)
    if base_or_top == 'top':
        if cloud_edge.ndim == 1:
            cloud_edge = cloud_edge[::-1]
        else:
            cloud_edge = cloud_edge[:,::-1]

    # try:
    cloud_edge_height = alt.values[1:-1]*np.where(cloud_edge,1,np.nan)#s.where()
    # except:
        # cloud_edge_height = alt.values[1:-1][None,:,None]*np.where(cloud_edge,1,np.nan)#s.where()
    if return_height:
        return cloud_edge, cloud_edge_height
    else:
        return cloud_edge



def refine_cloud_detection(bsc, cb, ct, F0 = 5, K0 = 3,bsc_thres = 1e-8, vg_thres = 0.1):
    """
    Function to refine cloud detection. If cloud base is detected but no cloud top, cloud base is removed.
    If several cloud layers are detected, cloud top is detected for each layer.

    """
    icb = np.where(cb)[0]
    if len(icb)==0: # no cloud base, moving on
        return

    for i_icb, ii in enumerate(icb):
        ict = np.where(ct)[0]

        if (((i_icb == len(icb)-1) and (np.any(ict>ii))) | # if last cloud layer and already a cloud top
            ((i_icb < len(icb)-1) and (np.any((ict > ii) & (ict < icb[i_icb+1]))))): # if not last cloud layer, look for cloud top below next cloud base
            continue # Already a cloud top, moving on

        elif (i_icb < len(icb)-1): # if not the last cloud layer, select indices below next cloud base
            x = np.log(bsc[ii:icb[i_icb+1]])
            cti = ct[ii:icb[i_icb+1]]
        else: # otherwise, look for cloud top in all ranges above cloud base
            x = np.log(bsc[ii:])
            cti = ct[ii:]

        # SavGol smoothing of bsc profile + gradient
        F = F0 if len(x)>F0 else len(x)
        K = K0 if len(x)>F0 else len(x)-1
        xf, y = savgol(x[::-1], F, K) # reverse x because we are looking for cloud top

        # Set y to nan where cloud top conditions are not matched
        y[1:-1][xf[2:]<np.log(bsc_thres)] = np.nan # abs threshold on backscatter NB to do check indexing
        y[1:-1][~((y[2:]-y[1:-1]<0) & (y[:-2]-y[1:-1]<0))] = np.nan # sign threshold on gradient

        if np.nanmax(y[1:-1])<vg_thres: # max gradient below threshold, no satisfactory cloud top
            cb[ii] = 0 # no cloud top detected, removing cloud base
            logger.info('no cloud top detected, removing cloud base')

        else: # different dimensions depending on the number of cloud layers
            if len(cti[1:-1])==len(y[1:-1]):
                cti[1:-1] = np.where((y[1:-1]==np.nanmax(y[1:-1])), 1, 0)[::-1]
            else:
                cti[:] = np.where((y[1:-1]==np.nanmax(y[1:-1])), 1, 0)[::-1]


def find_cloud_mask(bsc, cloud_base, cloud_top, return_below_cloud_top = False, return_above_cloud_base = False):
    below_cloud_top = xr.zeros_like(bsc)
    above_cloud_top = xr.zeros_like(bsc)
    below_cloud_base = xr.zeros_like(bsc)
    above_cloud_base = xr.zeros_like(bsc)
    below_cloud_base[:,1:-1] = np.cumsum(cloud_base[:,::-1],axis=1)[:,::-1]
    above_cloud_base[:,1:-1] = np.cumsum(cloud_base,axis=1)#[:,::-1]
    below_cloud_top[:,1:-1] = np.cumsum(cloud_top[:,::-1],axis=1)[:,::-1]
    above_cloud_top[:,1:-1] = np.cumsum(cloud_top,axis=1)
    below_cloud_top[:,0] = below_cloud_top[:,1]
    below_cloud_base[:,0] = below_cloud_base[:,1]
    above_cloud_base[:,-1] = above_cloud_base[:,-2]
    above_cloud_top[:,-1] = above_cloud_top[:,-2]
    n_above_cloud_top = np.cumsum(above_cloud_top,axis=1)
    n_above_cloud_base = np.cumsum(above_cloud_base,axis=1)

    cloud_mask = xr.zeros_like(bsc)
    cloud_mask.data = (((above_cloud_base>0) & (below_cloud_top>0)) &
                  ~((above_cloud_top>0) & (below_cloud_base>0) & (n_above_cloud_base>n_above_cloud_top)))

    if return_below_cloud_top and not (return_above_cloud_base):
        return cloud_mask, below_cloud_top
    elif return_above_cloud_base and not(return_below_cloud_top):
        return cloud_mask, above_cloud_base
    elif return_below_cloud_top and return_above_cloud_base:
        return cloud_mask, below_cloud_top, above_cloud_base
    else:
        return cloud_mask


def plot_cloud(ds,ymax=30000,name_bsc_var = 'attenuated_backscatter_0', savefig=None):

    fig,ax = plt.subplots(figsize = (15,4))
    im=ds[name_bsc_var].plot(x='time',vmin=1e-9,vmax=1e-5,norm=colors.LogNorm(),cmap='plasma')
    cloud_mask_for_plot=ds.cloud_mask.where(ds.cloud_mask,np.nan)
    cloud_mask_for_plot.T.plot(alpha=.7,vmin=0, vmax=1, cmap='Greys_r',ylim=(0,ymax),add_colorbar=False)
    ax.plot([],[],lw=0,marker='s', ms=10, color='white', alpha=.7, label='clouds or aerosols')
    ax.set_ylim(0,ymax)
    ax.set_facecolor('dimgray')
    ax.legend(loc='upper right')

    if ('cloud_base' in ds) and ('cloud_top' in ds):
        cloud_base_height = ds.altitude.values*np.where(ds.cloud_base,1,np.nan)
        cloud_top_height = ds.altitude.values*np.where(ds.cloud_top,1,np.nan)
        time_array = np.repeat(ds.time.values.reshape(-1,1),len(ds.altitude),axis=1)
        ax.scatter(time_array, cloud_base_height,s=10,color='k',marker='.')
        ax.scatter(time_array, cloud_top_height,s=10,color='cyan',marker='.')

    if savefig:
        fig.savefig(savefig)

def in_house_cloud_detection(ds,name_altitude_var = 'altitude_mie',vg_thres_base = 0.45,vg_thres_top = 0.6, remove_below=5, return_height=True):
    cloud_base = detect_cloud_edge(ds, ds[name_altitude_var], return_height = False, vg_thres=vg_thres_base)
    cloud_top = detect_cloud_edge(ds, ds[name_altitude_var], return_height = False, base_or_top='top',vg_thres=vg_thres_top)
    # cloud_base = detect_cloud_edge(ds[name_bsc_var], ds[name_altitude_var], return_height = False, vg_thres=vg_thres_base)
    # cloud_top = detect_cloud_edge(ds[name_bsc_var], ds[name_altitude_var], return_height = False, base_or_top='top',vg_thres=vg_thres_top)

    for i in range(len(ds.time)):
        cb = cloud_base[i]
        ct = cloud_top[i]
        # bsc = ds[name_bsc_var].isel(time=i)
        bsc = ds.isel(time=i)
        refine_cloud_detection(bsc,cb,ct)

    cloud_base[:,:remove_below] = 0 # the lowest gates are not valid
    cloud_top[:,:remove_below] = 0

    cloud_ds = xr.Dataset({})
    cloud_ds['cloud_mask'], cloud_ds['below_cloud_top'], cloud_ds['above_cloud_base'] = find_cloud_mask(ds,cloud_base,cloud_top,
                                        return_below_cloud_top=True, return_above_cloud_base=True)
    # cloud_ds['cloud_mask'], cloud_ds['below_cloud_top'], cloud_ds['above_cloud_base'] = find_cloud_mask(ds[name_bsc_var],cloud_base,cloud_top,
    #                                     return_below_cloud_top=True, return_above_cloud_base=True)
    cloud_ds['cloud_base'] = xr.zeros_like(cloud_ds.cloud_mask)
    cloud_ds['cloud_top'] = xr.zeros_like(cloud_ds.cloud_mask)
    cloud_ds['cloud_base'][:,1:-1] = cloud_base
    cloud_ds['cloud_top'][:,1:-1] = cloud_top
    if return_height:
        cloud_ds['cloud_base_height'] = ds[name_altitude_var]*xr.where(cloud_ds['cloud_base'],1,np.nan)
        cloud_ds['cloud_top_height'] = ds[name_altitude_var]*xr.where(cloud_ds['cloud_top'],1,np.nan)

    return cloud_ds


if __name__=='__main__':
    path_l2 = '/home/bia/euliaa_postproc/data/L2Test_NC_for_Aprofiles.nc'
    REMOVE_BELOW = 6
    PLOT = True
    savefig = '/home/bia/euliaa_postproc/figures/cloud_detection_inhouse.png'
    # savefig = '/home/bia/euliaa_postproc/figures/cloud_detection_aprofiles.png'
    SAVE_NC = True
    VG_THRES_BASE = 0.25
    VG_THRES_TOP = 0.5
    run_in_house_cloud_detection = True
    run_aprofiles_cloud_detection = False
    name_bsc_var = 'attenuated_backscatter_0'

    ds = xr.open_dataset(path_l2)
    if run_in_house_cloud_detection:
        ds = xr.merge([ds,in_house_cloud_detection(ds,name_bsc_var=name_bsc_var,name_altitude_var='altitude',vg_thres_base=VG_THRES_BASE,vg_thres_top=VG_THRES_TOP,remove_below=REMOVE_BELOW)])

        if False:
            cloud_base = detect_cloud_edge(ds[name_bsc_var], ds.altitude, return_height = False, vg_thres=.25)
            cloud_top = detect_cloud_edge(ds[name_bsc_var], ds.altitude, return_height = False, base_or_top='top',vg_thres=.5)

            for i in range(len(ds.time)):
                cb = cloud_base[i]
                ct = cloud_top[i]
                bsc = ds[name_bsc_var].isel(time=i)
                refine_cloud_detection(bsc,cb,ct)

            cloud_base[:,:REMOVE_BELOW] = 0 # the lowest gates are not valid
            cloud_top[:,:REMOVE_BELOW] = 0

            ds['cloud_mask'], ds['below_cloud_top'], ds['above_cloud_base'] = find_cloud_mask(ds[name_bsc_var],cloud_base,cloud_top,
                                                return_below_cloud_top=True, return_above_cloud_base=True)
            ds['cloud_base'] = xr.zeros_like(ds.cloud_mask)
            ds['cloud_top'] = xr.zeros_like(ds.cloud_mask)
            ds['cloud_base'][:,1:-1] = cloud_base
            ds['cloud_top'][:,1:-1] = cloud_top

    elif run_aprofiles_cloud_detection:
        ds['cloud_mask'] = cloud_aprofiles(path_l2)

    if PLOT:
        plot_cloud(ds,savefig=savefig)

    if SAVE_NC:
        if in_house_cloud_detection:
            suffix = '_cloud_in_house.nc'
        elif aprofiles_cloud_detection:
            suffix = '_cloud_aprofiles.nc'
        ds.to_netcdf(path_l2.replace('.nc',suffix))
