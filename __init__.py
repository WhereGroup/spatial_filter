"""
/***************************************************************************
 SpatialFilter
                                 A QGIS plugin
 This plugin applies spatial filters to layers for performance and efficiency.

 Base was generated by Plugin Builder: http://g-sherman.github.io/Qgis-Plugin-Builder/
                              -------------------
        begin                : 2022-10-16
        copyright            : (C) 2022 Wheregroup GmbH
        email                : info@wheregroup.com
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
 This script initializes the plugin, making it known to QGIS.
"""


# noinspection PyPep8Naming
def classFactory(iface):  # pylint: disable=invalid-name
    """Load MapFilter class from file MapFilter.

    :param iface: A QGIS interface instance.
    :type iface: QgsInterface
    """
    #
    from .spatial_filter import SpatialFilter
    return SpatialFilter(iface)
