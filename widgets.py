import os

from typing import Optional, List, Iterable

from PyQt5.QtCore import QSize
from PyQt5.QtGui import QIcon, QPixmap
from PyQt5.QtWidgets import QToolBar, QWidget, QComboBox, QAction, QHBoxLayout, QPushButton
from qgis.core import QgsApplication, QgsMapLayer, QgsMapLayerType, QgsProject, QgsVectorLayer

from .helpers import refreshLayerTree
from .settings import FILTER_COMMENT, GEOMETRY_COLUMN
from .filters import Predicate, FilterDefinition, saveFilterDefinition, loadFilterDefinition


class FilterWidget(QWidget):
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent=parent)
        self.setupUi()
        self.setObjectName("mFilterWidget")


        self.filterBox.addItem("Kein aktiver Filter", None)
        self.filterBox.addItem("Filter 1", )

    def setupUi(self):
        self.setMaximumWidth(300)
        self.horizontalLayout = QHBoxLayout(self)
        self.horizontalLayout.setContentsMargins(0, 0, 0, 0)
        self.horizontalLayout.setSpacing(0)
        self.filterBox = QComboBox(self)
        self.horizontalLayout.addWidget(self.filterBox)
        self.toggleVisibilityButton = QPushButton(self)
        self.toggleVisibilityButton.setIcon(QgsApplication.getThemeIcon("/mActionHideAllLayers.svg"))
        self.toggleVisibilityButton.setIconSize(QSize(21, 21))
        self.toggleVisibilityButton.setCheckable(True)
        self.horizontalLayout.addWidget(self.toggleVisibilityButton)
        self.horizontalLayout.setStretch(0, 1)


class ToggleFilterAction(QAction):
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent=parent)
        self.setObjectName('mToggleFilterAction')
        icon = QIcon()
        pixmapOn = QPixmap(os.path.join(os.path.dirname(__file__), "icons", "filter_on.png"))
        pixmapOff = QPixmap(os.path.join(os.path.dirname(__file__), "icons", "filter_off.png"))
        icon.addPixmap(pixmapOn, QIcon.Normal, QIcon.On)
        icon.addPixmap(pixmapOff, QIcon.Normal, QIcon.Off)
        self.setIcon(icon)
        self.setCheckable(True)


class EditFilterAction(QAction):
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent=parent)
        icon = QgsApplication.getThemeIcon("/mActionToggleEditing.svg")
        self.setIcon(icon)
        self.triggered.connect(self.testStuff)

    def testStuff(self):
        wkt = 'Polygon ((790119.38837672967929393 6574913.99197626393288374, 790457.12272053339984268 ' \
               '6574913.99197626393288374, 790457.12272053339984268 6575038.15901442710310221, ' \
               '790119.38837672967929393 6575038.15901442710310221, 790119.38837672967929393 6574913.99197626393288374))'
        filter = FilterDefinition('filter1', wkt, 2105, Predicate.INTERSECTS.value)
        storageString = filter.storageString
        newFilter = FilterDefinition.fromStorageString(storageString)
        saveFilterDefinition(newFilter)
        otherFilter = loadFilterDefinition('filter1')
        for layer in QgsProject.instance().mapLayers().values():
            print(layer.name())




class FilterToolbar(QToolBar):
    currentFilter: Optional[FilterDefinition]

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent=parent)
        self.currentFilter = None
        self.currentFilter = getTestFilterDefinition()
        self.filterActions: List[QAction] = []

        self.setWindowTitle('Filter Toolbar')
        self.setObjectName('mFilterToolbar')
        self.setupUi()
        self.setupConnections()
        self.onToggled(False)

    def setupUi(self):
        self.layout().setSpacing(10)
        self.toggleFilterAction = ToggleFilterAction(self)
        self.addAction(self.toggleFilterAction)

        filterWidget = FilterWidget(self)
        self.filterActions.append(filterWidget)
        self.addWidget(filterWidget)

        self.addFilterAction(EditFilterAction(self))

        dummyAction = QAction(self)
        dummyAction.setIcon(QgsApplication.getThemeIcon("/mActionFileOpen.svg"))
        self.addFilterAction(dummyAction)

    def setupConnections(self):
        self.toggleFilterAction.toggled.connect(self.onToggled)

    def addFilterAction(self, action: QAction):
        self.filterActions.append(action)
        self.addAction(action)

    def onToggled(self, checked: bool) -> None:
        for action in self.filterActions:
            action.setEnabled(checked)
        self.connectProjectLayersAdded(checked)
        self.updateLayerFilters(checked)

    def connectProjectLayersAdded(self, checked):
        if checked:
            QgsProject.instance().layersAdded.connect(self._onLayersAdded)
        else:
            try:
                QgsProject.instance().layersAdded.disconnect()
            except TypeError:
                pass

    def _onLayersAdded(self, layers: Iterable[QgsMapLayer]):
        for layer in getPostgisLayers(layers):
            filterCondition = self.currentFilter.filterString(GEOMETRY_COLUMN)
            filterString = f'{FILTER_COMMENT}{filterCondition}'
            layer.setSubsetString(filterString)

    def updateLayerFilters(self, checked: bool):
        for layer in getPostgisLayers(QgsProject.instance().mapLayers().values()):
            if not checked:
                removePluginFilter(layer)
            else:
                addPluginFilter(layer, self.currentFilter)
        refreshLayerTree()


def getPostgisLayers(layers: Iterable[QgsMapLayer]):
    for layer in layers:
        if layer.type() != QgsMapLayerType.VectorLayer:
            continue
        if layer.providerType() != 'postgres':
            continue
        yield layer


def removePluginFilter(layer: QgsVectorLayer):
    currentFilter = layer.subsetString()
    if FILTER_COMMENT not in currentFilter:
        return
    index = currentFilter.find(FILTER_COMMENT)
    newFilter = currentFilter[:index]
    layer.setSubsetString(newFilter)


def addPluginFilter(layer: QgsVectorLayer, filter: FilterDefinition):
    currentFilter = layer.subsetString()
    if FILTER_COMMENT in currentFilter:
        removePluginFilter(layer)
    currentFilter = layer.subsetString()
    connect = " AND " if currentFilter else ""
    newFilter = f'{currentFilter}{FILTER_COMMENT}{connect}{filter.filterString(GEOMETRY_COLUMN)}'
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



