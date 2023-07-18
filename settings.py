from qgis.PyQt.QtCore import QCoreApplication

def tr(message):
    return QCoreApplication.translate('@default', message)


LOCALIZED_PLUGIN_NAME = tr("Spatial Filter")  # for use in messages etc.

GROUP = 'SpatialFilter'  # The section name for filter definitions stored in QSettings
GROUP_SYMBOL = 'SpatialFilterSymbol'  # Section to store symbol settings
LAYER_EXCEPTION_VARIABLE = 'SpatialFilterException'

FILTER_SYMBOL = {"color": "#0000ff", "outline_color": "#000000", "opacity": 0.5}

# The filter string might contain user-specific parts so we surround *our* filter
# string with text markers
FILTER_COMMENT_START = '/* SpatialFilter Plugin Start */'
FILTER_COMMENT_STOP = '/* SpatialFilter Plugin Stop */'

# The QGIS Storage Types that can be filtered by the plugin
SUPPORTED_STORAGE_TYPES = ['POSTGRESQL DATABASE WITH POSTGIS EXTENSION', 'GPKG', 'SQLITE']
