# Contribute

Contributors are welcome to extend the plugin's features further. Please fork the repository and make a pull request if your feature is ready. Just creating issues also helps to maintain the plugin working. Please, provide a meaningful example.
## Update Translations

1. Update .ts file

       pylupdate5 i18n/map_filter.pro

1. Edit translations with QtLinguist in .ts file

1. Create .qm file

       lrelease i18n/map_filter_de.py

   or alternatively

       pbt translate

[Translation docs](https://docs.qgis.org/testing/en/docs/pyqgis_developer_cookbook/plugins/plugins.html#translation)