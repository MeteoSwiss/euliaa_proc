import xarray as xr
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import re
import numpy as np
import os 
from euliaa_proc.utils.data_utils import compute_wind_speed
import pandas as pd
from netCDF4 import Dataset

var_fig_dict_general = {
        'backscatter_coef': {'var_names':['BSCMieZ','BSCMieE','BSCMieN'], 'spacing': 0.05, 'ylim': 50000},
        'signal_mie': {'var_names':['signalAPD1Z','signalAPD1E','signalAPD1N','signalAPD1D'], 'spacing': 0.03, 'ylim': 50000},
        'signal_ray': {'var_names':['signalAPD2Z','signalAPD2E','signalAPD2N','signalAPD2D','background'], 'spacing': 0.03, 'ylim': 100000},
    }

def compute_background(signal, number_of_gates=20):
    """Compute background rate from signal data."""
    inds_for_bg = np.where(signal.mean(axis=0)>1)[0][-number_of_gates:]
    background_photons = np.nanmean(signal[:,inds_for_bg],axis=1)
    background_rate = background_photons / 1e-6 # Assuming 1 microsecond integration time
    return background_rate*1e-6 # in MHz 

# Interactive quicklooks using Plotly for web viewing with zoom capabilities

def plot_daily_signal_quicklooks_interactive(fname_list, fig_dir, fig_title, fig_prefix='L1_', ylim=50000):
    """
    Create interactive daily quicklooks from multiple L2A files using Plotly.
    """
    
    if not os.path.exists(fig_dir) and not fig_dir.startswith('s3://'):
        os.makedirs(fig_dir)
    
    # Load first file to check available variables
    # ds_0 = xr.load_dataset(fname_list[0], engine='h5netcdf')
    
    nc0 = Dataset(fname_list[0], diskless=True, persist=False)
    rec0 = xr.open_dataset(xr.backends.NetCDF4DataStore(nc0.groups.get('rec')))
    glo0 = xr.open_dataset(xr.backends.NetCDF4DataStore(nc0.groups.get('glo')))
    var_list = []
    if 'BSCMieZ' in rec0.keys():
        var_list.append('backscatter_coef')
    if 'signalAPD1Z' in rec0.keys():
        var_list.append('signal_mie')
    if 'signalAPD2Z' in rec0.keys():
        var_list.append('signal_ray')
    var_fig_dict = {var: var_fig_dict_general[var] for var in var_list}

    fig_dict = {var: make_subplots(rows=len(var_fig_dict[var]['var_names']), cols=1, shared_xaxes=True, vertical_spacing=var_fig_dict[var]['spacing'], subplot_titles=['']*len(var_fig_dict[var]['var_names'])) for var in var_list}
    
    # Collect data from all files
    all_ds = []
    for fname in fname_list:
        nc = Dataset(fname, diskless=True, persist=False)
        rec = xr.open_dataset(xr.backends.NetCDF4DataStore(nc.groups.get('rec')))
        glo = xr.open_dataset(xr.backends.NetCDF4DataStore(nc.groups.get('glo')))
        
        # ds = xr.load_dataset(fname, engine='h5netcdf')
        all_ds.append(rec)
    
    # Concatenate datasets
    ds_combined = xr.concat(all_ds, dim='phony_dim_1')
    ds_combined['timestamp'] = pd.to_datetime(ds_combined.time.values,unit='s')
        
    # Calculate colorbar positions based on subplot layout
    # With vertical_spacing=0.08, each plot takes (1 - 0.08*(n_plots-1)) / n_plots of space
    # spacing = 0.03
    # subplot_height = (1.0 - spacing * (n_plots - 1)) / n_plots
    
    # Function to get center y position for each subplot
    def get_colorbar_y(subplot_idx, subplot_height,spacing):
        # subplot_idx is 0-based
        # Start from top: y = 1.0 for first subplot center
        y_top = 1.0 - (subplot_idx * (subplot_height + spacing))
        y_center = y_top - subplot_height / 2
        return y_center
    
    # iplot = 1
    # colorbar_idx = 0
    
    # 1. Backscatter coefficient
    if 'backscatter_coef' in var_list:
        n_plots = len(var_fig_dict['backscatter_coef']['var_names'])
        spacing = var_fig_dict['backscatter_coef']['spacing']
        subplot_height = (1.0 - spacing * (n_plots - 1)) / n_plots

        fig_dict['backscatter_coef'].add_trace(
            go.Heatmap(
                x=ds_combined.timestamp.values,
                y=glo.altInt.values,
                z=np.log10(ds_combined.BSCMieZ.values.T),
                colorscale='Viridis',
                zmin=-9,
                zmax=-5,
                colorbar=dict(
                    title='log10(Backscatter<br>coefficient Zenith)<br>[m-1 sr-1]',
                    len=subplot_height * 0.85,
                    y=get_colorbar_y(0, subplot_height, spacing),
                    yanchor='middle',
                    thickness=15,
                    x=1.02
                ),
                hovertemplate='Time: %{x}<br>Altitude: %{y:.0f} m<br>log10(Bsc): %{z:.2f}<extra></extra>'
            ),
            row=1, col=1
            )
        fig_dict['backscatter_coef'].add_trace(
            go.Heatmap(
                x=ds_combined.timestamp.values,
                y=glo.altInt.values,
                z=np.log10(ds_combined.BSCMieE.values.T),
                colorscale='Viridis',
                zmin=-9,
                zmax=-5,
                colorbar=dict(
                    title='log10(Backscatter<br>coefficient East)<br>[m-1 sr-1]',
                    len=subplot_height * 0.85,
                    y=get_colorbar_y(1, subplot_height, spacing),
                    yanchor='middle',
                    thickness=15,
                    x=1.02
                ),
                hovertemplate='Time: %{x}<br>Altitude: %{y:.0f} m<br>log10(Bsc): %{z:.2f}<extra></extra>'
            ),
            row=2, col=1
            )
        fig_dict['backscatter_coef'].add_trace(
            go.Heatmap(
                x=ds_combined.timestamp.values,
                y=glo.altInt.values,
                z=np.log10(ds_combined.BSCMieN.values.T),
                colorscale='Viridis',
                zmin=-9,
                zmax=-5,
                colorbar=dict(
                    title='log10(Backscatter<br>coefficient North)<br>[m-1 sr-1]',
                    len=subplot_height * 0.85,
                    y=get_colorbar_y(2, subplot_height, spacing),
                    yanchor='middle',
                    thickness=15,
                    x=1.02
                ),
                hovertemplate='Time: %{x}<br>Altitude: %{y:.0f} m<br>log10(Bsc): %{z:.2f}<extra></extra>'
            ),
            row=3, col=1
            )
        
    # 2-5. Signal Mie plots
    if 'signal_mie' in var_list:
        n_plots = len(var_fig_dict['signal_mie']['var_names'])
        spacing = var_fig_dict['signal_mie']['spacing']
        subplot_height = (1.0 - spacing * (n_plots - 1)) / n_plots

        fig_dict['signal_mie'].add_trace(
            go.Heatmap(
                x=ds_combined.timestamp.values,
                y=glo.altInt.values,
                z=np.log10(ds_combined.signalAPD1Z.values.T),
                customdata=ds_combined.signalAPD1Z.values.T,
                colorscale='Turbo',
                zmin=0,
                zmax=8,
                colorbar=dict(
                    title='log10(Signal Mie Z)<br>[-]',
                    len=subplot_height * 0.85,
                    y=get_colorbar_y(0, subplot_height, spacing),
                    yanchor='middle',
                    thickness=15,
                    x=1.02
                ),
                hovertemplate='Time: %{x}<br>Altitude: %{y:.0f} m<br>Signal Mie Z: %{customdata:.0f}<extra></extra>' 
            ),
            row=1, col=1
        )

        fig_dict['signal_mie'].add_trace(
            go.Heatmap(
                x=ds_combined.timestamp.values,
                y=glo.altInt.values,
                z=np.log10(ds_combined.signalAPD1E.values.T),
                customdata=ds_combined.signalAPD1E.values.T,
                colorscale='Turbo',
                zmin=0,
                zmax=8,
                colorbar=dict(
                    title='log10(Signal Mie E)<br>[-]',
                    len=subplot_height * 0.85,
                    y=get_colorbar_y(1, subplot_height, spacing),
                    yanchor='middle',
                    thickness=15,
                    x=1.02
                ),
                hovertemplate='Time: %{x}<br>Altitude: %{y:.0f} m<br>Signal Mie E: %{customdata:.0f}<extra></extra>'
            ),
            row=2, col=1
        )

        fig_dict['signal_mie'].add_trace(
            go.Heatmap(
                x=ds_combined.timestamp.values,
                y=glo.altInt.values,
                z=np.log10(ds_combined.signalAPD1N.values.T),
                customdata=ds_combined.signalAPD1N.values.T,
                colorscale='Turbo',
                zmin=0,
                zmax=8,
                colorbar=dict(
                    title='log10(Signal Mie N)<br>[-]',
                    len=subplot_height * 0.85,
                    y=get_colorbar_y(2, subplot_height, spacing),
                    yanchor='middle',
                    thickness=15,
                    x=1.02
                ),
                hovertemplate='Time: %{x}<br>Altitude: %{y:.0f} m<br>Signal Mie N: %{customdata:.0f}<extra></extra>'
            ),
            row=3, col=1
        )

        fig_dict['signal_mie'].add_trace(
            go.Heatmap(
                x=ds_combined.timestamp.values,
                y=glo.altInt.values,
                z=np.log10(ds_combined.signalAPD1D.values.T) if np.max(ds_combined.signalAPD1D.values) > 0 else ds_combined.signalAPD1D.values.T,
                customdata=ds_combined.signalAPD1D.values.T,
                colorscale='Turbo',
                zmin=0,
                zmax=5,
                colorbar=dict(
                    title='log10(Signal Mie D)<br>[-]' if np.max(ds_combined.signalAPD1D.values) > 0 else 'Signal Mie D<br>[-]',
                    len=subplot_height * 0.85,
                    y=get_colorbar_y(3, subplot_height, spacing),
                    yanchor='middle',
                    thickness=15,
                    x=1.02
                ),
                hovertemplate='Time: %{x}<br>Altitude: %{y:.0f} m<br>Signal Mie D: %{customdata:.0f}<extra></extra>'
            ),
            row=4, col=1
        )

    if 'signal_ray' in var_list:
        n_plots = len(var_fig_dict['signal_ray']['var_names'])
        spacing = var_fig_dict['signal_ray']['spacing']
        subplot_height = (1.0 - spacing * (n_plots - 1)) / n_plots

        fig_dict['signal_ray'].add_trace(
            go.Heatmap(
                x=ds_combined.timestamp.values,
                y=glo.altInt.values,
                z=np.log10(ds_combined.signalAPD2Z.values.T),
                customdata=ds_combined.signalAPD2Z.values.T,
                colorscale='Turbo',
                zmin=1,
                zmax=5.5,
                colorbar=dict(
                    title='log10(Signal Ray Z)<br>[-]',
                    len=subplot_height * 0.85,
                    y=get_colorbar_y(0, subplot_height, spacing),
                    yanchor='middle',
                    thickness=15,
                    x=1.02
                ),
                hovertemplate='Time: %{x}<br>Altitude: %{y:.0f} m<br>Signal Ray Z: %{customdata:.0f}<extra></extra>'
            ),
            row=1, col=1
        )

        fig_dict['signal_ray'].add_trace(
            go.Heatmap(
                x=ds_combined.timestamp.values,
                y=glo.altInt.values,
                z=np.log10(ds_combined.signalAPD2E.values.T),
                customdata=ds_combined.signalAPD2E.values.T,
                colorscale='Turbo',
                zmin=1,
                zmax=5.5,
                colorbar=dict(
                    title='log10(Signal Ray E)<br>[-]',
                    len=subplot_height * 0.85,
                    y=get_colorbar_y(1, subplot_height, spacing),
                    yanchor='middle',
                    thickness=15,
                    x=1.02
                ),
                hovertemplate='Time: %{x}<br>Altitude: %{y:.0f} m<br>Signal Ray E: %{customdata:.0f}<extra></extra>'
            ),
            row=2, col=1
        )

        fig_dict['signal_ray'].add_trace(
            go.Heatmap(
                x=ds_combined.timestamp.values,
                y=glo.altInt.values,
                z=np.log10(ds_combined.signalAPD2N.values.T),
                customdata=ds_combined.signalAPD2N.values.T,
                colorscale='Turbo',
                zmin=1,
                zmax=5.5,
                colorbar=dict(
                    title='log10(Signal Ray N)<br>[-]',
                    len=subplot_height * 0.85,
                    y=get_colorbar_y(2, subplot_height, spacing),
                    yanchor='middle',
                    thickness=15,
                    x=1.02
                ),
                hovertemplate='Time: %{x}<br>Altitude: %{y:.0f} m<br>Signal Ray N: %{customdata:.0f}<extra></extra>'
            ),
            row=3, col=1
        )

        fig_dict['signal_ray'].add_trace(
            go.Heatmap(
                x=ds_combined.timestamp.values,
                y=glo.altInt.values,
                z=np.log10(ds_combined.signalAPD2D.values.T) if np.max(ds_combined.signalAPD2D.values) > 0 else ds_combined.signalAPD2D.values.T,
                customdata=ds_combined.signalAPD2D.values.T,
                colorscale='Turbo',
                zmin=0,
                zmax=5,
                colorbar=dict(
                    title='log10(Signal Ray D)<br>[-]' if np.max(ds_combined.signalAPD2D.values) > 0 else 'Signal Ray D<br>[-]',
                    len=subplot_height * 0.85,
                    y=get_colorbar_y(3, subplot_height, spacing),
                    yanchor='middle',
                    thickness=15,
                    x=1.02
                ),
                hovertemplate='Time: %{x}<br>Altitude: %{y:.0f} m<br>Signal Ray D: %{customdata:.0f}<extra></extra>' 
            ),
            row=4, col=1
        )

        # Compute and plot background rates
        try:
            bg2Z = compute_background(ds_combined.signalAPD2Z.values * 1., number_of_gates=20)
            bg2E = compute_background(ds_combined.signalAPD2E.values * 1., number_of_gates=20)
            bg2N = compute_background(ds_combined.signalAPD2N.values * 1., number_of_gates=20)
            bg2D = compute_background(ds_combined.signalAPD2D.values * 1., number_of_gates=20)
            
            fig_dict['signal_ray'].add_trace(
                go.Scatter(
                    x=ds_combined.timestamp.values,
                    y=bg2Z,
                    mode='lines',
                    line=dict(color='black', width=1),
                    name='Z',
                    hovertemplate='Time: %{x}<br>Background Z: %{y:.2e}<extra></extra>'
                ),
                row=5, col=1
            )
            fig_dict['signal_ray'].add_trace(
                go.Scatter(
                    x=ds_combined.timestamp.values,
                    y=bg2E,
                    mode='lines',
                    line=dict(color='blue', width=1),
                    name='E',
                    hovertemplate='Time: %{x}<br>Background E: %{y:.2e}<extra></extra>'
                ),
                row=5, col=1
            )
            fig_dict['signal_ray'].add_trace(
                go.Scatter(
                    x=ds_combined.timestamp.values,
                    y=bg2N,
                    mode='lines',
                    line=dict(color='red', width=1),
                    name='N',
                    hovertemplate='Time: %{x}<br>Background N: %{y:.2e}<extra></extra>'
                ),
                row=5, col=1
            )
            fig_dict['signal_ray'].add_trace(
                go.Scatter(
                    x=ds_combined.timestamp.values,
                    y=bg2D,
                    mode='lines',
                    line=dict(color='green', width=1),
                    name='D',
                    hovertemplate='Time: %{x}<br>Background D: %{y:.2e}<extra></extra>'
                ),
                row=5, col=1
            )
            
            # Update y-axis for background subplot (log scale, specific range)
            fig_dict['signal_ray'].update_yaxes(
                title_text='Background [MHz]',
                type='log',
                range=[0, 3.5], 
                row=5, col=1
            )
        except Exception as e:
            print(f"Error computing background: {e}")

    
    # Set time range
    ds0 = all_ds[0]
    ds1 = all_ds[-1]
    
    # if (pd.Timestamp(ds1.time[-1].values) - pd.Timestamp(ds0.time[0].values)).total_seconds() < 12*3600:
    #     dt_start = pd.Timestamp(ds0.time[0].values)
    #     if dt_start.hour < 12:
    #         dt_end = dt_start + pd.Timedelta(hours=12)
    #     else:
    #         dt_end = pd.Timestamp(ds0.time[0].values).date() + pd.Timedelta(days=1)
    # else:
    dt_start = pd.Timestamp(ds0.time[0].values.item())
    dt_end = pd.Timestamp(ds1.time[-1].values.item())
    
    # Update all axes
    for var in var_list:
        fig = fig_dict[var]
        n_plots = len(var_fig_dict[var]['var_names'])  # Number of subplots in the current figure
        subplot_height = (1.0 - spacing * (n_plots - 1)) / n_plots
        
        # Check if this is signal_ray with background subplot
        is_signal_ray_with_bg = (var == 'signal_ray' and 'background' in var_fig_dict[var]['var_names'])
        n_heatmap_plots = n_plots - 1 if is_signal_ray_with_bg else n_plots

        for i in range(1, n_plots + 1):
            # Skip the background subplot - it's already configured
            if is_signal_ray_with_bg and i == n_plots:
                # Only update x-axis for background subplot
                fig.update_xaxes(
                    title_text='Time [UTC]',
                    showticklabels=True,
                    row=i, col=1
                )
                continue
                
            if i==1:
                fig.update_yaxes(
                    title_text='Altitude [masl]',
                    range=[0, var_fig_dict[var]['ylim']] if 'ylim' in var_fig_dict[var] else [0, ylim],
                    autorange=False,
                    row=i, col=1
                )
            else:
                fig.update_yaxes(
                    title_text='Altitude [masl]',
                    row=i, col=1
                )

            # Only show x-axis title on the bottom plot to reduce clutter
            if i == n_plots:
                fig.update_xaxes(
                    title_text='Time [UTC]',
                    showticklabels=True,
                    row=i, col=1
                )
            else:
                fig.update_xaxes(
                    showticklabels=True,
                    row=i, col=1
                )
        
        # Match y-axes only for heatmap plots (exclude background)
        if is_signal_ray_with_bg:
            # Match y-axes for first 4 subplots only
            for i in range(1, n_heatmap_plots + 1):
                fig.update_yaxes(matches='y', row=i, col=1)
        else:
            fig.update_yaxes(matches='y')
            
        # Update layout
        fig.update_layout(
            title=dict(text=fig_title, x=0.5, xanchor='center'),
            height=300 * n_plots,
            showlegend=is_signal_ray_with_bg,  # Show legend for background traces
            hovermode='closest'
        )
        
        # Position legend for signal_ray background plot
        if is_signal_ray_with_bg:
            fig.update_layout(
                legend=dict(
                    orientation='v',
                    yanchor='middle',
                    y=0.08,  # Position at bottom subplot
                    xanchor='left',
                    x=1.02,
                    font=dict(size=10)
                )
            )
        
        # Generate figure name
        try:
            date_from_fname = re.search("([0-9]{4}\-[0-9]{2}\-[0-9]{2})", fname_list[0]).group(1)
        except:
            try:
                date_from_fname = re.search("([0-9]{4}[0-9]{2}[0-9]{2})", fname_list[0]).group(1)
            except:
                date_from_fname = '20251006'
        
        if not date_from_fname:
            raise ValueError("Could not extract date from filename. Please check the filename format.")
        
        fig_name = os.path.join(fig_dir, fig_prefix + pd.Timestamp(date_from_fname).strftime('%Y-%m-%d') + '_' + var + '.html')
        print(f"Saving figure: {fig_name}")
        
        # Save the figure
        if fig_name.startswith('s3://'):
            import boto3
            from io import BytesIO
            
            # Get HTML string and encode to bytes
            html_str = fig.to_html()
            html_bytes = html_str.encode('utf-8')
            
            buffer = BytesIO(html_bytes)
            
            s3 = boto3.client('s3')
            bucket_name = fig_name.split('/')[2]
            key = '/'.join(fig_name.split('/')[3:])
            
            s3.upload_fileobj(buffer, bucket_name, key, ExtraArgs={'ContentType': 'text/html'})
            buffer.close()
        else:
            fig.write_html(fig_name)


