from qgis.PyQt.QtCore import QAbstractListModel, Qt, QModelIndex
from qgis.PyQt.QtGui import QStandardItemModel, QStandardItem

from qgis.core import QgsProject,  QgsFeatureSource, QgsApplication, QgsMapLayer

from .filters import loadAllFilterDefinitions
from .helpers import hasLayerException, isLayerSupported


DataRole = Qt.UserRole + 1


class FilterModel(QAbstractListModel):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.filters = loadAllFilterDefinitions()
        self.filters.sort()

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

            if isLayerSupported(layer):
                item.setEnabled(True)
                if layer.dataProvider().hasSpatialIndex() == QgsFeatureSource.SpatialIndexPresence.SpatialIndexNotPresent:
                    item.setToolTip(self.tr('Layer has no spatial index'))
                    item.setIcon(QgsApplication.getThemeIcon('/mIconWarning.svg'))
            else:
                item.setEnabled(False)
                item.setToolTip(self.tr('Layer type is not supported'))
            self.initItemCheckState(layer, item)
            self.appendRow(item)

    def initItemCheckState(self, layer: QgsMapLayer, item: QStandardItem):
        item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
        if hasLayerException(layer):
            item.setCheckState(Qt.Checked)
        else:
            item.setCheckState(Qt.Unchecked)
