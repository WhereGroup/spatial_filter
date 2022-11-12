from typing import Any

from PyQt5.QtCore import QAbstractListModel, Qt, QModelIndex, QVariant, QAbstractTableModel, QAbstractItemModel
from PyQt5.QtGui import QStandardItemModel, QStandardItem

from qgis.core import QgsMessageLog, Qgis, QgsMapLayerProxyModel, QgsProject,  QgsFeatureSource, QgsApplication

from .helpers import hasLayerException
from .settings import SUPPORTED_PROVIDERS
from .filters import FilterManager


DataRole = Qt.UserRole + 1


class FilterModel(QAbstractListModel):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.filters = FilterManager.loadAllFilterDefinitions()
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


def getLayerModel():
    model = QStandardItemModel()
    for layer in [layerNode.layer() for layerNode in QgsProject.instance().layerTreeRoot().findLayers()]:
        item = QStandardItem(layer.name())
        item.setData(layer, role=DataRole)
        item.setFlags(Qt.ItemIsUserCheckable)
        if layer.providerType() in SUPPORTED_PROVIDERS:
            item.setEnabled(True)
        else:
            item.setEnabled(False)
        if hasLayerException(layer):
            item.setCheckState(Qt.Checked)
        else:
            item.setCheckState(Qt.Unchecked)
        model.appendRow(item)
    return model


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


class LayerModel1(QgsMapLayerProxyModel):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.headers = ['Layer', self.tr('Do not filter'), self.tr('Description')]

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = ...) -> Any:
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return self.headers[section]
        return QVariant()

    def data(self, index: QModelIndex, role: int = ...) -> Any:
        if not index.isValid():
            return QVariant()
        if index.column() == 0:
            return super().data(index, role=role)
        if index.column() == 1 and role == Qt.DisplayRole:
            return 'Checkbox'
        if index.column() == 2:
            layerIndex = self.index(row=index.row(), column=0)
            return super().data(layerIndex, role=Qt.UserRole)
        return QVariant()

    def columnCount(self, parent: QModelIndex = ...) -> int:
        return len(self.headers)


class LayerModel2(QAbstractTableModel):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.layers = list(QgsProject.instance().mapLayers().values())
        self.headers = [self.tr('Do not filter'), 'Layer', 'Status']

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = ...) -> Any:
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return self.headers[section]
        return QVariant()

    def display(self, index):
        mapping = {
            0: 'checkbox',
            1: self.layers[index.row()].name(),
            2: 'Layer wird nicht unterstützt' if self.layers[index.row()].providerType() == 'postgres' else '',
        }
        return mapping[index.column()]

    def data(self, index, role=Qt.DisplayRole):
        if role == Qt.DisplayRole:
            return self.display(index)
        elif role == DataRole:
            return self.layers[index.row()]
        return QVariant()

    def rowCount(self, parent=QModelIndex()):
        return len(self.layers)

    def columnCount(self, parent: QModelIndex = ...) -> int:
        return len(self.headers)