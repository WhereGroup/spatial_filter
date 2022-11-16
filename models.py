from typing import Any

from PyQt5.QtCore import QAbstractListModel, Qt, QModelIndex
from PyQt5.QtGui import QStandardItemModel, QStandardItem

from qgis.core import QgsMessageLog, Qgis, QgsProject,  QgsFeatureSource, QgsApplication

from .filters import loadAllFilterDefinitions
from .helpers import hasLayerException
from .settings import SUPPORTED_PROVIDERS


DataRole = Qt.UserRole + 1


class FilterModel(QAbstractListModel):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.filters = loadAllFilterDefinitions()
        self.filters.sort()
        QgsMessageLog.logMessage(f"{len(self.filters)} filter definitions loaded.", "FilterPlugin", level=Qgis.Info)

    def data(self, index, role=Qt.DisplayRole):
        if role == Qt.DisplayRole:
            return self.filters[index.row()].name
        elif role == DataRole:
            return self.filters[index.row()]

    def rowCount(self, parent=QModelIndex()):
        return len(self.filters)

    def removeRows(self, row: int, count: int = 1, parent: QModelIndex = ...) -> bool:
        self.beginRemoveRows(QModelIndex(), row, row + count - 1)
        self.filters = self.filters[:row] + self.tableData[row + count:]
        self.endRemoveRows()
        return True


class LayerModel(QStandardItemModel):
    def __init__(self, parent=None):
        super(LayerModel, self).__init__(parent)

        for layer in [layerNode.layer() for layerNode in QgsProject.instance().layerTreeRoot().findLayers()]:
            item = QStandardItem(layer.name())
            item.setData(layer, role=DataRole)
            item.setFlags(Qt.ItemIsUserCheckable)
            if layer.providerType() in SUPPORTED_PROVIDERS:
                item.setEnabled(True)
                if layer.dataProvider().hasSpatialIndex() == QgsFeatureSource.SpatialIndexNotPresent:
                    item.setToolTip(self.tr('Layer has no spatial index'))
                    item.setIcon(QgsApplication.getThemeIcon('/mIconWarning.svg'))
            else:
                item.setEnabled(False)
                item.setToolTip(self.tr('Layer type is not supported'))
            if hasLayerException(layer):
                item.setCheckState(Qt.Checked)
            else:
                item.setCheckState(Qt.Unchecked)
            self.appendRow(item)

