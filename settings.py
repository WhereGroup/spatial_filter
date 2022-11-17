GROUP = 'MapFilter'  # The section name for filter definitions stored in QSettings
GROUP_SYMBOL = 'MapFilterSymbol'  # Section to store symbols settings
LAYER_EXCEPTION_VARIABLE = 'MapFilterException'
SPLIT_STRING = '#!#!#'  # String used to split filter definition parameters in QSettings

FILTER_SYMBOL = {"color": "#0000ff", "outline_color": "#000000", "opacity": 0.5}

# The filter string might contain user-specific parts so we surround *our* filter
# string with text markers
FILTER_COMMENT_START = '/* MapFilter Plugin Start */'
FILTER_COMMENT_STOP = '/* MapFilter Plugin Stop */'

# The QGIS Provider Types that can be filtered by the plugin
SUPPORTED_PROVIDERS = ['postgres']
