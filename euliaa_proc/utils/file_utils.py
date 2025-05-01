from pathlib import Path
import euliaa_proc

def abs_file_path(*file_path):
    """
    Make a relative file_path absolute in respect to the mwr_l12l2 project directory.
    Absolute paths wil not be changed
    """
    path = Path(*file_path)
    if path.is_absolute():
        return path
    return Path(euliaa_proc.__file__).parent.parent / path
