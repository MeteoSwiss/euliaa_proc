import xarray as xr
import eccodes as ec
import datetime
import numpy as np


def bufr_encode_header(ibufr, dst):
    """ Generic BUFR headers """
    # set header keys and values
    levels = dst.altitude_mie.size
    ivalues = (levels,)
    ec.codes_set_array(ibufr, 'inputExtendedDelayedDescriptorReplicationFactor',ivalues) # This sets the delayed replication factor value (used later)
    ec.codes_set(ibufr, 'edition', 4)
    ec.codes_set(ibufr, 'masterTableNumber', 0) # BUFR master table. 0: standard WMO FM 94 BUFR tables
    ec.codes_set(ibufr, 'bufrHeaderCentre', 98) # Identification of originating/generating center (Table C-11 p.1155 of WMO manual); 98: centre is ecmf; 215 is Zurich; TO DO VALUE
    ec.codes_set(ibufr, 'bufrHeaderSubCentre', 0) # Identification of originating/generating sub center (Table C-12 p.1164); 0 is no sub-center; TO DO VALUE
    ec.codes_set(ibufr, 'updateSequenceNumber', 0) #  zero for original messages and for messages containing only delayed reports; incremented for the other updates
    ec.codes_set(ibufr, 'dataCategory', 2)                    # 0: Surface data - land; 2: Vertical Soundings (other than satellite)
    ec.codes_set(ibufr, 'internationalDataSubCategory', 10)  # 10: wind profiler reports # TO DO check if better exists
    # ec.codes_set(ibufr, 'dataSubCategory', ) # for compatibility with previous versions # TO DO NEEDED? TO DO VALUE?
    ec.codes_set(ibufr, 'masterTablesVersionNumber', 40) # from Common code Tables C-0 (p. 1103 in WMO code book)
    ec.codes_set(ibufr, 'localTablesVersionNumber', 0) # Local tables define those parts of the master table which are reserved for local use; f no local table is used, the version number of the local table shall be encoded as 0.
    ec.codes_set(ibufr, 'observedData', 1)
    ec.codes_set(ibufr, 'compressedData', 0)
    if (type(dst.time.item())==int) | (type(dst.time.item())==float):
        dt = datetime.datetime.fromtimestamp(dst.time.item())
    elif (type(dst.time.item())==datetime.datetime):
        dt = dst.time.item()
    else:
        raise TypeError('dst.time should be float, int or datetime.datetime')
    ec.codes_set(ibufr, 'typicalYear', dt.year)
    ec.codes_set(ibufr, 'typicalMonth', dt.month)
    ec.codes_set(ibufr, 'typicalDay', dt.day)
    ec.codes_set(ibufr, 'typicalHour', dt.hour)
    ec.codes_set(ibufr, 'typicalMinute', dt.minute)
    ec.codes_set(ibufr, 'typicalSecond', 0)
    ec.codes_set(ibufr, 'numberOfSubsets', 1)


