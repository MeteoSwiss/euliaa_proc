import xarray as xr
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import re
import numpy as np
import os 
from euliaa_proc.utils.data_utils import compute_wind_speed
import pandas as pd

# Interactive quicklooks using Plotly for web viewing with zoom capabilities

# def plot_quicklooks_interactive(fname, fig_dir, fig_title, fig_prefix='', ylim=50000):
#     """
#     Create interactive quicklooks for a single L2A file using Plotly.
#     """
#     if not os.path.exists(fig_dir) and not fig_dir.startswith('s3://'):
#         os.makedirs(fig_dir)
#     fig_name = os.path.join(fig_dir, fig_prefix+os.path.basename(fname).replace('.nc', '.html'))

#     ds = xr.load_dataset(fname, engine='h5netcdf')
    
#     # Apply quality flags
#     for var in ['backscatter_coef','w_mie','u_mie','v_mie','temperature_int']:
#         ds[var] = ds[var].where(ds[var+'_flag']==0, np.nan)
    
#     wind_speed = compute_wind_speed(ds.u_mie, ds.v_mie)

#     # Create subplots
#     fig = make_subplots(
#         rows=6, cols=1,
#         subplot_titles=('', '', '', '', '', ''),
#         vertical_spacing=0.01,
#         shared_xaxes=True
#     )

#     # 1. Backscatter coefficient (log scale)
#     bsc_data = ds.backscatter_coef.sel(line_of_sight=0).values.T
#     fig.add_trace(
#         go.Heatmap(
#             x=ds.time.values,
#             y=ds.altitude_mie.values,
#             z=np.log10(bsc_data),
#             colorscale='Viridis',
#             zmin=-9,
#             zmax=-5,
#             colorbar=dict(
#                 title='log10(Backscatter<br>coefficient)<br>[m-1 sr-1]',
#                 len=0.15,
#                 y=0.92,
#                 yanchor='top',
#                 thickness=15,
#                 x=1.02
#             ),
#             hovertemplate='Time: %{x}<br>Altitude: %{y:.0f} m<br>Backscatter: %{z:.2f}<extra></extra>'
#         ),
#         row=1, col=1
#     )

#     # 2. Wind barbs (represented as quiver/arrows)
#     # Subsample for better visibility
#     # skip = 3
#     # time_sub = ds.time.values[::skip]
#     # alt_sub = ds.altitude_mie.values[::skip]
#     # u_sub = ds.u_mie.values[::skip, ::skip]
#     # v_sub = ds.v_mie.values[::skip, ::skip]
#     # wind_speed_sub = wind_speed.values[::skip, ::skip]
    
#     # # Create meshgrid for arrow positions
#     # time_mesh, alt_mesh = np.meshgrid(range(len(time_sub)), alt_sub)
    
#     # # Flatten arrays for plotting
#     # time_flat = time_mesh.flatten()
#     # alt_flat = alt_mesh.flatten()
#     # u_flat = u_sub.T.flatten()
#     # v_flat = v_sub.T.flatten()
#     # ws_flat = wind_speed_sub.T.flatten()
    
#     # # Remove NaN values
#     # valid = ~(np.isnan(u_flat) | np.isnan(v_flat))
#     # time_valid = time_flat[valid]
#     # alt_valid = alt_flat[valid]
#     # u_valid = u_flat[valid]
#     # v_valid = v_flat[valid]
#     # ws_valid = ws_flat[valid]
    
#     # # Convert to actual time values for plotting
#     # time_valid_dt = [time_sub[i] for i in time_valid]
    
#     # Add wind speed as background heatmap
#     fig.add_trace(
#         go.Heatmap(
#             x=ds.time.values,
#             y=ds.altitude_mie.values,
#             z=wind_speed.values.T,
#             colorscale='Turbo',
#             zmin=0,
#             zmax=50,
#             colorbar=dict(
#                 title='Horizontal wind speed<br>[m s-1]',
#                 len=0.15,
#                 y=0.75,
#                 yanchor='top',
#                 thickness=15,
#                 x=1.02
#             ),
#             hovertemplate='Time: %{x}<br>Altitude: %{y:.0f} m<br>Horizontal wind speed: %{z:.1f} m/s<extra></extra>'
#         ),
#         row=2, col=1
#     )

