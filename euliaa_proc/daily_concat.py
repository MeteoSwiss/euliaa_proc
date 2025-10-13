import xarray as xr
import argparse
import s3fs
from pathlib import Path
import logging
import tempfile

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def concat_netcdf_files(input_files, output_file, s3_kwargs=None):
    """
    Concatenate NetCDF files from S3 into a single file.
    
    Parameters:
    -----------
    input_files : list of str
        List of S3 paths to NetCDF files (e.g., 's3://bucket/path/file.nc')
    output_file : str
        Output path for the concatenated NetCDF file
    s3_kwargs : dict, optional
        Additional kwargs for s3fs.S3FileSystem
    """
    logger.info(f"Concatenating {len(input_files)} files")
    
    # Set up S3 filesystem
    s3_kwargs = s3_kwargs or {}
    fs = s3fs.S3FileSystem(**s3_kwargs)
    
    try:
        # Open multiple datasets and concatenate along time dimension
        logger.info("Opening datasets with xarray.open_mfdataset...")
        ds = xr.open_mfdataset(
            input_files,
            # concat_dim='time',
            # combine='nested',
            engine='h5netcdf',
            # chunks='auto',
            storage_options=s3_kwargs
        )
        
        # Sort by time if needed
        if 'time' in ds.dims:
            ds = ds.sortby('time')
        
        logger.info(f"Dataset shape: {ds.dims}")
        logger.info(f"Time range: {ds.time.min().values} to {ds.time.max().values}")
        
        # Save to NetCDF
        logger.info(f"Saving concatenated dataset to {output_file}")

        if output_file.startswith('s3://'): # If output is in a bucket
            import fsspec
            with tempfile.NamedTemporaryFile(suffix=".nc") as tmpfile:
                ds.to_netcdf(tmpfile.name)
                tmpfile.seek(0)
                # write to S3 using fsspec
                try:
                    # This works when called by the service, maybe also in other cases
                    with fsspec.open(output_file, mode='wb', s3={}) as outfile: 
                        outfile.write(tmpfile.read())
                        logger.info(f'Wrote netCDF file to S3: {output_file}')
                except Exception as e:
                    logger.info(e)
                    try:
                        # This is known to work when called by the user, not sure about the service
                        with fsspec.open(output_file, mode='wb', s3=dict(profile='default')) as outfile: 
                            outfile.write(tmpfile.read())
                    except Exception as e2:
                        logger.error(f'Error writing to S3: {e, e2}')
                        raise e2
                tmpfile.flush()

        else: # Save locally
            Path(output_file).parent.mkdir(parents=True, exist_ok=True)
            ds.to_netcdf(output_file, engine='netcdf4')
        
        logger.info("Concatenation completed successfully")
        
    except Exception as e:
        logger.error(f"Error during concatenation: {str(e)}")
        raise
    finally:
        # Close the dataset to free memory
        if 'ds' in locals():
            ds.close()


def main():
    parser = argparse.ArgumentParser(description='Concatenate NetCDF files from S3 along time dimension')
    parser.add_argument('input_files',nargs='+', help='List of S3 paths to NetCDF files (e.g., s3://bucket/path/*.nc)')
    parser.add_argument('-o', '--output', required=True, help='Output path for concatenated NetCDF file (can be S3 or local path)')
    parser.add_argument('--s3-profile',help='AWS profile to use for S3 access')
    parser.add_argument('--verbose', '-v', action='store_true',help='Enable verbose logging')

    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Prepare S3 kwargs
    s3_kwargs = {}
    if args.s3_profile:
        s3_kwargs['profile'] = args.s3_profile
    
    # Run concatenation
    concat_netcdf_files(args.input_files, args.output, s3_kwargs)


if __name__ == '__main__':
    main()
