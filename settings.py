GROUP = 'MapFilter'  # The section name for filter definitions stored in QSettings
SPLIT_STRING = '#!#!#'  # String used to split filter definition parameters in QSettings

# The filter string might contain user-specific parts so we surround *our* filter
# string with text markers
FILTER_COMMENT_START = '/* MapFilter Plugin Start */'
FILTER_COMMENT_STOP = '/* MapFilter Plugin Stop */'
