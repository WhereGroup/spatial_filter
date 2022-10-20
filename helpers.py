from typing import Any, List, Iterable

from qgis.core import QgsSettings, QgsMapLayer, QgsMapLayerType, QgsVectorLayer

from .settings import GROUP, FILTER_COMMENT, GEOMETRY_COLUMN


def saveValue(key: str, value: Any):
    settings = QgsSettings()
    settings.beginGroup(GROUP)
    settings.setValue(key, value)
    settings.endGroup()


def readValue(key: str, defaultValue: Any = None) -> Any:
    settings = QgsSettings()
    settings.beginGroup(GROUP)
    value = settings.value(key, defaultValue)
    settings.endGroup()
    return value


def allValues(defaultValue: Any = None) -> List[Any]:
    settings = QgsSettings()
    settings.beginGroup(GROUP)
    values = [settings.value(key, defaultValue) for key in settings.allKeys()]
    settings.endGroup()
    return values


def removeValue(key: str) -> None:
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
    if FILTER_COMMENT not in currentFilter:
        return
    index = currentFilter.find(FILTER_COMMENT)
    newFilter = currentFilter[:index]
    layer.setSubsetString(newFilter)


def addFilterToLayer(layer: QgsVectorLayer, filterDef: 'FilterDefinition'):
    currentFilter = layer.subsetString()
    if FILTER_COMMENT in currentFilter:
        removeFilterFromLayer(layer)
    currentFilter = layer.subsetString()
    connect = " AND " if currentFilter else ""
    newFilter = f'{currentFilter}{FILTER_COMMENT}{connect}{filterDef.filterString(GEOMETRY_COLUMN)}'
    layer.setSubsetString(newFilter)


def getTestFilterDefinition():
    from .filters import Predicate, FilterDefinition
    name = 'museumsinsel'
    srsid = 3452
    predicate = Predicate.INTERSECTS.value
    wkt = 'Polygon ((13.38780495720708963 52.50770539474106613, 13.41583642354597039 52.50770539474106613, ' \
          '13.41583642354597039 52.52548910505585411, 13.38780495720708963 52.52548910505585411, ' \
          '13.38780495720708963 52.50770539474106613))'
    return FilterDefinition(name, wkt, srsid, predicate)