#     # 3. Vertical wind (w_mie)
#     fig.add_trace(
#         go.Heatmap(
#             x=ds.time.values,
#             y=ds.altitude_mie.values,
#             z=ds.w_mie.values.T,
#             colorscale='RdBu_r',
#             zmin=-6,
#             zmax=6,
#             colorbar=dict(
#                 title='Vertical wind<br>[m s-1]',
#                 len=0.15,
#                 y=0.58,
#                 yanchor='top',
#                 thickness=15,
#                 x=1.02
#             ),
#             hovertemplate='Time: %{x}<br>Altitude: %{y:.0f} m<br>w: %{z:.2f} m/s<extra></extra>'
#         ),
#         row=3, col=1
#     )

#     # 4. Eastward wind (u_mie)
#     fig.add_trace(
#         go.Heatmap(
#             x=ds.time.values,
#             y=ds.altitude_mie.values,
#             z=ds.u_mie.values.T,
#             colorscale='Jet',
#             zmin=-40,
#             zmax=40,
#             colorbar=dict(
#                 title='Eastward wind<br>[m s-1]',
#                 len=0.15,
#                 y=0.41,
#                 yanchor='top',
#                 thickness=15,
#                 x=1.02
#             ),
#             hovertemplate='Time: %{x}<br>Altitude: %{y:.0f} m<br>u: %{z:.2f} m/s<extra></extra>'
#         ),
#         row=4, col=1
#     )

#     # 5. Northward wind (v_mie)
#     fig.add_trace(
#         go.Heatmap(
#             x=ds.time.values,
#             y=ds.altitude_mie.values,
#             z=ds.v_mie.values.T,
#             colorscale='Jet',
#             zmin=-40,
#             zmax=40,
#             colorbar=dict(
#                 title='Northward wind<br>[m s-1]',
#                 len=0.15,
#                 y=0.24,
#                 yanchor='top',
#                 thickness=15,
#                 x=1.02
#             ),
#             hovertemplate='Time: %{x}<br>Altitude: %{y:.0f} m<br>v: %{z:.2f} m/s<extra></extra>'
#         ),
#         row=5, col=1
#     )

#     # 6. Temperature
#     temp_data = ds.temperature_int.sel(line_of_sight=0).values - 273.15
#     fig.add_trace(
#         go.Heatmap(
#             x=ds.time.values,
#             y=ds.altitude_mie.values,
#             z=temp_data.T,
#             colorscale='Turbo',
#             zmin=-60,
#             zmax=30,
#             colorbar=dict(
#                 title='Temperature from<br>Rayleigh integration<br>[deg C]',
#                 len=0.15,
#                 y=0.07,
#                 yanchor='top',
#                 thickness=15,
#                 x=1.02
#             ),
#             hovertemplate='Time: %{x}<br>Altitude: %{y:.0f} m<br>Temperature: %{z:.1f} °C<extra></extra>'
#         ),
#         row=6, col=1
#     )

#     # Update all y-axes and x-axes
#     for i in range(1, 7):
#         fig.update_yaxes(
#             title_text='Altitude [masl]' if i == 4 else '',
#             range=[0, ylim],
#             row=i, col=1
#         )
#         # Only show x-axis title on the bottom plot to reduce clutter
#         if i == 6:
#             fig.update_xaxes(title_text='Time [UTC]', showticklabels=True, row=i, col=1)
#         else:
#             fig.update_xaxes(showticklabels=True, row=i, col=1)
    
#     # Update layout
#     fig.update_layout(
#         title=dict(text=fig_title, x=0.5, xanchor='center'),
#         height=2000,
#         showlegend=False,
#         hovermode='closest'
#     )

#     # Save the figure
#     if fig_name.startswith('s3://'):
#         import boto3
#         from io import BytesIO
        
#         # Get HTML string and encode to bytes
#         html_str = fig.to_html()
#         html_bytes = html_str.encode('utf-8')
        
#         buffer = BytesIO(html_bytes)
        
#         s3 = boto3.client('s3')
#         bucket_name = fig_name.split('/')[2]
#         key = '/'.join(fig_name.split('/')[3:])
        
#         s3.upload_fileobj(buffer, bucket_name, key, ExtraArgs={'ContentType': 'text/html'})
#         buffer.close()
#     else:
#         fig.write_html(fig_name)


