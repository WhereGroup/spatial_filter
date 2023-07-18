from typing import Iterable, Optional, List

from qgis.PyQt.QtCore import pyqtSignal, QObject
from qgis.core import Qgis, QgsProject, QgsMapLayer, QgsMapLayerType, QgsWkbTypes, QgsGeometry
from qgis.gui import QgsRubberBand
from qgis.utils import iface

from .maptool import PolygonTool
from .filters import FilterDefinition, Predicate
from .helpers import getSupportedLayers, removeFilterFromLayer, addFilterToLayer, refreshLayerTree, hasLayerException, \
    warnAboutCurveGeoms
from .settings import FILTER_COMMENT_START


class FilterController(QObject):
    currentFilter: Optional[FilterDefinition]
    rubberBands: Optional[List[QgsRubberBand]]

    filterChanged = pyqtSignal(object)

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent=parent)
        self.currentFilter = None
        self.rubberBands = []
        self.connectSignals()

    def connectSignals(self):
        # Many thanks to *Thomas B* for suggesting that the layersAdded signal fires so quickly that editing
        # the layer filter will happen before the data is actually requested, at least for PostGIS
        QgsProject.instance().layersAdded.connect(self.onLayersAdded)

    def disconnectSignals(self):
        QgsProject.instance().layersAdded.disconnect(self.onLayersAdded)

    def removeFilter(self):
        self.currentFilter = None
        self.refreshFilter()

    def onLayersAdded(self, layers: Iterable[QgsMapLayer]):
        warnAboutCurveGeoms(layers)
        if self.hasValidFilter():
            # Apply the filter to added layers or loaded project
            for layer in getSupportedLayers(layers):
                addFilterToLayer(layer, self.currentFilter)
        else:
            # Look for saved filters to use with the plugin (possible when project was loaded)
            for layer in getSupportedLayers(layers):
                if FILTER_COMMENT_START in layer.subsetString():
                    self.setFilterFromLayer(layer)
                    return

    def setFilterFromLayer(self, layer):
        filterDefinition = FilterDefinition.fromFilterString(layer.subsetString())
        self.currentFilter = filterDefinition
        self.refreshFilter()

    def updateLayerFilters(self):
        for layer in getSupportedLayers(QgsProject.instance().mapLayers().values()):
            if self.hasValidFilter() and not hasLayerException(layer):
                addFilterToLayer(layer, self.currentFilter)
            else:
                removeFilterFromLayer(layer)
        refreshLayerTree()

    def updateProjectLayers(self):
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
        geom = QgsGeometry().unaryUnion([feature.geometry() for feature in layer.selectedFeatures()])
        self.initFilter()
        self.currentFilter.name = self.tr('New filter from selection')
        self.currentFilter.crs = crs
        self.currentFilter.wkt = geom.asWkt()
        self.refreshFilter()

    def setFilterPredicate(self, predicate: Predicate):
        self.currentFilter.predicate = predicate.value
        self.refreshFilter()

    def setFilterBbox(self, bbox: bool):
        self.currentFilter.bbox = bbox
        self.refreshFilter()

    def initFilter(self):
        self.currentFilter = FilterDefinition.defaultFilter()

    def hasValidFilter(self):
        return self.currentFilter and self.currentFilter.isValid

    def startSketchingTool(self):
        self.mapTool = PolygonTool()
        self.mapTool.sketchFinished.connect(self.onSketchFinished)
        iface.mapCanvas().setMapTool(self.mapTool)

    def stopSketchingTool(self):
        iface.mapCanvas().unsetMapTool(self.mapTool)
        self.mapTool.deactivate()

    def onSketchFinished(self, geometry: QgsGeometry):
        self.stopSketchingTool()
        if not geometry.isGeosValid():
            iface.messageBar().pushMessage(self.tr("Geometry is not valid"), level=Qgis.Warning, duration=3)
            return
        self.initFilter()
        self.currentFilter.name = self.tr('New filter from sketch')
        self.currentFilter.wkt = geometry.asWkt()
        self.currentFilter.crs = QgsProject.instance().crs()
        self.refreshFilter()
