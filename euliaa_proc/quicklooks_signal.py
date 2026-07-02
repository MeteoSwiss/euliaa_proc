import xarray as xr
import matplotlib.pyplot as plt
import matplotlib.colors as colors
import matplotlib.dates as mdates
import re
from netCDF4 import Dataset
import datetime
import numpy as np
import os 
from euliaa_proc.utils.data_utils import compute_wind_speed
import pandas as pd

# Example use with L1 files on s3 bucket: python3 quicklooks.py --l1_file_list $(s3cmd ls s3://euliaa-l1/TESTS/L1_20250723* | awk '{print $4}')


def plot_daily_signal_quicklooks(fname_list, fig_dir, fig_title, fig_prefix='L1_', ylim=50000):
    if not os.path.exists(fig_dir) and not fig_dir.startswith('s3://'):
    # Create the directory if it does not exist
        os.makedirs(fig_dir)
    
    fig1, axs1 = plt.subplots(4,figsize=(12,10))
    fig2, axs2 = plt.subplots(4,figsize=(12,10))
    fig3, axs3 = plt.subplots(3,figsize=(12,7.5))
    plotBSC=0
    
    for fname in fname_list:
        nc = Dataset(fname, diskless=True, persist=False)
        rec = xr.open_dataset(xr.backends.NetCDF4DataStore(nc.groups.get('rec')))
        glo = xr.open_dataset(xr.backends.NetCDF4DataStore(nc.groups.get('glo')))
        
        t = [datetime.datetime.fromtimestamp(tt) for tt in rec.time.values]
        t1 = t[-1]+datetime.timedelta(seconds=glo.deltaSec.values.item())
        t_edges = np.array(t+[t1])
        alt = glo.altInt.values
        alt1 = np.array([alt[-1]+glo.AltitudeResolution])
        alt_edges = np.concatenate((alt,alt1))

        im10=axs1[0].pcolormesh(t_edges,alt_edges, rec.signalAPD1Z.T,shading='flat',norm=colors.LogNorm(vmin=1,vmax=1e4))
        im11=axs1[1].pcolormesh(t_edges,alt_edges, rec.signalAPD1E.T,shading='flat',norm=colors.LogNorm(vmin=1,vmax=1e4))
        im12=axs1[2].pcolormesh(t_edges,alt_edges, rec.signalAPD1N.T,shading='flat',norm=colors.LogNorm(vmin=1,vmax=1e4))
        im13=axs1[3].pcolormesh(t_edges,alt_edges, rec.signalAPD1D.T,shading='flat',vmin=0,vmax=1)

        im20=axs2[0].pcolormesh(t_edges,alt_edges, rec.signalAPD2Z.T,shading='flat',norm=colors.LogNorm(vmin=1,vmax=1e6))
        im21=axs2[1].pcolormesh(t_edges,alt_edges, rec.signalAPD2E.T,shading='flat',norm=colors.LogNorm(vmin=1,vmax=1e6))
        im22=axs2[2].pcolormesh(t_edges,alt_edges, rec.signalAPD2N.T,shading='flat',norm=colors.LogNorm(vmin=1,vmax=1e6))
        im23=axs2[3].pcolormesh(t_edges,alt_edges, rec.signalAPD2D.T,shading='flat',vmin=0,vmax=1)


        if 'BSCMieZ' in rec.keys():
            # if not(np.isnan(rec.BSCMieZ.max()) and np.isnan(rec.BSCMieE.max()) and np.isnan(rec.BSCMieN.max())): # That's if we don't want empty quicklooks
            im30=axs3[0].pcolormesh(t_edges,alt_edges, rec.BSCMieZ.T,shading='flat',norm=colors.LogNorm(vmin=1e-9,vmax=1e-5),cmap='viridis')
            im31=axs3[1].pcolormesh(t_edges,alt_edges, rec.BSCMieE.T,shading='flat',norm=colors.LogNorm(vmin=1e-9,vmax=1e-5),cmap='viridis')
            im32=axs3[2].pcolormesh(t_edges,alt_edges, rec.BSCMieN.T,shading='flat',norm=colors.LogNorm(vmin=1e-9,vmax=1e-5),cmap='viridis')
            plotBSC=1

    plt.colorbar(im10,ax=axs1[0],label='Signal Mie Z [-]',extend='both')
    plt.colorbar(im11,ax=axs1[1],label='Signal Mie E [-]',extend='both')
    plt.colorbar(im12,ax=axs1[2],label='Signal Mie N [-]',extend='both')
    plt.colorbar(im13,ax=axs1[3],label='Signal Mie D [-]',extend='both')

    plt.colorbar(im20,ax=axs2[0],label='Signal Ray Z [-]',extend='both')
    plt.colorbar(im21,ax=axs2[1],label='Signal Ray E [-]',extend='both')
    plt.colorbar(im22,ax=axs2[2],label='Signal Ray N [-]',extend='both')
    plt.colorbar(im23,ax=axs2[3],label='Signal Ray D [-]',extend='both')

    if plotBSC:
        plt.colorbar(im30,ax=axs3[0],label='Backscatter coefficient [m-1 sr-1]', extend='both')
        plt.colorbar(im31,ax=axs3[1],label='Backscatter coefficient [m-1 sr-1]', extend='both')
        plt.colorbar(im32,ax=axs3[2],label='Backscatter coefficient [m-1 sr-1]', extend='both')


    nc0 = Dataset(fname_list[0], diskless=True, persist=False)
    rec0 = xr.open_dataset(xr.backends.NetCDF4DataStore(nc0.groups.get('rec')))
    dt0 = datetime.datetime.fromtimestamp(rec0.time.values[0])

    nc1 = Dataset(fname_list[-1], diskless=True, persist=False)
    rec1 = xr.open_dataset(xr.backends.NetCDF4DataStore(nc1.groups.get('rec')))
    glo1 = xr.open_dataset(xr.backends.NetCDF4DataStore(nc1.groups.get('glo')))
    dt1 = datetime.datetime.fromtimestamp(rec1.time.values[-1])+datetime.timedelta(seconds=glo1.deltaSec.values.item())
    

    if (dt1-dt0).total_seconds() < 12*3600:
        dt_start = dt0
        if dt_start.hour < 12:
            dt_end = dt0 + datetime.timedelta(hours=12)
        else:
            dt_end = dt0.date() + datetime.timedelta(days=1)
    else: # to do this is temporary because files are long
        dt_start = dt0
        dt_end = dt1
    # else: # to do uncomment this when files are ~hourly or less
    #     dt_start = pd.Timestamp(ds0.time[0].values).date()
    #     dt_end = dt_start + pd.Timedelta(days=1)

    axs = axs1.tolist()+axs2.tolist()        
    if plotBSC:
        axs+=axs3.tolist()

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
    fig_name1 = os.path.join(fig_dir, fig_prefix+pd.Timestamp(date_from_fname).strftime('%Y-%m-%d')+'_signal_mie.png')
    fig_name2 = os.path.join(fig_dir, fig_prefix+pd.Timestamp(date_from_fname).strftime('%Y-%m-%d')+'_signal_ray.png')
    axs1[0].set_title(fig_title)
    axs2[0].set_title(fig_title)
    fig1.tight_layout()
    fig2.tight_layout()
    savefig(fig1,fig_name1)
    savefig(fig2,fig_name2)

    if plotBSC:
        fig_name3 = os.path.join(fig_dir, fig_prefix+pd.Timestamp(date_from_fname).strftime('%Y-%m-%d')+'_backscatter_coef.png')    
        axs3[0].set_title(fig_title)
        fig3.tight_layout()
        savefig(fig3,fig_name3)
    
    

