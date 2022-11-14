from typing import Iterable, Optional, List

from PyQt5.QtCore import pyqtSignal, QObject
from qgis.core import QgsProject, QgsMapLayer, QgsMapLayerType, QgsWkbTypes, QgsGeometry, QgsCoordinateReferenceSystem
from qgis.gui import QgsRubberBand
from qgis.utils import iface

from .filters import FilterDefinition, Predicate, FilterManager
from .helpers import getPostgisLayers, removeFilterFromLayer, addFilterToLayer, refreshLayerTree, hasLayerException
from .settings import FILTER_COMMENT_START, FILTER_COMMENT_STOP


class FilterController(QObject):
    currentFilter: Optional[FilterDefinition]
    rubberBands: Optional[List[QgsRubberBand]]

    filterChanged = pyqtSignal(FilterDefinition)

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent=parent)
        self.currentFilter = FilterDefinition(
            self.tr('New Filter'), '', QgsCoordinateReferenceSystem(), Predicate.INTERSECTS, False
        )
        self.rubberBands = []
        self.toolbarIsActive = False

    def onToggled(self, checked: bool) -> None:
        self.toolbarIsActive = checked
        if checked and not self.currentFilter.isValid:
            return
        self.updateProjectLayers(checked)

    def updateConnectionProjectLayersAdded(self, checked):
        self.disconnectProjectLayersAdded()
        if checked:
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

    def updateLayerFilters(self, checked: bool):
        for layer in getPostgisLayers(QgsProject.instance().mapLayers().values()):
            if checked and not hasLayerException(layer):
                addFilterToLayer(layer, self.currentFilter)
            else:
                removeFilterFromLayer(layer)
        refreshLayerTree()

    def updateProjectLayers(self, checked):
        self.updateConnectionProjectLayersAdded(checked)
        self.updateLayerFilters(checked)

    def refreshFilter(self):
        self.filterChanged.emit(self.currentFilter)
        if self.currentFilter.isValid:
            self.updateProjectLayers(self.toolbarIsActive)

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
        self.currentFilter.predicate = predicate.value
        self.refreshFilter()

    def setFilterBbox(self, bbox: bool):
        self.currentFilter.bbox = bbox
        self.refreshFilter()

    def saveCurrentFilter(self):
        FilterManager().saveFilterDefinition(self.currentFilter)
        self.refreshFilter()
