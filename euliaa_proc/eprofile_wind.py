import numpy as np
import xarray as xr
from euliaa_proc.utils.data_utils import compute_wind_speed, compute_wind_direction, compute_hor_width
from euliaa_proc.measurement import Measurement
from euliaa_proc.log import logger

c = 299792458  # Speed of light in m/s
lam_default = 386  # Wavelength in nanometers
# theta = 30.0  # Angle of off-zenith telescopes in degrees


class EProfileWindMeasurement(Measurement):
    """
    Class to handle the conversion of EProfile measurements to DWL eprofile files.
    Inherits from Measurement class.
    """

    def __init__(self, config_eprofile_wind_path, l2a_data, conf_qc_file=None):
        logger.info('Initializing E-Profile wind measurement object.')
        super().__init__(config_eprofile_wind_path, conf_qc_file=conf_qc_file)
        self.l2a_data = l2a_data
        logger.info(f'Config for E-Profile wind measurement loaded from {config_eprofile_wind_path}')
        self.lam = self.conf['variables']['instrument_wavelength']['value'] if 'instrument_wavelength' in self.conf['variables'] else lam_default
        self.lam = self.lam * 1e-9  # Convert from nm to m
        logger.info(f'Wavelength set to {self.lam} m for E-Profile wind measurement.')
    
    def load_data(self, time_idx_list=[-1]):
        """
        Load the L2A data into the measurement object.
        """
        l2a_zen = self.l2a_data.sel(line_of_sight=0).drop_vars("line_of_sight")
        l2a_final = l2a_zen.isel(time=time_idx_list) # Default is to take the last time index only
        l2a = l2a_final.mean(dim='time').expand_dims('time')
        l2a['time']= ('time', l2a_final['time'].values)

        self.add_var({'height': (l2a.altitude_mie-l2a_zen.station_altitude).values,
            'time': l2a['time'].values,
            'nv': np.array([0, 1])
            })
        
        if 'EPROFILE_SET_INVALID_TO_NAN' in self.qc_conf and self.qc_conf['EPROFILE_SET_INVALID_TO_NAN']:
            for var in l2a.variables.keys():
                if not (f'{var}_flag' in l2a.variables.keys()):
                    continue
                # logger.info(f'Setting invalid data to NaN for variable {var}')
                l2a[var] = l2a[var].where(l2a[var+'_flag']==0, np.nan)

        # print(l2a.height_bnds.dims)
        vert_res=l2a_zen.range_integration.values if 'range_integration' in l2a_zen.keys() else np.mean(self.data['height'].values[1:]-self.data['height'].values[:-1])
        self.add_var({'config': ((), ''),
                'wspeed': (('time', 'height'), compute_wind_speed(l2a.u_mie, l2a.v_mie).values),
                'qwind' : (('time', 'height'), xr.where(((l2a.u_mie_flag==0) & (l2a.v_mie_flag==0) & (l2a.w_mie_flag==0)), 1, 0).values),
                'qu' : (('time', 'height'), xr.where(l2a.u_mie_flag==0, 1, 0).values),
                'qv' : (('time', 'height'), xr.where(l2a.v_mie_flag==0, 1, 0).values),
                'qw' : (('time', 'height'), xr.where(l2a.w_mie_flag==0, 1, 0).values),
                'errwspeed' : (('time', 'height'), np.sqrt(l2a.u_mie_err**2 + l2a.v_mie_err**2).values),
                'u' : (('time', 'height'), l2a.u_mie.values),
                'erru' : (('time', 'height'), l2a.u_mie_err.values),
                'v' : (('time', 'height'), l2a.v_mie.values),
                'errv' : (('time', 'height'), l2a.v_mie_err.values),
                'w' : (('time', 'height'), l2a.w_mie.values),
                'errw' : (('time', 'height'), l2a.w_mie_err.values),
                'wdir' : (('time', 'height'), compute_wind_direction(l2a.u_mie, l2a.v_mie).values),
                'errwdir' : (('time', 'height'), np.zeros_like(l2a['w_mie'].values)),
                'r2' : (('time', 'height'), np.zeros_like(l2a['w_mie'].values)),
                'nvrad' : (('time', 'height'), np.zeros_like(l2a['w_mie'].values)),
                'cn' : (('time', 'height'), np.zeros_like(l2a['w_mie'].values)),
                'lat' : ((), l2a_zen.station_latitude.values),
                'lon' : ((), l2a_zen.station_longitude.values),
                'zsl' : ((), l2a_zen.station_altitude.values),
                'time_bnds' : (('time', 'nv'), l2a.time_bnds.values),
                # l2a_dwl['time_bnds' : (('time', 'nv'), np.array([[l2a_zen.time[0].values, l2a_zen.time[-1].values]]))
                'height_bnds' : (('height', 'nv'), l2a_zen.height_bnds.values), #np.array([[h-l2a_zen.range_integration/2, h+l2a_zen.range_integration/2] for h in self.data.height.values])),
                'frequency' : ((), c/self.lam),
                'instrument_wavelength' : ((), self.lam*1e9), # in nm
                'vert_res' : ((), vert_res),
                'hor_width' : (('height',), compute_hor_width(self.data.height.values))
        })


    def subsel_altitude_range(self):
        self.data = self.data.sel(height=slice(0,self.qc_conf['MAX_ALTITUDE']))
        if 'EPROFILE_SKIP_EVERY_SECOND_ALTITUDE' in self.qc_conf and self.qc_conf['EPROFILE_SKIP_EVERY_SECOND_ALTITUDE']:
            self.data = self.data.isel(height=slice(None, None, 2))
            logger.info("Every second altitude level skipped for E-Profile wind output.")