def bufr_encode_common_header_sequence(ibufr, dst):
    """ Common header sequence 3 01 132: 3 01 150, 3 01 001, 3 01 021, 0 07 030, 0 08 021, 3 01 011, 3 01 12, 0 02 006, 0 01 079, 0 01 085
    This sequence is used at the beginning of virtually every WMO template
    """

    # 3 01 150 (WIGOS identifiers): 0 01 150, 0 01 126, 0 01 127, 0 01 128
    wigosIdentifierSeries, wigosIssuerOfIdentifier, wigosIssueNumber, wigosLocalIdentifierCharacter = dst.wigos_station_id.split('-')
    ec.codes_set(ibufr, 'wigosIdentifierSeries', int(wigosIdentifierSeries)) # 0 01 150 -> wigos identifier series
    ec.codes_set(ibufr, 'wigosIssuerOfIdentifier', int(wigosIssuerOfIdentifier)) # 0 01 126 -> WIGOS issue of identifier
    ec.codes_set(ibufr, 'wigosIssueNumber', int(wigosIssueNumber)) # 0 01 127 -> WIGOS issue number
    ec.codes_set(ibufr, 'wigosLocalIdentifierCharacter', wigosLocalIdentifierCharacter) # 0 01 128 -> WIGOS local identifier (character)
    #-----------------
    # 3 01 001 (WMO block and station numbers): 0 01 001, 0 01 002
    if len(dst.wmo_id)<2:
        blockNumber = 0
        stationNumber = 0
    else:
        blockNumber = int(dst.wmo_id[:2])
        stationNumber = int(dst.wmo_id[2:])
    ec.codes_set(ibufr, 'blockNumber', blockNumber) # 0 01 001 -> WMO block number
    ec.codes_set(ibufr, 'stationNumber', stationNumber) # 0 01 002 -> WMO station number
    #-----------------
    # 3 01 021 (Radiosonde launch point location): 0 08 041, 3 01 122, 3 01 021, 0 07 031, 0 07 007
    # ec.codes_set(ibufr, 'dataSignificance', 1)  # 0 08 041 -> data significance, see p. 827 of WMO code book (1 = Observation site) # crashes (KeyValue not found)
    # 3 01 122: Date/time (to hundredth of second): 3 01 011, 3 01 012, 2 01 135, 2 02 130, 0 04 006, 2 02 000, 2 01 000
    # 3 01 121: Latitude / longitude (high accuracy): 0 05 001, 0 06 001
    ec.codes_set(ibufr, '#1#latitude', float(dst.station_latitude)) # 0 05 001 -> latitude (high accuracy)
    ec.codes_set(ibufr, '#1#longitude', float(dst.station_longitude)) # 0 06 001 -> longitude (high accuracy)
    # 0 07 031: height of barometer above mean sea level TO DO NEEDED?
    ec.codes_set(ibufr, '#1#height', float(dst.station_altitude)) # 0 07 007 Height
    #-------------------
    ec.codes_set(ibufr, 'heightOfStationGroundAboveMeanSeaLevel', float(dst.station_altitude)) # 0 07 030: height of station ground above mean sea level
    ec.codes_set(ibufr, '#1#timeSignificance', 25) # 0 08 021 -> time significance, see p. 820 of wmo code book
    #-------------------
    if (type(dst.time.item())==int) | (type(dst.time.item())==float):
        dt = datetime.datetime.fromtimestamp(dst.time.item())
    elif (type(dst.time.item())==datetime.datetime):
        dt = dst.time.item()
    else:
        raise TypeError('dst.time should be float, int or datetime.datetime')
    # 3 01 011: Year, month, day
    ec.codes_set(ibufr, 'year', dt.year) # 0 04 001: Year
    ec.codes_set(ibufr, 'month', dt.month) # 0 04 002: Month
    ec.codes_set(ibufr, 'day', dt.day) # 0 04 003: Day
    #-------------------
    # 3 01 012: Hour, minute
    ec.codes_set(ibufr, 'hour', dt.hour) # 0 04 004: Hour
    ec.codes_set(ibufr, 'minute', dt.minute) # 0 04 005: Minute
    #-------------------
    ec.codes_set(ibufr, 'upperAirRemoteSensingInstrumentType', 6) # 0 02 006: Upper air remote sensing instrument type -> TO DO check table p. 762, 6 is wind profiler, 7 is lidar
    ec.codes_set(ibufr, 'uniqueIdentifierForProfile', dst.instrument_id)    # 0 01 079: Unique identifier for the profile
    ec.codes_set(ibufr, 'observingPlatformManufacturerModel', dst.instrument_model) # 0 01 085: Observing platform manufacturer's model
    # ############################################




