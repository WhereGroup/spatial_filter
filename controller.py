from typing import Iterable, Optional, List

from PyQt5.QtCore import pyqtSignal, QObject
from qgis.core import QgsProject, QgsMapLayer, QgsMapLayerType, QgsWkbTypes, QgsGeometry, QgsCoordinateReferenceSystem
from qgis.gui import QgsRubberBand
from qgis.utils import iface

from .filters import FilterDefinition, Predicate, saveFilterDefinition
from .helpers import getPostgisLayers, removeFilterFromLayer, addFilterToLayer, refreshLayerTree, hasLayerException
from .settings import FILTER_COMMENT_START, FILTER_COMMENT_STOP


class FilterController(QObject):
    currentFilter: Optional[FilterDefinition]
    rubberBands: Optional[List[QgsRubberBand]]

    filterChanged = pyqtSignal(object)

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent=parent)
        self.currentFilter = None
        self.rubberBands = []

    def removeFilter(self) -> None:
        self.currentFilter = None
        self.refreshFilter()

    def updateConnectionProjectLayersAdded(self):
        self.disconnectProjectLayersAdded()
        if self.hasValidFilter():
            QgsProject.instance().layersAdded.connect(self.onLayersAdded)

    def disconnectProjectLayersAdded(self):
        try:
            QgsProject.instance().layersAdded.disconnect(self.onLayersAdded)
        except TypeError:
            pass

    def onLayersAdded(self, layers: Iterable[QgsMapLayer]):
        if not self.currentFilter.isValid:
            return
        for layer in getPostgisLayers(layers):
            filterCondition = self.currentFilter.filterString(layer)
            filterString = f'{FILTER_COMMENT_START}{filterCondition}{FILTER_COMMENT_STOP}'
            layer.setSubsetString(filterString)

    def updateLayerFilters(self):
        for layer in getPostgisLayers(QgsProject.instance().mapLayers().values()):
            if self.hasValidFilter() and not hasLayerException(layer):
                addFilterToLayer(layer, self.currentFilter)
            else:
                removeFilterFromLayer(layer)
        refreshLayerTree()

    def updateProjectLayers(self):
        self.updateConnectionProjectLayersAdded()
        self.updateLayerFilters()

    def refreshFilter(self):
        self.filterChanged.emit(self.currentFilter)
        self.updateProjectLayers()

    def setFilterFromSelection(self):
        layer = iface.activeLayer()
        if not layer or not layer.type() == QgsMapLayerType.VectorLayer:
            iface.messageBar().pushInfo('', self.tr('Select a polygon layer'))
            return
        if not layer.geometryType() == QgsWkbTypes.PolygonGeometry:
            iface.messageBar().pushInfo('', self.tr('Select a polygon layer'))
            return
        if not layer.selectedFeatureCount():
            iface.messageBar().pushInfo('', self.tr('No features selected'))
            return
        crs = iface.activeLayer().crs()
        geom = QgsGeometry().collectGeometry([feature.geometry() for feature in layer.selectedFeatures()])

        self.currentFilter.crs = crs
        self.currentFilter.wkt = geom.asWkt()
        self.refreshFilter()

    def setFilterPredicate(self, predicate: Predicate):
        self.initFilter()
        self.currentFilter.predicate = predicate.value
        self.refreshFilter()

    def setFilterBbox(self, bbox: bool):
        self.initFilter()
        self.currentFilter.bbox = bbox
        self.refreshFilter()

    def saveCurrentFilter(self):
        saveFilterDefinition(self.currentFilter)
        self.refreshFilter()

    def initFilter(self):
        if not self.currentFilter:
            self.currentFilter = FilterDefinition.defaultFilter()

    def hasValidFilter(self):
        return self.currentFilter and self.currentFilter.isValid
