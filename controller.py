from typing import Iterable, Optional

from PyQt5.QtCore import pyqtSignal, QObject
from qgis.core import QgsProject, QgsMapLayer, QgsMapLayerType, QgsWkbTypes, QgsGeometry
from qgis.utils import iface

from .filters import FilterDefinition, Predicate
from .helpers import getPostgisLayers, removeFilterFromLayer, addFilterToLayer, refreshLayerTree, getLayerGeomName
from .settings import FILTER_COMMENT


class Controller(QObject):
    currentFilter: Optional[FilterDefinition]
    nameChanged = pyqtSignal(str)

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent=parent)
        self.currentFilter = FilterDefinition('', '', 3452, Predicate.INTERSECTS.value)
        self.toolbarIsActive = False

    def onToggled(self, checked: bool) -> None:
        self.toolbarIsActive = checked
        if checked and not self.currentFilter:
            return
        self.updateProjectLayers(checked)

    def udpateConnectionProjectLayersAdded(self, checked):
        self.disconnectProjectLayersAdded()
        if checked:
            QgsProject.instance().layersAdded.connect(self.onLayersAdded)

    def disconnectProjectLayersAdded(self):
        try:
            QgsProject.instance().layersAdded.disconnect()
        except TypeError:
            pass

    def onLayersAdded(self, layers: Iterable[QgsMapLayer]):
        if not self.currentFilter.isValid:
            return
        for layer in getPostgisLayers(layers):
            filterCondition = self.currentFilter.filterString(getLayerGeomName(layer))
            filterString = f'{FILTER_COMMENT}{filterCondition}'
            layer.setSubsetString(filterString)

    def updateLayerFilters(self, checked: bool):
        for layer in getPostgisLayers(QgsProject.instance().mapLayers().values()):
            if not checked:
                removeFilterFromLayer(layer)
            else:
                addFilterToLayer(layer, self.currentFilter)
        refreshLayerTree()

    def updateProjectLayers(self, checked):
        self.udpateConnectionProjectLayersAdded(checked)
        self.updateLayerFilters(checked)

    def refreshFilter(self):
        if not self.currentFilter.isValid:
            self.nameChanged.emit("Kein aktiver Filter")
            return
        self.nameChanged.emit(self.currentFilter.name)
        self.updateProjectLayers(self.toolbarIsActive)

    def setFilterFromSelection(self):
        layer = iface.activeLayer()
        if not layer or not layer.type() == QgsMapLayerType.VectorLayer:
            iface.messageBar().pushInfo('', 'Polygon-Layer auswählen')
            return
        if not layer.geometryType() == QgsWkbTypes.PolygonGeometry:
            iface.messageBar().pushInfo('', 'Polygon-Layer auswählen')
            return
        if not layer.selectedFeatureCount():
            iface.messageBar().pushInfo('', 'Keine Features gewählt')
            return
        crs = iface.activeLayer().crs()
        geom = QgsGeometry.fromWkt('GEOMETRYCOLLECTION()')
        for feature in layer.selectedFeatures():
            geom = geom.combine(feature.geometry())

        self.currentFilter.srsid = crs.srsid()
        self.currentFilter.wkt = geom.asWkt()
        self.refreshFilter()