def bufr_encode_309024(ibufr, dst):
    """ This generates a valid BUFR with template 309024 (wind profiler)
     However there are some issues with setting valid heigt lat lon arrays and data quality information.
     For this reason, using for loop may be better (see other function)
     """
    # set header keys and values
    ivalues=(309024)
    """
    3 09 024 (wind profiler template):
    3 01 132,
    2 01 151, 2 02 130, 0 02 121, 2 02 000, 2 01 000,
    0 08 021, 0 04 025,
    1 09 000, 0 31 002,
    0 07 007,
    3 01 021,
    0 11 003, 0 11 004, 0 33 002, 0 11 006, 0 33 002, 0 10 071, 0 27 079
    """
    # create the bufr structure
    ec.codes_set(ibufr, 'unexpandedDescriptors', ivalues)

    # set data keys and values
    #################
    # common header sequence 3 01 132: 3 01 150, 3 01 001, 3 01 021, 0 07 030, 0 08 021, 3 01 011, 3 01 12, 0 02 006, 0 01 079, 0 01 085
    #-----------------
    # 3 01 150 (WIGOS identifiers): 0 01 150, 0 01 126, 0 01 127, 0 01 128
    ec.codes_set(ibufr, 'wigosIdentifierSeries', 0) # 0 01 150 -> wigos identifier series: TO DO VALUE
    ec.codes_set(ibufr, 'wigosIssuerOfIdentifier', 20000) # 0 01 126 -> WIGOS issue of identifier: TO DO VALUE
    ec.codes_set(ibufr, 'wigosIssueNumber', 0) # 0 01 127 -> WIGOS issue number: TO DO VALUE
    ec.codes_set(ibufr, 'wigosLocalIdentifierCharacter', '06610') # 0 01 128 -> WIGOS local identifier (character)
    #-----------------
    # 3 01 001 (WMO block and station numbers): 0 01 001, 0 01 002
    ec.codes_set(ibufr, 'blockNumber', 6) # 0 01 001 -> WMO block number TO DO VALUE
    ec.codes_set(ibufr, 'stationNumber', 610) # 0 01 002 -> WMO station number TO DO VALUE
    #-----------------
    # 3 01 021 (Radiosonde launch point location): 0 08 041, 3 01 122, 3 01 021, 0 07 031, 0 07 007
    # ec.codes_set(ibufr, 'dataSignificance', 1)  # 0 08 041 -> data significance, see p. 827 of WMO code book (1 = Observation site) # crashes (KeyValue not found)
    # 3 01 122: Date/time (to hundredth of second): 3 01 011, 3 01 012, 2 01 135, 2 02 130, 0 04 006, 2 02 000, 2 01 000
    # 3 01 121: Latitude / longitude (high accuracy): 0 05 001, 0 06 001
    ec.codes_set(ibufr, 'latitude', float(dst.station_latitude)) # 0 05 001 -> latitude (high accuracy)
    ec.codes_set(ibufr, 'longitude', float(dst.station_longitude)) # 0 06 001 -> longitude (high accuracy)
    # 0 07 031: height of barometer above mean sea level TO DO NEEDED?
    ec.codes_set(ibufr, '#1#height', 200) # 0 07 007 Height TO DO NEEDED?
    #-------------------
    ec.codes_set(ibufr, 'heightOfStationGroundAboveMeanSeaLevel', 200) # 0 07 030: height of station ground above mean sea level
    ec.codes_set(ibufr, '#1#timeSignificance', 25) # 0 08 021 -> time significance, see p. 820 of wmo code book
    #-------------------
    # 3 01 011: Year, month, day
    ec.codes_set(ibufr, 'year', datetime.datetime.fromtimestamp(dst.time.item()*1e-9).year) # 0 04 001: Year
    ec.codes_set(ibufr, 'month', datetime.datetime.fromtimestamp(dst.time.item()*1e-9).month) # 0 04 002: Month
    ec.codes_set(ibufr, 'day', datetime.datetime.fromtimestamp(dst.time.item()*1e-9).day) # 0 04 003: Day
    #-------------------
    # 3 01 012: Hour, minute
    ec.codes_set(ibufr, 'hour', datetime.datetime.fromtimestamp(dst.time.item()*1e-9).hour) # 0 04 004: Hour
    ec.codes_set(ibufr, 'minute', datetime.datetime.fromtimestamp(dst.time.item()*1e-9).minute) # 0 04 005: Minute
    #-------------------
    ec.codes_set(ibufr, 'upperAirRemoteSensingInstrumentType', 6) # 0 02 006: Upper air remote sensing instrument type -> TO DO check table p. 762, 6 is wind profiler, 7 is lidar
    ec.codes_set(ibufr, 'uniqueIdentifierForProfile', 'EULIAAKL')    # 0 01 079: Unique identifier for the profile -> TO DO CHECK VALUE
    ec.codes_set(ibufr, 'observingPlatformManufacturerModel','EULIAA' ) # 0 01 085: Observing platform manufacturer's model
    ############################################


    ec.codes_set(ibufr, '#2#timeSignificance', 2) # 0 08 021 -> time significance, see p. 820 of wmo code book (2: Time averaged)
    ec.codes_set(ibufr, 'timePeriod', 1) # 0 04 025 -> Time period indicates the duration in minutes over which the measurements have been averaged

    # 1 09 000 -> Delayed replication of 9 descriptors (defined before)
    # ec.codes_set(ibufr, 'extendedDelayedReplicationFactor', ivalues) # 0 31 002: Extended delayed description replication factor, TO DO CHECK NEEDED / REDUNDANT? apparently this is read only

    ec.codes_set_array(ibufr, '#2#height', dst.altitude_mie.values[:-1]) # 0 07 007 Height TO DO NEEDED HERE??

    # 3 01 021 (Radiosonde launch point location): 0 08 041, 3 01 122, 3 01 021, 0 07 031, 0 07 007
    # ec.codes_set(ibufr, 'dataSignificance', 4)  # 0 08 041 -> data significance, see p. 827 of WMO code book (4 = Surface obs) # crashes (KeyValue not found)
    # 3 01 122: Date/time (to hundredth of second): 3 01 011, 3 01 012, 2 01 135, 2 02 130, 0 04 006, 2 02 000, 2 01 000
    # 3 01 121: Latitude / longitude (high accuracy): 0 05 001, 0 06 001
    # ec.codes_set(ibufr, 'latitude', float(dst.station_latitude)) # 0 05 001 -> latitude (high accuracy)
    # ec.codes_set(ibufr, 'longitude', float(dst.station_longitude)) # 0 06 001 -> longitude (high accuracy)
    ec.codes_set_array(ibufr, 'latitude', dst.latitude_mie.values[:,0]) # 0 05 001 -> latitude (high accuracy)
    ec.codes_set_array(ibufr, 'longitude', dst.latitude_mie.values[:,0]*0. + float(dst.station_longitude)) # 0 06 001 -> longitude (high accuracy)
    # 0 07 031: height of barometer above mean sea level TO DO NEEDED?
    # ec.codes_set_array(ibufr, 'height', dst.altitude_mie.values[:-1]) # 0 07 007 Height

    ec.codes_set_array(ibufr,'u', dst.u_mie.values[:-1]) # 0 11 003 -> u-component
    ec.codes_set_array(ibufr, 'v', dst.v_mie.values[:-1]) # 0 11 004 -> v-component
    ec.codes_set(ibufr, 'qualityInformation', 0.)#*np.ones(len(dst.altitude_mie)))   # 0 33 002 -> Quality information (0: Data not suspect, 1: Data suspect, 2: Reserved, 3: Quality information not given)
    ec.codes_set_array(ibufr, 'w', dst.w_mie.values[:-1]) # 0 11 006 -> w-component
    ec.codes_set(ibufr, 'qualityInformation', 3)   # 0 33 002 -> Quality information (0: Data not suspect, 1: Data suspect, 2: Reserved, 3: Quality information not given)
    ec.codes_set(ibufr, 'verticalResolution', dst.vertical_resolution.item())#*np.ones(len(dst.altitude_mie))) # 0 10 071 -> vertical resolution
    ec.codes_set(ibufr, 'horizontalWidthOfSampledVolume', 1.)#*np.ones(len(dst.altitude_mie)))  # 027079 -> horizontal width of sampled volume (m) TO DO CHECK VALUE

    ec.codes_set(ibufr, 'pack', 1)  # Required to encode the keys back in the data section