def savefig(fig,fig_name):

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
        print('Saved daily quicklook to S3:', fig_name)
    else:
        # Save the figure locally
        fig.savefig(fig_name,dpi=300,bbox_inches='tight',facecolor='w')
        print('Saved daily quicklook to:', fig_name)

if __name__=='__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Make quicklooks')
    parser.add_argument('--l1_file', type=str, help='Path to the L1 file')
    parser.add_argument('--l1_file_list', type=str, nargs='+', help='List of paths to the L1 files for daily quicklooks')
    parser.add_argument('--fig_dir', type=str, default='./', help='Path to the directory where quicklooks are saved')
    parser.add_argument('--fig_prefix', type=str, default='L1_', help='Figure filename prefix')
    parser.add_argument('--ylim', type=int, default=50000, help='Y-axis limit for the plots')  # Added ylim argument
    args = parser.parse_args()

    # fname='/data/euliaa-l2/TESTS/L2A_2025-04-14_12-40-01.nc'
    # fig_dir = '/data/euliaa-quicklooks/TESTS/'
    if args.l1_file_list:
        # If a list of files is provided, create a daily quicklook
        file_list = sorted(args.l1_file_list)
        fig_title0 = file_list[0].split('/')[-1]
        try:
            fig_title0 = 'L1_'+re.search("([0-9]{4}\-[0-9]{2}\-[0-9]{2})", fig_title0).group(1)
        except:
            fig_title0 = 'L1_'+re.search("([0-9]{4}[0-9]{2}[0-9]{2})", fig_title0).group(1)
        fig_title1 = file_list[-1].split('/')[-1]
        try:
            fig_title1 = 'L1_'+re.search("([0-9]{4}\-[0-9]{2}\-[0-9]{2})", fig_title1).group(1)
        except:
            fig_title1 = 'L1_'+re.search("([0-9]{4}[0-9]{2}[0-9]{2})", fig_title1).group(1)
        fig_title = fig_title0 + ' to ' + fig_title1
        plot_daily_signal_quicklooks(args.l1_file_list, args.fig_dir, fig_title, ylim=args.ylim, fig_prefix=args.fig_prefix)  # Pass ylim and mask to the function
    elif args.l1_file:
        fig_title = args.l1_file.split('/')[-1]
        try:
            fig_title = 'L1_'+re.search("([0-9]{4}\-[0-9]{2}\-[0-9]{2})", fig_title).group(1)
        except:
            fig_title = 'L1_'+re.search("([0-9]{4}[0-9]{2}[0-9]{2})", fig_title).group(1)
        plot_daily_signal_quicklooks(args.l1_file, args.fig_dir, fig_title, ylim=args.ylim)  # Pass ylim and mask to the function
    else:
        raise ValueError('Either --l1_file or --l1_file_list must be provided')
    

