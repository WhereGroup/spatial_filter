from PyQt5.QtCore import QAbstractListModel, Qt, QModelIndex

from .filters import FilterManager


DataRole = Qt.UserRole + 1


class FilterModel(QAbstractListModel):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.filters = FilterManager.loadAllFilterDefinitions()
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
