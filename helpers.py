import os
import re
import importlib
from typing import Any, List, Iterable

from osgeo import ogr
from qgis.PyQt.QtCore import QCoreApplication
from qgis.core import Qgis, QgsExpressionContextUtils, QgsSettings, QgsMapLayer, QgsMapLayerType, QgsVectorLayer,\
    QgsWkbTypes
from qgis.utils import iface

from .settings import SUPPORTED_STORAGE_TYPES, GROUP, FILTER_COMMENT_START, FILTER_COMMENT_STOP, LAYER_EXCEPTION_VARIABLE


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


def removeFilterFromLayer(layer: QgsVectorLayer):
    currentFilter = layer.subsetString()
    if FILTER_COMMENT_START not in currentFilter:
        return
    start_index = currentFilter.find(FILTER_COMMENT_START)
    stop_index = currentFilter.find(FILTER_COMMENT_STOP) + len(FILTER_COMMENT_STOP)
    newFilter = currentFilter[:start_index] + currentFilter[stop_index:]
    layer.setSubsetString(newFilter)


def addFilterToLayer(layer: QgsVectorLayer, filterDef: 'FilterDefinition'):
    currentFilter = layer.subsetString()
    if FILTER_COMMENT_START in currentFilter:
        removeFilterFromLayer(layer)
    currentFilter = layer.subsetString()
    connect = " AND " if currentFilter else ""
    newFilter = f'{currentFilter}{FILTER_COMMENT_START}{connect}{filterDef.filterString(layer)}{FILTER_COMMENT_STOP}'
    layer.setSubsetString(newFilter)


def getLayerGeomName(layer: QgsVectorLayer):
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
        if layer.storageType().upper() in ['GPKG', 'SQLITE'] and QgsWkbTypes.isCurvedType(layer.wkbType()):
            txt = tr('The layer "{layername}" has an unsupported geometry type: '
                     '"Circularstring", "CompoundCurve", "CurvePolygon", "MultiCurve", "MultiSurface", '
                     '"Curve" or "Surface".').format(layername=layer.name())
            iface.messageBar().pushMessage(txt, level=Qgis.Warning)