def plot_daily_quicklooks_interactive(fname_list, fig_dir, fig_title, fig_prefix='L2A_', ylim=30000, 
                                     wind_str='', bsc_str='', T_str='', mask_flag=1):
    """
    Create interactive daily quicklooks from multiple L2A files using Plotly.
    """
    T_str=T_str.replace('None','')
    wind_str=wind_str.replace('None','')
    bsc_str=bsc_str.replace('None','')
    print('wind_str:', wind_str)
    print('bsc_str:', bsc_str)
    if not os.path.exists(fig_dir) and not fig_dir.startswith('s3://'):
        os.makedirs(fig_dir)
    
    # Load first file to check available variables
    ds_0 = xr.load_dataset(fname_list[0], engine='h5netcdf')
    var_list = ['backscatter_coef', 'w_mie', 'u_mie', 'v_mie', 'temperature_int', 'aerosol_depolarization_ratio']
    var_list = [var for var in var_list if var in ds_0.data_vars]
    
    n_plots = len(var_list) + ('u_mie' in var_list)
    
    # Create subplots
    subplot_titles = []
    if 'backscatter_coef' in var_list:
        subplot_titles.append('')
    if 'u_mie' in var_list:
        subplot_titles.extend(['', '', '', ''])  # Wind speed, w, u, v
    if 'temperature_int' in var_list:
        subplot_titles.append('')
    if 'aerosol_depolarization_ratio' in var_list:
        subplot_titles.append('')
    
    fig = make_subplots(
        rows=n_plots, cols=1,
        subplot_titles=subplot_titles,

        vertical_spacing=0.03,
        shared_xaxes=True
    )
    
    # Collect data from all files
    all_ds = []
    for fname in fname_list:
        ds = xr.load_dataset(fname, engine='h5netcdf')
        all_ds.append(ds)
    
    # Concatenate datasets
    ds_combined = xr.concat(all_ds, dim='time')
    
    # Apply masking
    if mask_flag:
        for var in var_list:
            ds_combined[var] = ds_combined[var].where(ds_combined[var+'_flag'] == 0, np.nan)
    
    # Calculate colorbar positions based on subplot layout
    # With vertical_spacing=0.08, each plot takes (1 - 0.08*(n_plots-1)) / n_plots of space
    spacing = 0.03
    subplot_height = (1.0 - spacing * (n_plots - 1)) / n_plots
    
    # Function to get center y position for each subplot
    def get_colorbar_y(subplot_idx, n_total):
        # subplot_idx is 0-based
        # Start from top: y = 1.0 for first subplot center
        y_top = 1.0 - (subplot_idx * (subplot_height + spacing))
        y_center = y_top - subplot_height / 2
        return y_center
    
    iplot = 1
    colorbar_idx = 0
    
    # 1. Backscatter coefficient
    if 'backscatter_coef' in var_list:
        plot_data = (len(bsc_str) == 0 or any(bsc_str in fname for fname in fname_list))
        if plot_data:
            bsc_data = ds_combined.backscatter_coef.sel(line_of_sight=0).values.T
            fig.add_trace(
                go.Heatmap(
                    x=ds_combined.time.values,
                    y=ds_combined.altitude_mie.values,
                    z=np.log10(bsc_data),
                    colorscale='Viridis',
                    zmin=-9,
                    zmax=-5,
                    colorbar=dict(
                        title='log10(Backscatter<br>coefficient)<br>[m-1 sr-1]',
                        len=subplot_height * 0.85,
                        y=get_colorbar_y(colorbar_idx, n_plots),
                        yanchor='middle',
                        thickness=15,
                        x=1.02
                    ),
                    hovertemplate='Time: %{x}<br>Altitude: %{y:.0f} m<br>log10(Bsc): %{z:.2f}<extra></extra>'
                ),
                row=iplot, col=1
            )
        iplot += 1
        colorbar_idx += 1
    
    # 2-5. Wind plots
    if 'u_mie' in var_list:
        plot_data = (len(wind_str) == 0 or any(wind_str in fname for fname in fname_list))
        if plot_data:
            wind_speed = compute_wind_speed(ds_combined.u_mie, ds_combined.v_mie)
            
            # Wind speed
            fig.add_trace(
                go.Heatmap(
                    x=ds_combined.time.values,
                    y=ds_combined.altitude_mie.values,
                    z=wind_speed.values.T,
                    colorscale='Turbo',
                    zmin=0,
                    zmax=50,
                    colorbar=dict(
                        title='Wind speed<br>[m s-1]',
                        len=subplot_height * 0.85,
                        y=get_colorbar_y(colorbar_idx, n_plots),
                        yanchor='middle',
                        thickness=15,
                        x=1.02
                    ),
                    hovertemplate='Time: %{x}<br>Altitude: %{y:.0f} m<br>Wind speed: %{z:.1f} m/s<extra></extra>'
                ),
                row=iplot, col=1
            )
            iplot += 1
            colorbar_idx += 1
            
            # Vertical wind
            fig.add_trace(
                go.Heatmap(
                    x=ds_combined.time.values,
                    y=ds_combined.altitude_mie.values,
                    z=ds_combined.w_mie.values.T,
                    colorscale='RdBu_r',
                    zmin=-6,
                    zmax=6,
                    colorbar=dict(
                        title='Vertical wind<br>[m s-1]',
                        len=subplot_height * 0.85,
                        y=get_colorbar_y(colorbar_idx, n_plots),
                        yanchor='middle',
                        thickness=15,
                        x=1.02
                    ),
                    hovertemplate='Time: %{x}<br>Altitude: %{y:.0f} m<br>w: %{z:.2f} m/s<extra></extra>'
                ),
                row=iplot, col=1
            )
            iplot += 1
            colorbar_idx += 1
            
            # Eastward wind
            fig.add_trace(
                go.Heatmap(
                    x=ds_combined.time.values,
                    y=ds_combined.altitude_mie.values,
                    z=ds_combined.u_mie.values.T,
                    colorscale='RdBu_r',
                    zmin=-40,
                    zmax=40,
                    colorbar=dict(
                        title='Eastward wind<br>[m s-1]',
                        len=subplot_height * 0.85,
                        y=get_colorbar_y(colorbar_idx, n_plots),
                        yanchor='middle',
                        thickness=15,
                        x=1.02
                    ),
                    hovertemplate='Time: %{x}<br>Altitude: %{y:.0f} m<br>u: %{z:.2f} m/s<extra></extra>'
                ),
                row=iplot, col=1
            )
            iplot += 1
            colorbar_idx += 1
            
            # Northward wind
            fig.add_trace(
                go.Heatmap(
                    x=ds_combined.time.values,
                    y=ds_combined.altitude_mie.values,
                    z=ds_combined.v_mie.values.T,
                    colorscale='RdBu_r',
                    zmin=-40,
                    zmax=40,
                    colorbar=dict(
                        title='Northward wind<br>[m s-1]',
                        len=subplot_height * 0.85,
                        y=get_colorbar_y(colorbar_idx, n_plots),
                        yanchor='middle',
                        thickness=15,
                        x=1.02
                    ),
                    hovertemplate='Time: %{x}<br>Altitude: %{y:.0f} m<br>v: %{z:.2f} m/s<extra></extra>'
                ),
                row=iplot, col=1
            )
            iplot += 1
            colorbar_idx += 1
    
    # 6. Temperature
    if 'temperature_int' in var_list:
        plot_data = (len(T_str) == 0 or any(T_str in fname for fname in fname_list))
        if plot_data:
            temp_data = ds_combined.temperature_int.sel(line_of_sight=0).values - 273.15
            fig.add_trace(
                go.Heatmap(
                    x=ds_combined.time.values,
                    y=ds_combined.altitude_mie.values,
                    z=temp_data.T,
                    colorscale='Turbo',
                    zmin=-80,
                    zmax=40,
                    colorbar=dict(
                        title='Temperature from<br>Rayleigh integration<br>[deg C]',
                        len=subplot_height * 0.85,
                        y=get_colorbar_y(colorbar_idx, n_plots),
                        yanchor='middle',
                        thickness=15,
                        x=1.02
                    ),
                    hovertemplate='Time: %{x}<br>Altitude: %{y:.0f} m<br>Temperature: %{z:.1f} °C<extra></extra>'
                ),
                row=iplot, col=1
            )
        iplot += 1
        colorbar_idx += 1
    
    # 7. Aerosol depolarization ratio
    if 'aerosol_depolarization_ratio' in var_list:
        plot_data = (len(bsc_str) == 0 or any(bsc_str in fname for fname in fname_list))
        if plot_data:
            adr_data = ds_combined.aerosol_depolarization_ratio.values.T
            fig.add_trace(
                go.Heatmap(
                    x=ds_combined.time.values,
                    y=ds_combined.altitude_mie.values,
                    z=np.log10(adr_data),
                    colorscale='Plasma',
                    zmin=-5,
                    zmax=0,
                    colorbar=dict(
                        title='log10(Aerosol<br>depolarization<br>ratio)',
                        len=subplot_height * 0.85,
                        y=get_colorbar_y(colorbar_idx, n_plots),
                        yanchor='middle',
                        thickness=15,
                        x=1.02
                    ),
                    hovertemplate='Time: %{x}<br>Altitude: %{y:.0f} m<br>log10(ADR): %{z:.2f}<extra></extra>'
                ),
                row=iplot, col=1
            )
    
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
    dt_start = pd.Timestamp(ds0.time[0].values)
    dt_end = pd.Timestamp(ds1.time[-1].values)
    
    # Update all axes
    for i in range(1, n_plots + 1):
        if i==1:
            fig.update_yaxes(
                title_text='Altitude [masl]',
                range=[0, ylim],
                autorange=False,
                row=i, col=1
            )
        else:
            fig.update_yaxes(
                title_text='Altitude [masl]',
                row=i, col=1
            )
        # fig.update_yaxes(
        #     title_text='Altitude [masl]',
        #     range=[0, ylim],
        #     row=i, col=1
        # )
        fig.update_yaxes(matches='y')






        # Only show x-axis title on the bottom plot to reduce clutter
        if i == n_plots:
            fig.update_xaxes(
                title_text='Time [UTC]',
                range=[dt_start, dt_end],
                showticklabels=True,
                row=i, col=1
            )
        else:
            fig.update_xaxes(
                range=[dt_start, dt_end],
                showticklabels=True,
                row=i, col=1
            )
    
    # Update layout
    fig.update_layout(
        title=dict(text=fig_title, x=0.5, xanchor='center'),
        height=300 * n_plots,
        showlegend=False,
        hovermode='closest'
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
    
    fig_name = os.path.join(fig_dir, fig_prefix + pd.Timestamp(date_from_fname).strftime('%Y-%m-%d') + '.html')
    
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
    parser.add_argument('--l2a_file', type=str, help='Path to the L2A file')
    parser.add_argument('--l2a_file_list', type=str, nargs='+', help='List of paths to the L2A files for daily quicklooks')
    parser.add_argument('--fig_dir', type=str, default='./', help='Path to the directory where quicklooks are saved')
    parser.add_argument('--fig_prefix', type=str, default='L2A_', help='Figure filename prefix')
    parser.add_argument('--ylim', type=int, default=30000, help='Y-axis limit for the plots')
    parser.add_argument('--wind_str', type=str, default='', help='String in filename to identify proper wind data, e.g. time integration 20MIN')
    parser.add_argument('--bsc_str', type=str, default='', help='String in filename to identify proper backscatter data, e.g. time integration 20MIN')
    parser.add_argument('--T_str', type=str, default='', help='String in filename to identify proper temperature data, e.g. time integration 60MIN')
    parser.add_argument('--mask_flag', type=int, default=1, help='1 to apply quality mask, 0 to ignore it')
    args = parser.parse_args()

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
        plot_daily_quicklooks_interactive(
            args.l2a_file_list, args.fig_dir, fig_title, 
            ylim=args.ylim, fig_prefix=args.fig_prefix, 
            wind_str=args.wind_str, bsc_str=args.bsc_str, 
            T_str=args.T_str, mask_flag=args.mask_flag
        )
    elif args.l2a_file:
        fig_title = args.l2a_file.split('/')[-1]
        try:
            fig_title = 'L2A_'+re.search("([0-9]{4}\-[0-9]{2}\-[0-9]{2})", fig_title).group(1)
        except:
            fig_title = 'L2A_'+re.search("([0-9]{4}[0-9]{2}[0-9]{2})", fig_title).group(1)
        plot_quicklooks_interactive(args.l2a_file, args.fig_dir, fig_title, args.fig_prefix, args.ylim)
    else:
        raise ValueError('Either --l2a_file or --l2a_file_list must be provided')
