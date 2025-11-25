import xarray as xr
import matplotlib.pyplot as plt
import matplotlib.colors as colors
import matplotlib.dates as mdates
import re
import numpy as np
import os 
from euliaa_proc.utils.data_utils import compute_wind_speed
import pandas as pd

# Example use with L2A files on s3 bucket: python3 quicklooks.py --l2a_file_list $(s3cmd ls s3://euliaa-l2/TESTS/L2A_20250723* | awk '{print $4}')

def plot_quicklooks(fname, fig_dir, fig_title, fig_prefix='', ylim=50000):
    
    if not os.path.exists(fig_dir) and not fig_dir.startswith('s3://'):
    # Create the directory if it does not exist
        os.makedirs(fig_dir)
    fig_name = os.path.join(fig_dir, fig_prefix+os.path.basename(fname).replace('.nc', '.png'))

    ds = xr.load_dataset(fname, engine='h5netcdf')
    fig,axs = plt.subplots(6,figsize=(12,17))
    for var in ['backscatter_coef','w_mie','u_mie','v_mie','temperature_int']:
        ds[var] = ds[var].where(ds[var+'_flag']==0, np.nan)
    
    wind_speed = compute_wind_speed(ds.u_mie, ds.v_mie)

    ds.backscatter_coef.sel(line_of_sight=0).plot(x='time',norm=colors.LogNorm(vmin=1e-9,vmax=1e-5),ax=axs[0], cbar_kwargs={'label': 'Backscatter coefficient [m-1 sr-1]', 'extend':'both'})
    im=axs[1].barbs(ds.time.values[:], ds.altitude_mie.values[::3], ds.u_mie.values[:,::3].T, ds.v_mie.values[:,::3].T,wind_speed.values[:,::3].T,
          length=3.5, pivot='middle', cmap='turbo', linewidth=.5)
    axs[1].set_ylabel('Altitude above mean sea level, for Mie peak measurements [m]')
    plt.colorbar(im, ax=axs[1], label='Wind speed [m s-1]')
    ds.w_mie.plot(x='time',vmin=-6,vmax=6,ax=axs[2],cmap='seismic')
    ds.u_mie.plot(x='time',ax=axs[3])
    ds.v_mie.plot(x='time',ax=axs[4])
    (ds.temperature_int.sel(line_of_sight=0)-273.15).plot(x='time',ax=axs[5],cbar_kwargs={'label': 'Temperature from\n Rayleigh integration [deg C]'},vmin=-60,vmax=30,cmap='turbo')
    for ax in axs:
        ax.set_ylim(0, ylim)  # Updated to use ylim argument
        ax.set_title('')
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
        ax.set_xlabel('Time [UTC]')

    axs[0].set_title(fig_title)
    fig.tight_layout()

    if fig_name.startswith('s3://'):
        # Save the figure to an in-memory buffer
        import boto3
        from io import BytesIO

        buffer = BytesIO()
        fig.savefig(buffer, dpi=300, bbox_inches='tight', facecolor='w', format='png')
        buffer.seek(0)

        # Parse the S3 bucket and key from the fig_name
        s3 = boto3.client('s3')
        bucket_name = fig_name.split('/')[2]
        key = '/'.join(fig_name.split('/')[3:])

        # Upload the figure to the S3 bucket
        s3.upload_fileobj(buffer, bucket_name, key)
        buffer.close()

    else:
        # Save the figure locally
        fig.savefig(fig_name,dpi=300,bbox_inches='tight',facecolor='w')



