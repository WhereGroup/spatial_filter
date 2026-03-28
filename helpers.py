import os
import re
import importlib
from typing import Any, List, Iterable

from osgeo import ogr
from qgis.PyQt.QtCore import QCoreApplication
from qgis.core import (
    Qgis, 
    QgsExpressionContextUtils, 
    QgsSettings, 
    QgsMapLayer, 
    QgsMapLayerType, 
    QgsVectorLayer,
    QgsWkbTypes, 
    QgsGeometry, 
    QgsCoordinateReferenceSystem,     
    QgsCoordinateTransform, 
    QgsProject
)

if Qgis.QGIS_VERSION_INT > 33600:
    from qgis.core import QgsSensorThingsUtils

from qgis.utils import iface

from .settings import (
    SUPPORTED_STORAGE_TYPES, 
    GROUP, 
    FILTER_COMMENT_START, 
    FILTER_COMMENT_STOP,
    FILTER_COMMENT_START_SENSORTHINGS, 
    FILTER_COMMENT_STOP_SENSORTHINGS,
    LAYER_EXCEPTION_VARIABLE, 
    LOCALIZED_PLUGIN_NAME, 
    SENSORTHINGS_STORAGE_TYPE
)

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .filters import FilterDefinition

def tr(message):
    return QCoreApplication.translate('@default', message)


def saveSettingsValue(key: str, value: Any):
    settings = QgsSettings()
    settings.beginGroup(GROUP)
    settings.setValue(key, value)
    settings.endGroup()


def readSettingsValue(key: str, defaultValue: Any = None) -> Any:
    settings = QgsSettings()
    settings.beginGroup(GROUP)
    value = settings.value(key, defaultValue)
    settings.endGroup()
    return value


def allSettingsValues(defaultValue: Any = None) -> List[Any]:
    settings = QgsSettings()
    settings.beginGroup(GROUP)
    values = [settings.value(key, defaultValue) for key in settings.allKeys()]
    settings.endGroup()
    return values


def removeSettingsValue(key: str) -> None:
    settings = QgsSettings()
    settings.beginGroup(GROUP)
    settings.remove(key)
    settings.endGroup()


def refreshLayerTree() -> None:
    """Refreshes the layer tree to update the filter icons.
    We use hide() and show() as there is no native refresh method
    """
    tree = iface.layerTreeView()
    tree.hide()
    tree.show()


def getSupportedLayers(layers: Iterable[QgsMapLayer]):
    for layer in layers:
        if isLayerSupported(layer):
            yield layer


def isLayerSupported(layer: QgsMapLayer):
    if layer.type() != QgsMapLayerType.VectorLayer:
        return False
    if layer.storageType().upper() not in SUPPORTED_STORAGE_TYPES:
        return False
    if not layer.isSpatial():
        return False
    return True


def getFilterStartStopString(layer: QgsVectorLayer) -> tuple[str, str]:
    if layer.storageType() == SENSORTHINGS_STORAGE_TYPE:
        return FILTER_COMMENT_START_SENSORTHINGS, FILTER_COMMENT_STOP_SENSORTHINGS
    else:
        return FILTER_COMMENT_START, FILTER_COMMENT_STOP

def removeFilterFromLayer(layer: QgsVectorLayer):
    # sensorthings filter does not support inline comments (FILTER_COMMENT_START)
    # The workaround for this is a string that always evals to true and is only used with this plugin
    FILTER_START_STRING, FILTER_STOP_STRING = getFilterStartStopString(layer)
    currentFilter = layer.subsetString()
    if FILTER_START_STRING not in currentFilter:
        return
    start_index = currentFilter.find(FILTER_START_STRING)
    stop_index = currentFilter.find(FILTER_STOP_STRING) + len(FILTER_STOP_STRING)
    newFilter = currentFilter[:start_index] + currentFilter[stop_index:]
    newFilter = newFilter.rstrip(' and ')
    layer.setSubsetString(newFilter)


def addFilterToLayer(layer: QgsVectorLayer, filterDef: 'FilterDefinition'):
    currentFilter = layer.subsetString()
    FILTER_START_STRING, FILTER_STOP_STRING = getFilterStartStopString(layer)
    if FILTER_START_STRING in currentFilter:
        removeFilterFromLayer(layer)
    
    currentFilter = layer.subsetString()

    connect = " AND " if currentFilter else ""
    if layer.storageType() == SENSORTHINGS_STORAGE_TYPE:
        connect = connect.lower() # SensorThings only supports lowercase 'and'
        newFilter = f'{currentFilter}{connect}{FILTER_START_STRING}{filterDef.filterString(layer)}{FILTER_STOP_STRING}'
    else:
        newFilter = f'{currentFilter}{FILTER_START_STRING}{connect}{filterDef.filterString(layer)}{FILTER_STOP_STRING}'
    layer.setSubsetString(newFilter)




def reproject_geometry(geometry: QgsGeometry, source_crs_epsg: int, target_crs_epsg: int) -> QgsGeometry:
    """
    Reproject a QgsGeometry from a source CRS to a target CRS.

    Args:
        geometry (QgsGeometry): The QgsGeometry to reproject.
        source_crs_epsg (int): The EPSG code of the source CRS.
        target_crs_epsg (int): The EPSG code of the target CRS.

    Returns:
        str: The reprojected geometry.
    """
    source_crs = QgsCoordinateReferenceSystem(source_crs_epsg)
    target_crs = QgsCoordinateReferenceSystem(target_crs_epsg)
    if source_crs == target_crs: 
        return geometry
    transform = QgsCoordinateTransform(source_crs, target_crs, QgsProject.instance())
    geometry.transform(transform)
    return geometry



