import numpy as np
import xarray as xr
import pandas as pd
from euliaa_proc.measurement import Measurement
from euliaa_proc.log import logger
from euliaa_proc.utils.cloud_detection import compute_cbh

class EProfileBSCMeasurement(Measurement):
    """
    Class to handle the conversion of EULIAA L2A backscatter data to CHM-like format.
    Inherits from Measurement class.
    """

    def __init__(self, config_eprofile_bsc_path, l2a_data, chm_template_path=None, line_of_sight_idx=0, conf_qc_file=None):
        """
        Initialize EProfileBSCMeasurement
        
        Parameters:
        -----------
        config_eprofile_path : str
            Path to configuration file
        l2a_data : xarray.Dataset
            L2A dataset containing backscatter_coef, time, altitude_mie, station_altitude
        chm_template_path : str, optional
            Path to CHM template file. If None, will create basic structure.
        line_of_sight_idx : int
            Index of line_of_sight to extract from L2A data (default: 0 = zenith)
        conf_qc_file : str, optional
            Path to QC configuration file
        """
        super().__init__(config_eprofile_bsc_path, conf_qc_file=conf_qc_file)
        self.l2a_data = l2a_data
        self.chm_template_path = chm_template_path
        self.line_of_sight_idx = line_of_sight_idx
        
    # def compute_cbh(self):
    #     """
    #     Compute cloud base height from L2A cloud mask
        
    #     Returns:
    #     --------
    #     cbh : xarray.DataArray or None
    #         Cloud base height for the specified line of sight, or None if cloud_mask doesn't exist
    #     """
    #     # Check if cloud_mask exists
    #     if 'cloud_mask' not in self.l2a_data:
    #         logger.warning("cloud_mask not found in L2A data, cannot compute cloud base height")
    #         return None
            
    #     cloud_mask = self.l2a_data.cloud_mask
        
    #     # Use altitude if exists, otherwise altitude_mie
    #     if 'altitude' in self.l2a_data:
    #         altitude_coord = self.l2a_data.altitude
    #         altitude_dim = 'altitude'
    #         logger.info("Using 'altitude' coordinate for CBH calculation")
    #     elif 'altitude_mie' in self.l2a_data:
    #         altitude_coord = self.l2a_data.altitude_mie
    #         altitude_dim = 'altitude_mie'
    #         logger.info("Using 'altitude_mie' coordinate for CBH calculation")
    #     else:
    #         logger.error("Neither 'altitude' nor 'altitude_mie' found in L2A data")
    #         return None
            
    #     # Compute cloud base height
    #     alt_in_cloud = cloud_mask * altitude_coord - 999999 * (1 - cloud_mask)
    #     cbh = abs(alt_in_cloud).min(dim=altitude_dim)
    #     cbh.data[cbh > altitude_coord.max()] = np.nan
        
    #     return cbh.isel(line_of_sight=self.line_of_sight_idx)
    
    def load_chm_template(self):
        """
        Load CHM template dataset
        
        Returns:
        --------
        chm_template : xarray.Dataset
            CHM template dataset
        """
        if self.chm_template_path:
            logger.info(f"Loading CHM template from: {self.chm_template_path}")
            return xr.open_dataset(self.chm_template_path)
        else:
            # Create basic CHM structure if no template provided
            logger.warning("No CHM template provided, creating basic structure")
            return self.create_basic_chm_structure()
    
    def create_basic_chm_structure(self):
        """
        Create a basic CHM structure if no template is provided
        
        Returns:
        --------
        basic_chm : xarray.Dataset
            Basic CHM-like dataset structure
        """
        # This is a minimal CHM structure - in practice you'd want to use a real CHM template
        time_dummy = np.arange(10)  # Dummy time dimension
        range_dummy = np.arange(0, 10000, 30)  # Dummy range from 0 to 10km with 30m resolution
        
        basic_chm = xr.Dataset(
            {
                'beta_raw': (['time', 'range'], np.full((len(time_dummy), len(range_dummy)), np.nan)),
                'latitude': ((), 0.0),
                'longitude': ((), 0.0),
                'altitude': ((), 0.0),
            },
            coords={
                'time': time_dummy,
                'range': range_dummy,
            },
            attrs={
                'title': 'Basic CHM structure',
                'source': '',
                'device_name': '',
                'day': 1,
                'month': 1,
                'year': 2024,
            }
        )
        
        return basic_chm
    
    def create_chm_like_dataset(self):
        """
        Create CHM-like dataset with L2A coordinates and backscatter data
        Based on the logic from create_chm_like_dataset.py
        
        Returns:
        --------
        ds_new : xarray.Dataset
            New dataset with CHM structure, L2A coordinates, and L2A backscatter data
        """
        
        # Load CHM template
        chm_template = self.load_chm_template()
        
        # Extract L2A coordinates
        time_l2_original = self.l2a_data.time
        altitude_l2 = self.l2a_data.altitude_mie.values
        station_altitude = self.l2a_data.station_altitude.values
        range_l2 = altitude_l2 - station_altitude
        
        # Convert time from L2A epoch (1970-01-01) to CHM epoch (1904-01-01)
        # Calculate the offset between the two epochs
        epoch_1904 = pd.Timestamp('1904-01-01 00:00:00')
        epoch_1970 = pd.Timestamp('1970-01-01 00:00:00')
        epoch_offset_seconds = (epoch_1970 - epoch_1904).total_seconds()
        
        logger.info(f"Converting time from 1970 epoch to 1904 epoch (offset: {epoch_offset_seconds} seconds)")
        
        # Convert L2A time values to CHM epoch
        # First convert datetime64 to numeric seconds since 1970, then add the epoch offset
        time_l2_seconds_1970 = pd.to_datetime(time_l2_original.values).astype(np.int64) #/ 1e9
        time_l2_chm_values = time_l2_seconds_1970 + epoch_offset_seconds
        
        # Create new time coordinate with CHM epoch and values
        time_l2 = xr.DataArray(
            time_l2_chm_values,
            dims=['time'],
            coords={'time': time_l2_chm_values},
            attrs={
                'units': 'seconds since 1904-01-01 00:00:00.000 00:00',
                'long_name': 'time UTC',
                'axis': 'T'
            }
        )
        
        logger.info(f"L2A time points: {len(time_l2)}")
        logger.info(f"L2A altitude range: {altitude_l2.min():.1f} - {altitude_l2.max():.1f} m")
        logger.info(f"Station altitude: {station_altitude:.1f} m")
        logger.info(f"Calculated range: {range_l2.min():.1f} - {range_l2.max():.1f} m")
        
        # Create new coordinates dictionary
        new_coords = {
            'time': time_l2,
            'range': ('range', range_l2, chm_template.range.attrs if hasattr(chm_template.range, 'attrs') else {})
        }
        
        # Copy scalar coordinates from CHM template, but override with L2A station coordinates
        for coord_name, coord_data in chm_template.coords.items():
            if coord_name not in ['time', 'range'] and coord_data.ndim == 0:
                # Use L2A station coordinates for latitude, longitude, altitude
                if coord_name == 'latitude' and 'station_latitude' in self.l2a_data:
                    new_coords[coord_name] = self.l2a_data.station_latitude
                    logger.info(f"Using L2A station_latitude: {self.l2a_data.station_latitude.values}")
                elif coord_name == 'longitude' and 'station_longitude' in self.l2a_data:
                    new_coords[coord_name] = self.l2a_data.station_longitude
                    logger.info(f"Using L2A station_longitude: {self.l2a_data.station_longitude.values}")
                elif coord_name == 'altitude' and 'station_altitude' in self.l2a_data:
                    new_coords[coord_name] = self.l2a_data.station_altitude
                    logger.info(f"Using L2A station_altitude: {self.l2a_data.station_altitude.values}")
                else:
                    new_coords[coord_name] = coord_data
            elif coord_name not in ['time', 'range'] and coord_name != 'range_hr':
                # Keep other 1D coordinates like 'layer'
                new_coords[coord_name] = coord_data
        
        # Create empty dataset with new coordinates
        ds_new = xr.Dataset(coords=new_coords)
        
        # Add all CHM variables with appropriate dimensions, filled with NaN/fill values
        for var_name, var_data in chm_template.data_vars.items():
            
            # Skip high resolution variables for simplicity
            if 'range_hr' in var_data.dims:
                logger.info(f"Skipping high resolution variable: {var_name}")
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
            backscatter_l2 = self.l2a_data.backscatter_coef.isel(line_of_sight=self.line_of_sight_idx)
            ds_new['beta_raw'].values[:] = backscatter_l2.values
            
            # Update beta_raw attributes
            ds_new['beta_raw'].attrs.update({
                'units': 'm-1 sr-1',
                'long_name': 'Volume backscatter coefficient from EULIAA L2A data',
                'source': f'L2A backscatter_coef (line_of_sight={self.line_of_sight_idx})'
            })
            
            logger.info(f"beta_raw filled with backscatter data, shape: {ds_new['beta_raw'].shape}")
            logger.info(f"Non-NaN values: {(~np.isnan(ds_new['beta_raw'].values)).sum()}")
            logger.info(f"Value range: {np.nanmin(ds_new['beta_raw'].values):.2e} - {np.nanmax(ds_new['beta_raw'].values):.2e}")
        
        # Fill cbh with cloud base height if it exists
        if 'cbh' in ds_new:
            cbh = compute_cbh(self.data, line_of_sight_idx=self.line_of_sight_idx)
            if cbh is not None:
                if 'layer' in ds_new['cbh'].dims:
                    # Fill only the first layer with CBH data
                    ds_new['cbh'].values[:, 0] = cbh.values
                else:
                    ds_new['cbh'].values[:] = cbh.values
                
                # Update cbh attributes
                ds_new['cbh'].attrs.update({
                    'long_name': 'Lowest cloud base height detected in EULIAA L2A data',
                    'source': f'L2A cloud mask (line_of_sight={self.line_of_sight_idx})'
                })
                logger.info("Cloud base height successfully computed and added")
            else:
                logger.warning("Could not compute cloud base height, leaving cbh variable empty")
        
        # Update global attributes
        ds_new.attrs.update(chm_template.attrs)
        
        # Extract date information from L2A time variable (use first time point)
        first_time = self.l2a_data.time.values[0]
        dt = pd.to_datetime(first_time)
        
        # Update specific attributes with L2A values
        # Use np.int32 to avoid int64 (LL suffix) in NetCDF output
        attrs_to_update = {
            'title': 'CHM-like dataset with EULIAA backscatter data',
            'source_l2a': 'EULIAA L2A backscatter_coef',
            'line_of_sight_used': np.int32(self.line_of_sight_idx),
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
        attrs_to_update['location'] = self.l2a_data.attrs['site_location'] if 'site_location' in self.l2a_data.attrs else ''
        attrs_to_update['institution'] = self.l2a_data.attrs['institution'] if 'institution' in self.l2a_data.attrs else ''
        attrs_to_update['wmo_id'] = self.l2a_data.attrs['wmo_id'] if 'wmo_id' in self.l2a_data.attrs else ''
        attrs_to_update['wigos_id'] = self.l2a_data.attrs['wigos_station_id'] if 'wigos_station_id' in self.l2a_data.attrs else ''

        # Apply all attribute updates
        ds_new.attrs.update(attrs_to_update)
        
        logger.info(f"Date extracted from L2A: {dt.year}-{dt.month:02d}-{dt.day:02d}")
        
        return ds_new
    
    def load_data(self):
        """
        Load the L2A data and create CHM-like dataset structure.
        This method populates self.data with the CHM-like dataset.
        """
        logger.info("Creating CHM-like dataset from L2A data")
        
        # Create the CHM-like dataset
        self.data = self.create_chm_like_dataset()
        
        logger.info("CHM-like dataset created successfully")
        # logger.info(f"Dataset dimensions: {dict(self.data.dims)}")
        # logger.info(f"Data variables: {list(self.data.data_vars.keys())}")
    
    # def save_dataset(self, output_filename):
    #     """
    #     Save the CHM-like dataset to a NetCDF file
        
    #     Parameters:
    #     -----------
    #     output_filename : str
    #         Path to output NetCDF file
    #     """
        
    #     # Set encoding for better compression and compatibility
    #     encoding = {}
        
    #     for var_name in self.data.data_vars:
    #         if self.data[var_name].dtype.kind == 'f':  # float variables
    #             encoding[var_name] = {
    #                 'zlib': True,
    #                 'complevel': 4,
    #                 '_FillValue': np.nan
    #             }
    #         else:  # integer variables - use appropriate fill value for data type
    #             dtype = self.data[var_name].dtype
    #             if dtype == np.int8:
    #                 fill_value = -127
    #             elif dtype == np.int16:
    #                 fill_value = -999
    #             elif dtype in [np.int32, np.int64]:
    #                 fill_value = -999
    #             else:
    #                 fill_value = 0
                    
    #             encoding[var_name] = {
    #                 'zlib': True,
    #                 'complevel': 4,
    #                 '_FillValue': fill_value
    #             }
        
    #     # Save to NetCDF with unlimited time dimension
    #     self.data.to_netcdf(output_filename, encoding=encoding, unlimited_dims=['time'])
    #     logger.info(f"Dataset saved to: {output_filename}")


if __name__ == '__main__':
    # Example usage
    import os
    
    # Load L2A data
    l2a_file = '../data/L2A_20250830_030001.nc'
    chm_template_file = '../data/20251001_pay_CHM200110_0920_000.nc'
    config_file = 'config/config_eprofile_bsc.yaml'  # You'll need to create this
    
    l2a_data = xr.open_dataset(l2a_file, decode_times=False)
    l2a_data=l2a_data.isel(time=slice(0,15))
    # Create EProfileBSCMeasurement instance
    meas = EProfileBSCMeasurement(
        config_eprofile_bsc_path=config_file,
        l2a_data=l2a_data,
        chm_template_path=chm_template_file,
        line_of_sight_idx=0
    )
    
    # Load the data (creates CHM-like dataset)
    meas.load_data()
    print(meas.data)
    
    # Save the dataset
    output_file = '../data/eprofile_bsc_output.nc'
    from euliaa_proc.write_netcdf import Writer
    eprofile_bsc_writer = Writer(meas, output_file=output_file)
    eprofile_bsc_writer.write_nc()
    
    print("EProfile BSC measurement created successfully!")
    print(f"Output saved to: {output_file}")
