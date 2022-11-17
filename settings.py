GROUP = 'SpatialFilter'  # The section name for filter definitions stored in QSettings
GROUP_SYMBOLS = 'SpatialFilterSymbols'  # Section to store symbols settings
LAYER_EXCEPTION_VARIABLE = 'SpatialFilterException'

FILTER_FILL_COLOR = '#0000ff'
FILTER_OUTLINE_COLOR = "#000000"
FILTER_OPACITY = 0.5

# The filter string might contain user-specific parts so we surround *our* filter
# string with text markers
FILTER_COMMENT_START = '/* SpatialFilter Plugin Start */'
FILTER_COMMENT_STOP = '/* SpatialFilter Plugin Stop */'

# The QGIS Provider Types that can be filtered by the plugin
SUPPORTED_PROVIDERS = ['postgres']
