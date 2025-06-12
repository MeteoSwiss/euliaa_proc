import numpy as np
import xarray as xr
from euliaa_proc.utils.data_utils import compute_wind_speed, compute_wind_direction, compute_hor_width
from euliaa_proc.measurement import Measurement
    
c = 299792458  # Speed of light in m/s
lam = 386.0e-9  # Wavelength in meters
# theta = 30.0  # Angle of off-zenith telescopes in degrees


class EProfileMeasurement(Measurement):
    """
    Class to handle the conversion of EProfile measurements to DWL eprofile files.
    Inherits from Measurement class.
    """

    def __init__(self, config_eprofile_path, l2a_data, conf_qc_file=None):
        super().__init__(config_eprofile_path, conf_qc_file=conf_qc_file)
        self.l2a_data = l2a_data
        
    
    def load_data(self):
        """
        Load the L2A data into the measurement object.
        """
        
        l2a_zen = self.l2a_data.sel(line_of_sight=0).drop_vars("line_of_sight")
        l2a_final = l2a_zen.isel(time=[-1])
        l2a = l2a_zen.mean(dim='time').expand_dims('time')
        l2a['time']= ('time', l2a_final['time'].values)

        self.add_var({'height': (l2a.altitude_mie-l2a_zen.station_altitude).values,
            'time': l2a['time'].values,
            'nv': np.array([0, 1])
            })

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
                'height_bnds' : (('height', 'nv'), np.array([[h-l2a_zen.range_integration/2, h+l2a_zen.range_integration/2] for h in self.data.height.values])),
                'frequency' : ((), c/lam),
                'vert_res' : ((), l2a_zen.range_integration.values),
                'hor_width' : (('height',), compute_hor_width(self.data.height.values))
        })


    def subsel_altitude_range(self):
        self.data = self.data.sel(height=slice(0,self.qc_conf['MAX_ALTITUDE']))
