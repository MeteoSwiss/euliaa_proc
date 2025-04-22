import datetime as dt
import os
from logging import DEBUG, FileHandler, Formatter, StreamHandler, getLogger
from logging.handlers import TimedRotatingFileHandler
from sys import stdout
from utils import get_conf
# from dl_toolbox_runner.utils.config_utils import get_log_config
# from dl_toolbox_runner.utils.file_utils import abs_file_path


# get logs config
log_config_file = ('configs/config_log.yaml')
conf = get_conf(log_config_file)


# Colors for the logs console output (Options see color_log-package)
LOG_COLORS = {
    'DEBUG': 'cyan',
    'INFO': 'white',
    'WARNING': 'yellow',
    'ERROR': 'red',
    'CRITICAL': 'red,bg_white',
    }

try:
    # TODO: solve bug with colorlog package
    import colorlog

    formatter = colorlog.ColoredFormatter(
        '%(log_color)s%(asctime)-8s %(levelname)-8s %(message)s',
        "%Y-%m-%d %H:%M:%S",
        # datefmt=None,
        reset=True,
        log_colors=LOG_COLORS,
        secondary_log_colors={},
        style='%',
    )
    get_logger = colorlog.getLogger

except Exception as e:  # noqa E841
    print(e)
    get_logger = getLogger
    formatter = Formatter(
        ' '
        '%(levelname)-8s %(message)s',
        '%Y-%m-%d %H:%M:%S',
    )


# general settings
logger = get_logger(conf['logger_name'])
logger.setLevel(DEBUG)  # set to the lowest possible level, using handler-specific levels for output


# logging to stdout
console_handler = StreamHandler(stdout)
console_formatter = formatter
console_handler.setFormatter(console_formatter)
console_handler.setLevel(conf['loglevel_stdout'])
logger.addHandler(console_handler)


# logging to file
if conf['write_logfile']:
    act_time_str = dt.datetime.now(tz=dt.timezone(dt.timedelta(0))).strftime(conf['logfile_timestamp_format'])
    log_filename = conf['logfile_basename'] + conf['logfile_ext']
    # log_filename = conf['logfile_basename'] + format(act_time_str) + conf['logfile_ext']
    log_file = str(os.path.join(conf['logfile_path'], log_filename))

    file_handler = TimedRotatingFileHandler(log_file, when='M', interval=1, utc=True)
    file_handler.suffix = "%Y-%m-%d_%H-%M-%S"
    file_handler_formatter = formatter
    file_handler.setFormatter(file_handler_formatter)
    file_handler.setLevel(conf['loglevel_file'])
    logger.addHandler(file_handler)