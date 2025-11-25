import xarray as xr
import numpy as np
import matplotlib.pyplot as plt
import boto3
import datetime
import argparse

s3 = boto3.client("s3")

def list_files_in_date_range(bucket, main_prefix, start_date, end_date):
    """
    start_date and end_date are datetime.date objects.
    """
    current = start_date
    results = []

    while current <= end_date:
        # Build S3 prefix: YYYY/MM/DD/
        prefix = main_prefix+current.strftime("/%Y/%m/%d/")
        
        response = s3.list_objects_v2(Bucket=bucket, Prefix=prefix)

        if "Contents" in response:
            for obj in response["Contents"]:
                if obj["Key"].endswith(".nc"):
                    results.append(f's3://{bucket}/{obj["Key"]}')
        
        current += datetime.timedelta(days=1)

    return results


def compute_w_offset(ds, savefig=None):
    """
    Compute vertical velocity offset from NetCDF dataset.
    """
    ds = ds.drop_duplicates(dim="time")
    w = ds.w_mie
    alt = ds.altitude_mie.to_numpy().reshape((1,-1)).repeat(w.sizes['time'], axis=0)
    t = ds.time.to_numpy().reshape((-1,1)).repeat(w.sizes['altitude_mie'], axis=1)
    mean_w = w.mean().values.item()

    if savefig is not None:
        fig=plt.figure()
        plt.scatter(w,alt,s=2, c=t)
        plt.vlines(mean_w,0,30000, colors='k', linestyles='dashed', label='Mean')
        plt.xlim(-10,10)
        plt.ylim(0,35000)
        plt.colorbar(label='Time')
        plt.xlabel('Vertical Velocity (m/s)')
        plt.ylabel('Altitude (m)')
        fig.savefig(savefig, dpi=200, bbox_inches='tight')

    print(f"COMPUTED VERTICAL VELOCITY OFFSET: {mean_w:.4f} m/s")

    return mean_w



if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="List NetCDF files in S3 within a date range")
    parser.add_argument("--bucket", default='euliaa-l2', type=str, help="S3 bucket name")
    parser.add_argument("--path", default='Andoya/L2A/20MIN', type=str, help="Main path prefix in the S3 bucket")
    parser.add_argument("--start", type=str, help="Start date in YYYY-MM-DD format")
    parser.add_argument("--end", type=str, help="End date in YYYY-MM-DD format")
    parser.add_argument("--savefig", type=str, default='./w_mean_offset.png', help="Path to save the scatter plot figure (optional)")
    args = parser.parse_args()

    bucket = args.bucket
    if bucket.startswith('s3://'):
        bucket = bucket[5:]
    if bucket.endswith('/'):
        bucket = bucket[:-1]

    path = args.path
    if path.endswith('/'):
        path = path[:-1]
    if path.startswith('/'):
        path = path[1:]
    if path.startswith('s3://'):
        print("Path should not include 's3://bucketname/' prefix.")
        exit(1)

    start_date = datetime.datetime.strptime(args.start, "%Y-%m-%d").date()
    end_date = datetime.datetime.strptime(args.end, "%Y-%m-%d").date()

    files = list_files_in_date_range(bucket, path, start_date, end_date)
    print("Computing w_mie offset from the following files:")
    for f in files:
        print(f)
    print('------------------------------------------------')
    print("\n")

    ds = xr.open_mfdataset(files,concat_dim='time',combine='nested',engine='h5netcdf')
    w_offset = compute_w_offset(ds, savefig=args.savefig)
    print("This value should be stored in the file config_nc_<campaign>.yaml in the attribute 'correction_w_offset'. \nIt will be used in the processing routine to correct w_mie, but also u_mie and v_mie.")
    print('------------------------------------------------')
    print("\n")
    ds.close()