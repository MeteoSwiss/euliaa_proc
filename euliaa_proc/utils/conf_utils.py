import yaml

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