def plot_daily_quicklooks(fname_list, fig_dir, fig_title, fig_prefix='L2A_', ylim=50000, wind_str='', bsc_str='', T_str='', mask_flag=1):
    
    if not os.path.exists(fig_dir) and not fig_dir.startswith('s3://'):
    # Create the directory if it does not exist
        os.makedirs(fig_dir)
    ds_0 = xr.load_dataset(fname_list[0], engine='h5netcdf')
    var_list = ['backscatter_coef', 'w_mie', 'u_mie', 'v_mie', 'temperature_int', 'aerosol_depolarization_ratio']
    var_list = [var for var in var_list if var in ds_0.data_vars]
    
    n_plots = len(var_list)+('u_mie' in var_list)
    fig,axs = plt.subplots(n_plots,figsize=(12,3*n_plots))
    for fname in fname_list:
        ds = xr.load_dataset(fname, engine='h5netcdf')
        
        if mask_flag:
            mask = xr.Dataset({var: xr.where(ds[var+'_flag'] == 0, np.nan, 1) for var in var_list})
        else:
            mask = xr.Dataset({var: xr.zeros_like(ds[var]) for var in var_list})*np.nan
        
        iplot=0 # this inelegant approach keeps the correct subplot index when some variables are missing
        if ((len(bsc_str)>0 and (bsc_str in fname)) or (len(bsc_str)==0)) and ('backscatter_coef' in var_list):
            im0=axs[iplot].pcolormesh(ds.time.values, ds.altitude_mie.values, ds.backscatter_coef.sel(line_of_sight=0).T,norm=colors.LogNorm(vmin=1e-9,vmax=1e-5),shading='nearest',cmap='viridis')
            axs[iplot].pcolormesh(ds.time.values, ds.altitude_mie.values, mask.backscatter_coef.sel(line_of_sight=0).T, cmap='Greys', vmin=0,vmax=5, shading='nearest')
        if ('backscatter_coef' in var_list):
            iplot+=1
        
        if ((len(wind_str)>0 and (wind_str in fname)) or (len(wind_str)==0)) and ('u_mie' in var_list):
            wind_speed = compute_wind_speed(ds.u_mie, ds.v_mie)
            im1=axs[iplot].barbs(ds.time.values[:], ds.altitude_mie.values[::3], ds.u_mie.values[:,::3].T, ds.v_mie.values[:,::3].T,wind_speed.values[:,::3].T,
                length=3.5, pivot='middle', cmap='turbo', linewidth=.5, norm = colors.Normalize(vmin=0, vmax=50,clip=True))
            axs[iplot].pcolormesh(ds.time.values, ds.altitude_mie.values, np.fmax(mask.u_mie.values,mask.v_mie.values).T, cmap='Greys', vmin=0,vmax=5, shading='nearest')
            im2=axs[iplot+1].pcolormesh(ds.time.values, ds.altitude_mie.values, ds.w_mie.T,vmin=-6,vmax=6,cmap='RdBu_r',shading='nearest')
            axs[iplot+1].pcolormesh(ds.time.values, ds.altitude_mie.values, mask.w_mie.T, cmap='Greys', vmin=0,vmax=5, shading='nearest')
            im3=axs[iplot+2].pcolormesh(ds.time.values, ds.altitude_mie.values, ds.u_mie.T, vmin=-40, vmax=40, cmap='RdBu_r', shading='nearest')
            axs[iplot+2].pcolormesh(ds.time.values, ds.altitude_mie.values, mask.u_mie.T, cmap='Greys', vmin=0,vmax=5, shading='nearest')
            im4=axs[iplot+3].pcolormesh(ds.time.values, ds.altitude_mie.values, ds.v_mie.T, vmin=-40, vmax=40, cmap='RdBu_r', shading='nearest')
            axs[iplot+3].pcolormesh(ds.time.values, ds.altitude_mie.values, mask.v_mie.T, cmap='Greys', vmin=0,vmax=5, shading='nearest')            
        if ('u_mie' in var_list):
            iplot=iplot+4
            
        if ((len(T_str)>0 and (T_str in fname)) or (len(T_str)==0)) and ('temperature_int' in var_list):
            im5=axs[iplot].pcolormesh(ds.time.values, ds.altitude_mie.values, ds.temperature_int.sel(line_of_sight=0).T-273.15,vmin=-80,vmax=40,cmap='turbo', shading='nearest')
            axs[iplot].pcolormesh(ds.time.values, ds.altitude_mie.values, mask.temperature_int.sel(line_of_sight=0).T, cmap='Greys', vmin=0,vmax=5, shading='nearest')
        if ('temperature_int' in var_list):
            iplot+=1
        
        if ((len(bsc_str)>0 and (bsc_str in fname)) or (len(bsc_str)==0)) and ('aerosol_depolarization_ratio' in var_list):
            im6=axs[iplot].pcolormesh(ds.time.values, ds.altitude_mie.values, ds.aerosol_depolarization_ratio.T,norm=colors.LogNorm(vmin=1e-5,vmax=1),shading='nearest',cmap='plasma')
            axs[iplot].pcolormesh(ds.time.values, ds.altitude_mie.values, mask.aerosol_depolarization_ratio.T, cmap='Greys', vmin=0,vmax=5, shading='nearest')
            
    iplot=0
    if ('backscatter_coef' in var_list):
        plt.colorbar(im0, ax=axs[iplot], label='Backscatter coefficient [m-1 sr-1]', extend='both')
        iplot+=1
    if ('u_mie' in var_list):
        plt.colorbar(im1, ax=axs[iplot], label='Wind speed [m s-1]')
        plt.colorbar(im2, ax=axs[iplot+1], label='Vertical wind [m s-1]')
        plt.colorbar(im3, ax=axs[iplot+2], label='Eastward wind [m s-1]')
        plt.colorbar(im4, ax=axs[iplot+3], label='Northward wind [m s-1]') 
        iplot+=4
    if ('temperature_int' in var_list):
        plt.colorbar(im5, ax=axs[iplot], label='Temperature from\n Rayleigh integration [deg C]')
        iplot+=1
    if ('aerosol_depolarization_ratio' in var_list):
        plt.colorbar(im6, ax=axs[iplot], label='Aerosol depolarization ratio', extend='both')
    ds0 = xr.load_dataset(fname_list[0], engine='h5netcdf')
    ds1 = xr.load_dataset(fname_list[-1], engine='h5netcdf')
    
    if (pd.Timestamp(ds1.time[-1].values) - pd.Timestamp(ds0.time[0].values)).total_seconds() < 12*3600:
        dt_start = pd.Timestamp(ds0.time[0].values)
        if dt_start.hour < 12:
            dt_end = dt_start + pd.Timedelta(hours=12)
        else:
            dt_end = pd.Timestamp(ds0.time[0].values).date() + pd.Timedelta(days=1)
    else: # to do this is temporary because files are long
        dt_start = pd.Timestamp(ds0.time[0].values)
        dt_end = pd.Timestamp(ds1.time[-1].values)
    # else: # to do uncomment this when files are ~hourly or less
    #     dt_start = pd.Timestamp(ds0.time[0].values).date()
    #     dt_end = dt_start + pd.Timedelta(days=1)
        
    for ax in axs:
        ax.set_ylim(0, ylim)  # Updated to use ylim argument
        ax.set_title('')
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
        ax.set_xlabel('Time [UTC]')
        ax.set_ylabel('Altitude [masl]')
        ax.set_xlim(dt_start, dt_end)
    try:
        date_from_fname = re.search("([0-9]{4}\-[0-9]{2}\-[0-9]{2})", fname_list[0]).group(1)
    except:
        try:
            date_from_fname = re.search("([0-9]{4}[0-9]{2}[0-9]{2})", fname_list[0]).group(1)
        except:
            date_from_fname='20251006'
    if not date_from_fname:
        raise ValueError("Could not extract date from filename. Please check the filename format.")
    fig_name = os.path.join(fig_dir, fig_prefix+pd.Timestamp(date_from_fname).strftime('%Y-%m-%d')+'.png')

    axs[0].set_title(fig_title)
    fig.tight_layout()

    if fig_name.startswith('s3://'):
        # Save the figure to an in-memory buffer
        import boto3
        from io import BytesIO

        buffer = BytesIO()
        fig.savefig(buffer, dpi=300, bbox_inches='tight', facecolor='w', format='png')
        buffer.seek(0)

        # Parse the S3 bucket and key from the fig_name
        s3 = boto3.client('s3')
        bucket_name = fig_name.split('/')[2]
        key = '/'.join(fig_name.split('/')[3:])

        # Upload the figure to the S3 bucket
        s3.upload_fileobj(buffer, bucket_name, key)
        buffer.close()

    else:
        # Save the figure locally
        fig.savefig(fig_name,dpi=300,bbox_inches='tight',facecolor='w')


