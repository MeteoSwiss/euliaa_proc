import xarray as xr
import numpy as np

def compute_cbh(ds_l2_source, line_of_sight_idx):
    cloud_mask = ds_l2_source.cloud_mask
    alt_in_cloud = cloud_mask * ds_l2_source.altitude_mie - 999999*(1-cloud_mask)
    cbh = abs(alt_in_cloud).min(dim='altitude_mie')
    cbh.data[cbh>ds_l2_source.altitude_mie.max()]=np.nan
    return cbh.isel(line_of_sight=line_of_sight_idx)

def create_chm_like_dataset(ds_chm_template, ds_l2_source, line_of_sight_idx=0):
    """
    Create a new dataset with CHM structure but with L2A coordinates and backscatter data
    
    Parameters:
    -----------
    ds_chm_template : xarray.Dataset
        CHM dataset to use as template structure
    ds_l2_source : xarray.Dataset  
        L2A dataset containing backscatter_coef, time, altitude_mie, station_altitude
    line_of_sight_idx : int
        Index of line_of_sight to extract from L2A data (default: 0 = zenith)
        
    Returns:
    --------
    ds_new : xarray.Dataset
        New dataset with CHM structure, L2A coordinates, and L2A backscatter data
    """
    
    # Extract L2A coordinates
    time_l2 = ds_l2_source.time
    altitude_l2 = ds_l2_source.altitude_mie.values
    station_altitude = ds_l2_source.station_altitude.values
    range_l2 = altitude_l2 - station_altitude
    
    print(f"L2A time points: {len(time_l2)}")
    print(f"L2A altitude range: {altitude_l2.min():.1f} - {altitude_l2.max():.1f} m")
    print(f"Station altitude: {station_altitude:.1f} m")
    print(f"Calculated range: {range_l2.min():.1f} - {range_l2.max():.1f} m")
    
    # Create new coordinates dictionary
    new_coords = {
        'time': time_l2,
        'range': ('range', range_l2, ds_chm_template.range.attrs if hasattr(ds_chm_template.range, 'attrs') else {})
    }
    
    # Copy scalar coordinates from CHM template, but override with L2A station coordinates
    for coord_name, coord_data in ds_chm_template.coords.items():
        if coord_name not in ['time', 'range'] and coord_data.ndim == 0:
            # Use L2A station coordinates for latitude, longitude, altitude
            if coord_name == 'latitude' and 'station_latitude' in ds_l2_source:
                new_coords[coord_name] = ds_l2_source.station_latitude
                print(f"Using L2A station_latitude: {ds_l2_source.station_latitude.values}")
            elif coord_name == 'longitude' and 'station_longitude' in ds_l2_source:
                new_coords[coord_name] = ds_l2_source.station_longitude
                print(f"Using L2A station_longitude: {ds_l2_source.station_longitude.values}")
            elif coord_name == 'altitude' and 'station_altitude' in ds_l2_source:
                new_coords[coord_name] = ds_l2_source.station_altitude
                print(f"Using L2A station_altitude: {ds_l2_source.station_altitude.values}")
            else:
                new_coords[coord_name] = coord_data
        elif coord_name not in ['time', 'range'] and coord_name != 'range_hr':
            # Keep other 1D coordinates like 'layer'
            new_coords[coord_name] = coord_data
    
    # Create empty dataset with new coordinates
    ds_new = xr.Dataset(coords=new_coords)
    
    # Add all CHM variables with appropriate dimensions, filled with NaN/fill values
    for var_name, var_data in ds_chm_template.data_vars.items():
        
        # Skip high resolution variables for simplicity
        if 'range_hr' in var_data.dims:
            print(f"Skipping high resolution variable: {var_name}")
            continue
            
        # Determine new shape and dimensions
        new_dims = []
        new_shape = []
        
        for dim in var_data.dims:
            if dim == 'time':
                new_dims.append('time')
                new_shape.append(len(time_l2))
            elif dim == 'range':
                new_dims.append('range')
                new_shape.append(len(range_l2))
            else:
                new_dims.append(dim)
                new_shape.append(var_data.sizes[dim])
        
        new_dims = tuple(new_dims)
        new_shape = tuple(new_shape)
        
        # Create array with appropriate fill values
        if var_name == 'beta_raw':
            # Will fill this with backscatter data later
            new_array = np.full(new_shape, np.nan, dtype=np.float32)
        elif var_name == 'cbh':
            new_array = np.full(new_shape, np.nan, dtype=np.float64)
        elif var_data.dtype.kind in ['f', 'c']:  # float or complex
            new_array = np.full(new_shape, np.nan, dtype=var_data.dtype)
        elif var_data.dtype == np.int8:
            new_array = np.full(new_shape, -127, dtype=np.int8)
        elif var_data.dtype == np.int16:
            new_array = np.full(new_shape, -999, dtype=np.int16)
        elif var_data.dtype in [np.int32, np.int64]:
            new_array = np.full(new_shape, -999, dtype=var_data.dtype)
        else:
            new_array = np.zeros(new_shape, dtype=var_data.dtype)
        

        
    
        # Create DataArray
        ds_new[var_name] = xr.DataArray(
            new_array,
            dims=new_dims,
            attrs=var_data.attrs.copy()
        )
    
    # Now fill beta_raw with L2A backscatter data
    if 'beta_raw' in ds_new:
        backscatter_l2 = ds_l2_source.backscatter_coef.isel(line_of_sight=line_of_sight_idx)
        ds_new['beta_raw'].values[:] = backscatter_l2.values
        
        # Update beta_raw attributes
        ds_new['beta_raw'].attrs.update({
            'units': 'm-1 sr-1',
            'long_name': 'Volume backscatter coefficient from EULIAA L2A data',
            'source': f'L2A backscatter_coef (line_of_sight={line_of_sight_idx})'
        })
        
        print(f"beta_raw filled with backscatter data, shape: {ds_new['beta_raw'].shape}")
        print(f"Non-NaN values: {(~np.isnan(ds_new['beta_raw'].values)).sum()}")
        print(f"Value range: {np.nanmin(ds_new['beta_raw'].values):.2e} - {np.nanmax(ds_new['beta_raw'].values):.2e}")
    
    if 'cbh' in ds_new:
        cbh = compute_cbh(ds_l2_source, line_of_sight_idx=line_of_sight_idx)
        ds_new['cbh'].values[:,0] = cbh.values
        # Update cbh attributes
        ds_new['cbh'].attrs.update({
            'long_name': 'Lowest cloud base height detected in EULIAA L2A data',
            'source': f'L2A cloud mask (line_of_sight={line_of_sight_idx})'
        })

    # Update global attributes
    ds_new.attrs.update(ds_chm_template.attrs)
    
    # Extract date information from L2A time variable (use first time point)
    first_time = ds_l2_source.time.values[0]
    # Convert numpy datetime64 to datetime object
    import pandas as pd
    dt = pd.to_datetime(first_time)
    
    # Update specific attributes with L2A values
    # Use numpy.int32 to avoid int64 (LL suffix) in NetCDF output
    attrs_to_update = {
        'title': 'CHM-like dataset with EULIAA backscatter data',
        'source_l2a': 'EULIAA L2A backscatter_coef',
        'line_of_sight_used': np.int32(line_of_sight_idx),
        'processing_note': 'CHM structure with L2A time/range coordinates and backscatter data',
        
        # Date from L2A time variable - use np.int32 to avoid LL suffix
        'day': np.int32(dt.day),
        'month': np.int32(dt.month), 
        'year': np.int32(dt.year),
        
        # Empty fields as requested
        'source': '',
        'device_name': '',
        'serlom': '',
        'overlap_file': '',
    }
    
    # Add L2A attributes if they exist
    attrs_to_update['location'] = ds_l2_source.attrs['site_location'] if 'site_location' in ds_l2_source.attrs else ''
    attrs_to_update['institution'] = ds_l2_source.attrs['institution'] if 'institution' in ds_l2_source.attrs else ''
    attrs_to_update['wmo_id'] = ds_l2_source.attrs['wmo_id'] if 'wmo_id' in ds_l2_source.attrs else ''
    attrs_to_update['wigos_id'] = ds_l2_source.attrs['wigos_station_id'] if 'wigos_station_id' in ds_l2_source.attrs else ''
    
    # Apply all attribute updates
    ds_new.attrs.update(attrs_to_update)
    print(f"Date extracted from L2A: {dt.year}-{dt.month:02d}-{dt.day:02d}")
    
    return ds_new


