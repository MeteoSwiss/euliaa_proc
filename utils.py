import yaml
import numpy as np

def get_conf(file):
    """get config dictionary from yaml files"""
    with open(file) as f:
        conf = yaml.load(f, Loader=yaml.FullLoader)
    return conf

def correct_dim_scalar_fields(conf):
    """scalar fields are assigned dimension=()"""
    for var in conf.keys():
        if conf[var]['dim']=='':
            conf[var]['dim']=()

def check_var_in_ds(ds, var):
    if type(var)==list:
        return np.all([v in ds.keys() for v in var])
    else:
        return (var in ds.keys())

# def compute_lat_lon_array(altitude, )
