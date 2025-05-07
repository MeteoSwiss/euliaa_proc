import xarray as xr
import matplotlib.pyplot as plt
import matplotlib.colors as colors
import matplotlib.dates as mdates
import re
import numpy as np

def plot_quicklooks(fname, fig_dir, fig_name, ylim):
    ds = xr.load_dataset(fname)
    fig,axs = plt.subplots(5,figsize=(12,14))
    for var in ['backscatter_coef','w_mie','u_mie','v_mie','temperature_int']:
        ds[var] = ds[var].where(ds[var+'_flag']==0, np.nan)

    ds.backscatter_coef.sel(line_of_sight=0).plot(x='time',norm=colors.LogNorm(vmin=1e-9,vmax=1e-5),ax=axs[0], cbar_kwargs={'label': 'Backscatter coefficient [m-1 sr-1]', 'extend':'both'})
    ds.w_mie.plot(x='time',vmin=-6,vmax=6,ax=axs[1],cmap='seismic')
    ds.u_mie.plot(x='time',ax=axs[2])
    ds.v_mie.plot(x='time',ax=axs[3])
    (ds.temperature_int.sel(line_of_sight=0)-273.15).plot(x='time',ax=axs[4],cbar_kwargs={'label': 'Temperature from\n Rayleigh integration [deg C]'},vmin=-60,vmax=30,cmap='turbo')
    for ax in axs:
        ax.set_ylim(0, ylim)  # Updated to use ylim argument
        ax.set_title('')
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
        ax.set_xlabel('Time [UTC]')

    axs[0].set_title(fig_name)
    fig.tight_layout()
    fig.savefig(fig_dir+fig_name,dpi=300,bbox_inches='tight',facecolor='w')

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