def save_chm_like_dataset(ds_chm_like, output_filename):
    """
    Save the CHM-like dataset to a NetCDF file
    
    Parameters:
    -----------
    ds_chm_like : xarray.Dataset
        The CHM-like dataset to save
    output_filename : str
        Path to output NetCDF file
    """
    
    # # Set encoding for better compression and compatibility
    # encoding = {}
    
    # for var_name in ds_chm_like.data_vars:
    #     if ds_chm_like[var_name].dtype.kind == 'f':  # float variables
    #         encoding[var_name] = {
    #             'zlib': True,
    #             'complevel': 4,
    #             # '_FillValue': np.nan
    #         }
    #     else:  # integer variables - use appropriate fill value for data type
    #         dtype = ds_chm_like[var_name].dtype
    #         if dtype == np.int8:
    #             fill_value = -127
    #         elif dtype == np.int16:
    #             fill_value = -999
    #         elif dtype in [np.int32, np.int64]:
    #             fill_value = -999
    #         else:
    #             fill_value = 0
                
    #         encoding[var_name] = {
    #             'zlib': True,
    #             'complevel': 4,
    #             # '_FillValue': fill_value
    #         }
    
    
    # Save to NetCDF with unlimited time dimension
    ds_chm_like.to_netcdf(output_filename, unlimited_dims=['time'])
    print(f"Dataset saved to: {output_filename}")


if __name__ == "__main__":
    # Example usage
    
    # Load datasets
    ds_l2 = xr.open_dataset('../data/L2A_20250830_030001.nc')
    ds_chm = xr.open_dataset('../data/20251001_pay_CHM200110_0920_000.nc')
    ds_l2 = ds_l2.isel(time=slice(0,10))
    # Create CHM-like dataset
    ds_chm_like = create_chm_like_dataset(ds_chm, ds_l2, line_of_sight_idx=0)
    
    print("\nDataset created successfully!")
    print(f"Dataset dimensions: {dict(ds_chm_like.dims)}")
    print(f"Data variables: {list(ds_chm_like.data_vars.keys())}")
    
    # Save to file
    output_file = "../data/chm_like_with_l2a_backscatter.nc"
    print(1, type(ds_chm_like.day))
    save_chm_like_dataset(ds_chm_like, output_file)
    
    # Display some basic info
    print(2, type(ds_chm_like.day))

    test_ds = xr.open_dataset(output_file)
    print(test_ds.day)
    print(3, type(test_ds.day))