"""
Version information for LexiScan
"""

__version__ = "0.1.0"
__build__ = "dev"
__commit__ = ""

# Version info tuple for programmatic access
VERSION_INFO = tuple(map(int, __version__.split('.')))

def get_version():
    """Get the current version string"""
    return __version__

def get_full_version():
    """Get the full version string including build info"""
    version = __version__
    if __build__ and __build__ != "release":
        version += f"-{__build__}"
    if __commit__:
        version += f"+{__commit__[:8]}"
    return version

def get_version_info():
    """Get version information as a dictionary"""
    return {
        "version": __version__,
        "build": __build__,
        "commit": __commit__,
        "full_version": get_full_version()
    }