def bufr_encode_forloop_309024(ibufr,dst):
    """ This generates a valid BUFR with template 309024 (wind profiler).

    3 09 024 (wind profiler template):
    3 01 132,
    2 01 151, 2 02 130, 0 02 121, 2 02 000, 2 01 000,
    0 08 021, 0 04 025,
    1 09 000, 0 31 002,
    0 07 007,
    3 01 021,
    0 11 003, 0 11 004, 0 33 002, 0 11 006, 0 33 002, 0 10 071, 0 27 079

     """
    # create the bufr structure using the template code
    ivalues=(309024)
    ec.codes_set(ibufr, 'unexpandedDescriptors', ivalues)


    # # set data keys and values
    # #################
    # # common header sequence 3 01 132: 3 01 150, 3 01 001, 3 01 021, 0 07 030, 0 08 021, 3 01 011, 3 01 12, 0 02 006, 0 01 079, 0 01 085
    # #-----------------
    bufr_encode_common_header_sequence(ibufr, dst)
    # ############################################

    # Frequency sequence: 2 01 151, 2 02 130, 0 02 121, 2 02 000, 2 01 000, TO DO implement sequence
    ############################################

    ec.codes_set(ibufr, '#2#timeSignificance', 2) # 0 08 021 -> time significance, see p. 820 of wmo code book (2: Time averaged)
    ec.codes_set(ibufr, 'timePeriod', 1) # 0 04 025 -> Time period indicates the duration in minutes over which the measurements have been averaged

    # 1 09 000 -> Delayed replication of 9 descriptors (defined before)
    # ec.codes_set(ibufr, 'extendedDelayedReplicationFactor', ivalues) # 0 31 002: Extended delayed description replication factor? -> NO apparently this is read only

    altitudes = dst.altitude_mie.values
    u_v_flag = (dst.u_v_flag.values>=1).astype('int')
    w_flag = (dst.w_mie_flag.values>=1).astype('int')
    temperature_flag = (dst.temperature_int_flag.values>=1).astype('int')

    for i in range(len(altitudes)):
        # print(i)
        ec.codes_set(ibufr,'#%d#height'%(i+1), altitudes[i]) # 0 07 007 Height
        ec.codes_set(ibufr,'#%d#latitude'%(i+2), float(dst.station_latitude)) # 0 05 001 -> latitude (high accuracy)
        ec.codes_set(ibufr,'#%d#longitude'%(i+2), float(dst.station_longitude)) # 0 06 001 -> longitude (high accuracy)
        ec.codes_set(ibufr,'#%d#u'%(i+1), float(dst.u_mie[i].values)) # 0 11 003 -> u-component
        ec.codes_set(ibufr,'#%d#v'%(i+1), float(dst.v_mie[i].values)) # 0 11 004 -> v-component
        ec.codes_set(ibufr,'#%d#qualityInformation'%(2*i+1), u_v_flag[i])  # 0 33 002 -> Quality information (0: Data not suspect, 1: Data suspect, 2: Reserved, 3: Quality information not given) TO DO adjust with flag in NC
        ec.codes_set(ibufr,'#%d#w'%(i+1), float(dst.w_mie[i].values)) # 0 11 006 -> w-component
        ec.codes_set(ibufr,'#%d#qualityInformation'%(2*i+2), w_flag[i]) # 0 33 002 -> Quality information
        ec.codes_set(ibufr,'#%d#verticalResolution'%(i+1), dst.vertical_resolution.item()) # 0 10 071 -> vertical resolution
        ec.codes_set(ibufr,'#%d#horizontalWidthOfSampledVolume'%(i+1), temperature_flag[i])  # 027079 -> horizontal width of sampled volume (m) TO DO CHECK VALUE

    ec.codes_set(ibufr, 'pack', 1)  # Required to encode the keys back in the data section



