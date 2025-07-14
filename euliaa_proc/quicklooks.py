import xarray as xr
import matplotlib.pyplot as plt
import matplotlib.colors as colors
import matplotlib.dates as mdates
import re
import numpy as np
import os 
from euliaa_proc.utils.data_utils import compute_wind_speed
import pandas as pd

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
    im=axs[5].barbs(ds.time.values[::2], ds.altitude_mie.values[::2], ds.u_mie.values[::2,::2].T, ds.v_mie.values[::2,::2].T,wind_speed.values[::2,::2].T,
          length=3.5, pivot='middle', cmap='turbo', linewidth=.5)
    axs[5].set_ylabel('Altitude above mean sea level, for Mie peak measurements [m]')
    plt.colorbar(im, ax=axs[5], label='Wind speed [m s-1]')
    ds.w_mie.plot(x='time',vmin=-6,vmax=6,ax=axs[2],cmap='seismic')
    ds.u_mie.plot(x='time',ax=axs[3])
    ds.v_mie.plot(x='time',ax=axs[4])
    (ds.temperature_int.sel(line_of_sight=0)-273.15).plot(x='time',ax=axs[5],cbar_kwargs={'label': 'Temperature from\n Rayleigh integration [deg C]'},vmin=-60,vmax=30,cmap='turbo')
    dt_start = pd.Timestamp(ds.time[0].values).date()
    dt_end = dt_start + pd.Timedelta(days=1)
    for ax in axs:
        ax.set_ylim(0, ylim)  # Updated to use ylim argument
        ax.set_title('')
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
        ax.set_xlabel('Time [UTC]')
    if pd.Timedelta(ds.time[-1].values-ds.time[0].values)< pd.Timedelta(days=1):
        ax.set_xlim(dt_start, dt_end)

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
    parser.add_argument('--fig_dir', type=str, help='Path to the directory where quicklooks are saved')
    parser.add_argument('--ylim', type=int, default=50000, help='Y-axis limit for the plots')  # Added ylim argument
    args = parser.parse_args()

    # fname='/data/euliaa-l2/TESTS/L2A_2025-04-14_12-40-01.nc'
    # fig_dir = '/data/euliaa-quicklooks/TESTS/'
    fig_name = args.l2a_file.split('/')[-1]
    fig_name = 'L2A_'+re.search("([0-9]{4}\-[0-9]{2}\-[0-9]{2})", fig_name).group(1)
    # fig_name = 'L2A_2025-04-17'
    plot_quicklooks(args.l2a_file, args.fig_dir, fig_name, args.ylim)  # Pass ylim to the function