if __name__=='__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Make interactive quicklooks with Plotly')
    parser.add_argument('--l1_file', type=str, help='Path to the L2A file')
    parser.add_argument('--l1_file_list', type=str, nargs='+', help='List of paths to the L2A files for daily quicklooks')
    parser.add_argument('--fig_dir', type=str, default='./', help='Path to the directory where quicklooks are saved')
    parser.add_argument('--fig_prefix', type=str, default='L1_', help='Figure filename prefix')
    parser.add_argument('--ylim', type=int, default=50000, help='Y-axis limit for the plots')
    args = parser.parse_args()

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
        plot_daily_signal_quicklooks_interactive(
            args.l1_file_list, args.fig_dir, fig_title, 
            ylim=args.ylim, fig_prefix=args.fig_prefix
        )
    elif args.l1_file:
        fig_title = args.l1_file.split('/')[-1]
        try:
            fig_title = 'L1_'+re.search("([0-9]{4}\-[0-9]{2}\-[0-9]{2})", fig_title).group(1)
        except:
            fig_title = 'L1_'+re.search("([0-9]{4}[0-9]{2}[0-9]{2})", fig_title).group(1)
        plot_daily_signal_quicklooks_interactive(
            [args.l1_file], args.fig_dir, fig_title, 
            ylim=args.ylim, fig_prefix=args.fig_prefix
        )
    else:
        raise ValueError('Either --l1_file or --l1_file_list must be provided')