def bufr_encode_forloop(ibufr,dst):
    """
    This generates a BUFR file using the following sequence.
    Basically like wind profiler + temperature and associated quality descr.

    301132, # common header sequence
    201138, 202126, 2121, 202000, 201000, # mean freq
    8021, 4025, # time significance and time period
    111000, 31002, # delayed replication (11 parameters)
    7007, 301021, # height and lat/lon
    11003, 11004, 33002, 11006, 33002, 12001, 33002, # atm vars
    10071, 27079, # vert res and horiz width
    """

    # create the bufr structure using the template code
    ivalues=(301132, 201138, 202126, 2121, 202000, 201000, 8021, 4025, 111000, 31002,
         7007, 301021,
         11003, 11004, 33002, 11006, 33002, 12001, 33002,
         10071, 27079,)
    ec.codes_set_array(ibufr, 'unexpandedDescriptors', ivalues)

    # set data keys and values
    #################
    # common header sequence 3 01 132: 3 01 150, 3 01 001, 3 01 021, 0 07 030, 0 08 021, 3 01 011, 3 01 12, 0 02 006, 0 01 079, 0 01 085
    #-----------------
    bufr_encode_common_header_sequence(ibufr, dst)

    ############################################

    # Frequency sequence: 2 01 151, 2 02 130, 0 02 121, 2 02 000, 2 01 000, TO DO implement sequence
    ############################################

    ec.codes_set(ibufr, '#2#timeSignificance', 2) # 0 08 021 -> time significance, see p. 820 of wmo code book (2: Time averaged)
    ec.codes_set(ibufr, 'timePeriod', int(dst.time_integration/60)) # 0 04 025 -> Time period indicates the duration in minutes over which the measurements have been averaged

    # 1 09 000 -> Delayed replication of 9 descriptors (defined before)
    # ec.codes_set(ibufr, 'extendedDelayedReplicationFactor', ivalues) # 0 31 002: Extended delayed description replication factor -> this is read only

    altitudes = dst.altitude_mie.values
    for i in range(len(altitudes)):
        ec.codes_set(ibufr,'#%d#height'%(i+1), altitudes[i]) # 0 07 007 Height
        ec.codes_set(ibufr,'#%d#latitude'%(i+2), float(dst.station_latitude)) # 0 05 001 -> latitude (high accuracy)
        ec.codes_set(ibufr,'#%d#longitude'%(i+2), float(dst.station_longitude)) # 0 06 001 -> longitude (high accuracy)
        ec.codes_set(ibufr,'#%d#u'%(i+1), float(dst.u_mie[i].values)) # 0 11 003 -> u-component
        ec.codes_set(ibufr,'#%d#v'%(i+1), float(dst.v_mie[i].values)) # 0 11 004 -> v-component
        ec.codes_set(ibufr,'#%d#qualityInformation'%(3*i+1), 0)  # 0 33 002 -> Quality information (0: Data not suspect, 1: Data suspect, 2: Reserved, 3: Quality information not given) TO DO adjust with flag in NC
        ec.codes_set(ibufr,'#%d#w'%(i+1), float(dst.w_mie[i].values)) # 0 11 006 -> w-component
        ec.codes_set(ibufr,'#%d#qualityInformation'%(3*i+2), 1) # 0 33 002 -> Quality information TO DO based on flag
        ec.codes_set(ibufr,'#%d#airTemperature'%(i+1), float(dst.temperature_int[i])) # 0 12 001 -> Temperature / air temperature
        ec.codes_set(ibufr,'#%d#qualityInformation'%(3*i+3), 2) # 0 33 002 -> Quality information TO DO based on flag
        ec.codes_set(ibufr,'#%d#verticalResolution'%(i+1), dst.vertical_resolution.item()) # 0 10 071 -> vertical resolution
        ec.codes_set(ibufr,'#%d#horizontalWidthOfSampledVolume'%(i+1), 1.)  # 027079 -> horizontal width of sampled volume (m) TO DO CHECK VALUE

    ec.codes_set(ibufr, 'pack', 1)  # Required to encode the keys back in the data section