if __name__=='__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Make quicklooks')
    parser.add_argument('--l2a_file', type=str, help='Path to the L2A file')
    parser.add_argument('--l2a_file_list', type=str, nargs='+', help='List of paths to the L2A files for daily quicklooks')
    parser.add_argument('--fig_dir', type=str, default='./', help='Path to the directory where quicklooks are saved')
    parser.add_argument('--fig_prefix', type=str, default='L2A_', help='Figure filename prefix')
    parser.add_argument('--ylim', type=int, default=50000, help='Y-axis limit for the plots')  # Added ylim argument
    parser.add_argument('--wind_str', type=str, default='', help='String in filename to identify proper wind data, e.g. time integration 20MIN')
    parser.add_argument('--bsc_str', type=str, default='', help='String in filename to identify proper backscatter data, e.g. time integration 20MIN')
    parser.add_argument('--T_str', type=str, default='', help='String in filename to identify proper temperature data, e.g. time integration 60MIN')
    parser.add_argument('--mask_flag', type=int, default=1, help='1 to apply quality mask, 0 to ignore it')
    args = parser.parse_args()

    # fname='/data/euliaa-l2/TESTS/L2A_2025-04-14_12-40-01.nc'
    # fig_dir = '/data/euliaa-quicklooks/TESTS/'
    if args.l2a_file_list:
        # If a list of files is provided, create a daily quicklook
        file_list = sorted(args.l2a_file_list)
        fig_title0 = file_list[0].split('/')[-1]
        try:
            fig_title0 = 'L2A_'+re.search("([0-9]{4}\-[0-9]{2}\-[0-9]{2})", fig_title0).group(1)
        except:
            fig_title0 = 'L2A_'+re.search("([0-9]{4}[0-9]{2}[0-9]{2})", fig_title0).group(1)
        fig_title1 = file_list[-1].split('/')[-1]
        try:
            fig_title1 = 'L2A_'+re.search("([0-9]{4}\-[0-9]{2}\-[0-9]{2})", fig_title1).group(1)
        except:
            fig_title1 = 'L2A_'+re.search("([0-9]{4}[0-9]{2}[0-9]{2})", fig_title1).group(1)
        fig_title = fig_title0 + ' to ' + fig_title1
        plot_daily_quicklooks(args.l2a_file_list, args.fig_dir, fig_title, ylim=args.ylim, fig_prefix=args.fig_prefix, wind_str=args.wind_str, bsc_str=args.bsc_str, T_str=args.T_str, mask_flag=args.mask_flag)  # Pass ylim and mask to the function
    elif args.l2a_file:
        fig_title = args.l2a_file.split('/')[-1]
        try:
            fig_title = 'L2A_'+re.search("([0-9]{4}\-[0-9]{2}\-[0-9]{2})", fig_title).group(1)
        except:
            fig_title = 'L2A_'+re.search("([0-9]{4}[0-9]{2}[0-9]{2})", fig_title).group(1)
        plot_quicklooks(args.l2a_file, args.fig_dir, fig_title, args.ylim)  # Pass ylim to the function
    else:
        raise ValueError('Either --l2a_file or --l2a_file_list must be provided')
    

