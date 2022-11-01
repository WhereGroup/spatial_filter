from typing import Any, List, Iterable

from qgis.core import QgsSettings, QgsMapLayer, QgsMapLayerType, QgsVectorLayer, QgsMessageLog, Qgis

from .settings import GROUP, FILTER_COMMENT_START, FILTER_COMMENT_STOP


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
    pass


def getPostgisLayers(layers: Iterable[QgsMapLayer]):
    for layer in layers:
        if layer.type() != QgsMapLayerType.VectorLayer:
            continue
        if layer.providerType() != 'postgres':
            continue
        yield layer


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
    return layer.dataProvider().uri().geometryColumn()


def getTestFilterDefinition():
    from .filters import Predicate, FilterDefinition
    name = 'museumsinsel'
    srsid = 3452  # 4326
    predicate = Predicate.INTERSECTS.value
    wkt = 'Polygon ((13.38780495720708963 52.50770539474106613, 13.41583642354597039 52.50770539474106613, ' \
          '13.41583642354597039 52.52548910505585411, 13.38780495720708963 52.52548910505585411, ' \
          '13.38780495720708963 52.50770539474106613))'
    return FilterDefinition(name, wkt, srsid, predicate)
