import pandas as pd
import yaml
import numpy as np


def extract_dims(df, i):
    dims_str_csv = df.iloc[i].dim.split('(')[1].split(')')[0]
    if len(dims_str_csv)>0:
        dims = dims_str_csv.split(',')
        dims = [dims_str.replace(' ','') for dims_str in dims]
        dims = [dims_str for dims_str in dims if len(dims_str)>0]
    else:
        dims = ''
    return dims

def extract_fill_value(df,i):
    fv = df.iloc[i]['_FillValue'].item()
    if fv!=fv:
        fv = None
    return fv


def extract_attributes(df,i,ignore_keys=[], end_valid_key=None):
    attrs = {}
    for key in df.keys()[:end_valid_key]:
        if key in ignore_keys:
            continue
        if type(df.iloc[i][key])==float:
            if np.isnan(df.iloc[i][key]):
                continue
        else:
            attrs[key] = df.iloc[i][key]
    return attrs

def extract_hdf5_info(df,i):
    hdf5_group = df.iloc[i]['original_hdf5_group']
    hdf5_var_name = df.iloc[i]['original_hdf5_var_name']
    if not(type(hdf5_group) == str):
        hdf5_group = None
        hdf5_var_name = None
    elif ',' in hdf5_var_name:
        hdf5_var_name = hdf5_var_name.split(', ')
    return {'hdf5_group':hdf5_group, 'hdf5_var_name':hdf5_var_name}


if __name__=='__main__':
    # User input

    csv_file = '/home/bia/Data/IAP/NetCDF_variables_option2.csv'
    yaml_output = 'config_nc_vars_option2.yml'
    SKIP_VAR_NAME = 'TBD'
    END_VALID_KEY = -2 # the last two columns in the csv should be ignored
    IGNORE_KEYS = ['name', 'dim', 'type', '_FillValue', 'original_hdf5', 'original_hdf5_group', 'original_hdf5_var_name','value']


    df = pd.read_csv(csv_file,sep=';',skiprows=11)
    metadata_dict = {}
    for i, var_name in enumerate(df.name):
        if (var_name==SKIP_VAR_NAME) | (var_name is np.nan):
            continue
        metadata_dict[var_name] = {'name': var_name,
                                'dim': extract_dims(df, i),
                                'type': df.iloc[i]['type'],
                                '_FillValue': extract_fill_value(df, i),
                                'original_hdf5': extract_hdf5_info(df,i),
                                'attributes': extract_attributes(df,i,ignore_keys = IGNORE_KEYS,end_valid_key=END_VALID_KEY)
                                }
        if ('value' in df.iloc[i].keys()) and (not(df.iloc[i]['value'] is None) and (not((df.iloc[i]['value'] is np.nan)))):
            value = df.iloc[i]['value']
            metadata_dict[var_name]['value'] = value if not (',' in value) else value.split(', ')

    with open(yaml_output, 'w') as outfile:
        yaml.dump({'variables':metadata_dict}, outfile,sort_keys=False)