if __name__=='__main__':

    inputFilename = '/home/bia/euliaa_postproc/data/Test_profile_NC.nc'
    outFilename = '/home/bia/euliaa_postproc/data/Test_profile_NC2BUFR_forloop_notemplate_newenv.bufr'

    # coder = xr.coders.CFDatetimeCoder(time_unit="s")
    ds = xr.open_dataset(inputFilename,decode_times=False)#, decode_times=coder) # Otherwise xarray converts time to ns - this works only for xarray >

    # following steps: if the file is the full LV1
    if False:
        ds = ds.isel(time=0)
        ds = ds.sel(altitude_mie=slice(0,60e3))
        ds = ds.sel(field_of_view='zenith')
        # Subselection with valid data (following BUFR min/max) - TO DO implement in prior QC / LV1 stripped file
        ds.w_mie[(ds.w_mie < -40.96)| (ds.w_mie > 40.96)]=np.nan
        ds.v_mie[(ds.v_mie < -409.6)|(ds.v_mie > 409.6)] = np.nan
        ds.v_mie[(ds.u_mie < -409.6)|(ds.u_mie > 409.6)] = np.nan
        ds.temperature_int[(ds.temperature_int > 409.5) | (ds.temperature_int < 0)]=np.nan

    # convert to BUFR
    fout = open(outFilename, "wb")
    bid = ec.codes_bufr_new_from_samples('BUFR4')
    bufr_encode_header(bid,ds)

    # bufr_encode_forloop_309024(bid,ds)
    # bufr_encode_309024(bid, ds)
    bufr_encode_forloop(bid,ds)

    ec.codes_write(bid,fout)