def getLayerGeomName(layer: QgsVectorLayer):
    if layer.storageType() == SENSORTHINGS_STORAGE_TYPE:
        entity_str = layer.dataProvider().uri().param('entity')
        entity_type = QgsSensorThingsUtils.stringToEntity(entity_str)
        geom_field = QgsSensorThingsUtils.geometryFieldForEntityType(entity_type)
        return geom_field
    return layer.dataProvider().uri().geometryColumn() or getLayerGeomNameOgr(layer)


def getLayerGeomNameOgr(layer: QgsVectorLayer):
    source = layer.source()

    # layer source *might* include pipe character and then the layername
    # but when created from a processing algorithm, it might not
    if "|" in source:
        split_source = source.split('|')
        filepath = split_source[0]
        lname = split_source[1].split('=')[1]
    else:
        # assuming we simply got a full path to the file and nothing else
        filepath = layer.source()
        lname = os.path.splitext(os.path.basename(filepath))[0]

    conn = ogr.Open(filepath)
    ogrLayer = conn.GetLayerByName(lname)
    columnName = ogrLayer.GetGeometryColumn()
    ogrLayer = None
    conn = None
    return columnName


def hasLayerException(layer: QgsVectorLayer) -> bool:
    return QgsExpressionContextUtils.layerScope(layer).variable(LAYER_EXCEPTION_VARIABLE) == 'true'


def setLayerException(layer: QgsVectorLayer, exception: bool) -> None:
    QgsExpressionContextUtils.setLayerVariable(layer, LAYER_EXCEPTION_VARIABLE, exception)


def matchFormatString(format_str: str, s: str) -> dict:
    """Match s against the given format string, return dict of matches.

    We assume all of the arguments in format string are named keyword arguments (i.e. no {} or
    {:0.2f}). We also assume that all chars are allowed in each keyword argument, so separators
    need to be present which aren't present in the keyword arguments (i.e. '{one}{two}' won't work
    reliably as a format string but '{one}-{two}' will if the hyphen isn't used in {one} or {two}).

    We raise if the format string does not match s.

    Example:
    fs = '{test}-{flight}-{go}'
    s = fs.format('first', 'second', 'third')
    match_format_string(fs, s) -> {'test': 'first', 'flight': 'second', 'go': 'third'}

    source: https://stackoverflow.com/questions/10663093/use-python-format-string-in-reverse-for-parsing
    """

    # First split on any keyword arguments, note that the names of keyword arguments will be in the
    # 1st, 3rd, ... positions in this list
    tokens = re.split(r'\{(.*?)\}', format_str)
    keywords = tokens[1::2]

    # Now replace keyword arguments with named groups matching them. We also escape between keyword
    # arguments so we support meta-characters there. Re-join tokens to form our regexp pattern
    tokens[1::2] = map(u'(?P<{}>.*)'.format, keywords)
    tokens[0::2] = map(re.escape, tokens[0::2])
    pattern = ''.join(tokens)

    # Use our pattern to match the given string, raise if it doesn't match
    matches = re.match(pattern, s)
    if not matches:
        raise Exception("Format string did not match")

    # Return a dict with all of our keywords and their values
    return {x: matches.group(x) for x in keywords}


def class_for_name(module_name: str, class_name: str):
    """Loads a class via its name as string.

    Source: https://stackoverflow.com/questions/1176136/convert-string-to-python-class-object
    """
    # load the module, will raise ImportError if module cannot be loaded
    m = importlib.import_module(module_name)
    # get the class, will raise AttributeError if class cannot be found
    c = getattr(m, class_name)
    return c


def warnAboutCurveGeoms(layers: Iterable[QgsMapLayer]):
    for layer in layers:
        if not isLayerSupported(layer):
            continue
        # additional exceptions due to missing support for curve geometries in ogr's spatialite-based spatial filtering
        # https://github.com/WhereGroup/spatial_filter/issues/1
        if layer.storageType().upper() in ['GPKG', 'SQLITE'] and QgsWkbTypes.isCurvedType(layer.wkbType()):
            txt = tr(
                'The {layerType} layer {layerName!r} has a geometry type ({geometryType}) that is not supported by the '
                '{pluginName} plugin and will be ignored for filtering.'
            ).format(
                layerName=layer.name(),
                layerType=layer.storageType(),
                pluginName=LOCALIZED_PLUGIN_NAME,
                geometryType=QgsWkbTypes.displayString(layer.wkbType()),
            )
            iface.messageBar().pushWarning(LOCALIZED_PLUGIN_NAME, txt)


def warnAboutQgisBugProjectSaving():
    """Show a warning because of https://github.com/qgis/QGIS/issues/55975"""
    if Qgis.QGIS_VERSION_INT < 33404:
        txt = tr(
            "QGIS &lt; 3.34.4 has a bug breaking the saving of (active) filters to projects "
            '(<a href="https://github.com/WhereGroup/spatial_filter/issues/24">Info</a>)'
        ).format(pluginName=LOCALIZED_PLUGIN_NAME)
        iface.messageBar().pushWarning(LOCALIZED_PLUGIN_NAME, txt)
