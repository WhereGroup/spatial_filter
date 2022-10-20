from typing import Iterable, Optional

from PyQt5.QtCore import pyqtSignal, QObject
from qgis.core import QgsProject, QgsMapLayer

from .filters import FilterDefinition, Predicate
from .helpers import getPostgisLayers, removeFilterFromLayer, addFilterToLayer, refreshLayerTree
from .settings import GEOMETRY_COLUMN, FILTER_COMMENT


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
        filterCondition = self.currentFilter.filterString(GEOMETRY_COLUMN)
        filterString = f'{FILTER_COMMENT}{filterCondition}'
        for layer in getPostgisLayers(layers):
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
