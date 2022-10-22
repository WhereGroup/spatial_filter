## Contribute

### Update Translations

1. Update .ts file

       pylupdate5 i18n/map_filter.pro

1. Edit translations with QtLinguist in .ts file

1. Create .qm file

       lrelease i18n/map_filter_de.py

   or alternatively

       pbt translate

[Translation docs](https://docs.qgis.org/testing/en/docs/pyqgis_developer_cookbook/plugins/plugins.html#translation)