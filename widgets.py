import os

from typing import Optional, List, Iterable, Union

from PyQt5 import uic
from PyQt5.QtCore import QSize, Qt, pyqtSignal
from PyQt5.QtGui import QIcon, QPixmap
from PyQt5.QtWidgets import (
    QToolBar,
    QWidget,
    QAction,
    QHBoxLayout,
    QPushButton,
    QLineEdit,
    QDialog,
    QVBoxLayout,
    QSizePolicy,
    QDialogButtonBox, QListWidget
)
from qgis.gui import QgsExtentWidget
from qgis.core import QgsApplication, QgsGeometry, QgsMapLayer, QgsMapLayerType, QgsProject, QgsVectorLayer
from qgis.utils import iface

from .models import FilterModel, DataRole
from .helpers import refreshLayerTree
from .settings import FILTER_COMMENT, GEOMETRY_COLUMN
from .filters import Predicate, FilterDefinition, saveFilterDefinition, deleteFilterDefinition


class FilterWidget(QWidget):
    currentFilter: Optional[FilterDefinition]
    lineEditFilterName: QLineEdit

    filterChanged = pyqtSignal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent=parent)
        self.setObjectName("mFilterWidget")
        self.setupUi()
        self.setupConnections()

    def setupUi(self):
        self.setMaximumWidth(300)
        self.horizontalLayout = QHBoxLayout(self)
        self.horizontalLayout.setContentsMargins(0, 0, 0, 0)
        self.horizontalLayout.setSpacing(0)
        self.lineEditFilterName = QLineEdit(self)
        self.horizontalLayout.addWidget(self.lineEditFilterName)
        self.toggleVisibilityButton = QPushButton(self)
        visibilityIcon = QIcon()
        pixmapOn = QgsApplication.getThemeIcon("/mActionShowAllLayers.svg").pixmap(QSize(21, 21))
        pixmapOff = QgsApplication.getThemeIcon("/mActionHideAllLayers.svg").pixmap(QSize(21, 21))
        visibilityIcon.addPixmap(pixmapOn, QIcon.Normal, QIcon.On)
        visibilityIcon.addPixmap(pixmapOff, QIcon.Normal, QIcon.Off)
        self.toggleVisibilityButton.setIcon(visibilityIcon)
        self.toggleVisibilityButton.setIconSize(QSize(21, 21))
        self.toggleVisibilityButton.setCheckable(True)
        self.horizontalLayout.addWidget(self.toggleVisibilityButton)
        self.horizontalLayout.setStretch(0, 1)

    def setupConnections(self):
        self.toggleVisibilityButton.toggled.connect(self.onFilterVisibilityToggled)
        self.lineEditFilterName.textChanged.connect(self.onTextChanged)

    def setFilter(self, filterDef: FilterDefinition):
        self.currentFilter = filterDef
        if filterDef is None:
            self.lineEditFilterName.setText("Kein aktiver Filter")
            return
        self.lineEditFilterName.setText(filterDef.name)
        self.filterChanged.emit()

    def onFilterVisibilityToggled(self, checked: bool):
        print(checked)

    def onTextChanged(self, text):
        self.currentFilter.name = text


class ExtentDialog(QDialog):
    def __init__(self, filterWidget: FilterWidget, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent=parent)
        self.filterWidget = filterWidget
        self.setObjectName("mExtentDialog")
        self.setWindowTitle("Set rectangular filter")
        self.setupUi()
        self.extentWidget.setOriginalExtent(iface.mapCanvas().extent(), QgsProject.instance().crs())
        #self.extentWidget.setCurrentExtent(iface.mapCanvas().extent(), QgsProject.instance().crs())
        #self.extentWidget.setOutputCrs(QgsProject.instance().crs())
        self.extentWidget.setMapCanvas(iface.mapCanvas())

    def setupUi(self):
        self.resize(700, 80)
        sizePolicy = QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.sizePolicy().hasHeightForWidth())
        self.setSizePolicy(sizePolicy)
        self.verticalLayout = QVBoxLayout(self)
        self.verticalLayout.setObjectName("verticalLayout")
        self.extentWidget = QgsExtentWidget(self)
        self.extentWidget.setObjectName("mExtentGroupBox")
        self.verticalLayout.addWidget(self.extentWidget)
        self.buttonBox = QDialogButtonBox(self)
        self.buttonBox.setOrientation(Qt.Horizontal)
        self.buttonBox.setStandardButtons(QDialogButtonBox.Cancel | QDialogButtonBox.Ok)
        self.verticalLayout.addWidget(self.buttonBox)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)

    def getExtent(self):
        return self.extentWidget.outputExtent()

    def getCrs(self):
        return self.extentWidget.outputCrs()

    def accept(self) -> None:
        if self.extentWidget.isValid():
            filter = self.filterWidget.currentFilter
            filter.wkt = QgsGeometry.fromRect(self.getExtent()).asWkt()
            filter.srsid = self.getCrs().srsid()
            self.filterWidget.setFilter(filter)
        super().accept()


FORM_CLASS, _ = uic.loadUiType(os.path.join(os.path.dirname(__file__), 'ui', 'named_filters_dialog.ui'))


class ManageFiltersDialog(QDialog, FORM_CLASS):
    lineEditActiveFilter: QLineEdit
    listViewNamedFilters: QListWidget
    buttonName: QPushButton
    buttonApply: QPushButton
    buttonDelete: QPushButton
    buttonClose: QPushButton

    def __init__(self, filterWidget: FilterWidget, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent=parent)
        self.filterWidget = filterWidget
        self.setupUi(self)
        self.setupConnections()
        self.setModel()

    def setupConnections(self):
        self.buttonApply.clicked.connect(self.onApplyClicked)
        self.buttonDelete.clicked.connect(self.onDeleteClicked)

    def setModel(self):
        self.filterModel = FilterModel()
        self.listViewNamedFilters.setModel(self.filterModel)
        self.listViewNamedFilters.selectionModel().selectionChanged.connect(self.onSelectionChanged)
        self.onSelectionChanged()

    def onSelectionChanged(self):
        hasSelection = self.listViewNamedFilters.selectionModel().hasSelection()
        self.buttonApply.setEnabled(hasSelection)
        self.buttonDelete.setEnabled(hasSelection)

    def onApplyClicked(self):
        selectedIndex = self.listViewNamedFilters.selectedIndexes()[0]
        filterDefinition = self.filterModel.data(index=selectedIndex, role=DataRole)
        self.filterWidget.setFilter(filterDefinition)

    def onDeleteClicked(self):
        selectedIndex = self.listViewNamedFilters.selectedIndexes()[0]
        filterDefinition = self.filterModel.data(index=selectedIndex, role=DataRole)
        deleteFilterDefinition(filterDefinition)
        self.setModel()


class ToggleFilterAction(QAction):
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent=parent)
        self.setObjectName('mToggleFilterAction')
        self.setToolTip('Toggle filter on/off')
        icon = QIcon()
        pixmapOn = QPixmap(os.path.join(os.path.dirname(__file__), "icons", "filter_on.png"))
        pixmapOff = QPixmap(os.path.join(os.path.dirname(__file__), "icons", "filter_off.png"))
        icon.addPixmap(pixmapOn, QIcon.Normal, QIcon.On)
        icon.addPixmap(pixmapOff, QIcon.Normal, QIcon.Off)
        self.setIcon(icon)
        self.setCheckable(True)


class TestAction(QAction):
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent=parent)
        icon = QgsApplication.getThemeIcon("/mActionToggleEditing.svg")
        self.setIcon(icon)
        self.triggered.connect(self.testStuff)

    def testStuff(self):
        wkt = 'Polygon ((790119.38837672967929393 6574913.99197626393288374, 790457.12272053339984268 ' \
               '6574913.99197626393288374, 790457.12272053339984268 6575038.15901442710310221, ' \
               '790119.38837672967929393 6575038.15901442710310221, 790119.38837672967929393 6574913.99197626393288374))'
        filter = FilterDefinition('aaasortiermich!', wkt, 2105, Predicate.DISJOINT.value)
        storageString = filter.storageString
        newFilter = FilterDefinition.fromStorageString(storageString)
        saveFilterDefinition(newFilter)


class FilterToolbar(QToolBar):
    filterWidget: FilterWidget

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent=parent)
        self.setWindowTitle('Filter Toolbar')
        self.setObjectName('mFilterToolbar')
        self.setupUi()
        self.setupConnections()
        self.onToggled(False)

        self.filterWidget.setFilter(getTestFilterDefinition())

    def setupUi(self):
        self.layout().setSpacing(10)
        self.toggleFilterAction = ToggleFilterAction(self)
        self.addAction(self.toggleFilterAction)

        self.filterWidget = FilterWidget(self)
        self.addWidget(self.filterWidget)

        self.filterFromExtentAction = QAction(self)
        self.filterFromExtentAction.setIcon(QgsApplication.getThemeIcon('/mActionAddBasicRectangle.svg'))
        self.filterFromExtentAction.setToolTip('Set rectangular filter geometry')
        self.addAction(self.filterFromExtentAction)

        self.saveCurrentFilterAction = QAction(self)
        self.saveCurrentFilterAction.setIcon(QgsApplication.getThemeIcon('/mActionFileSave.svg'))
        self.saveCurrentFilterAction.setToolTip('Save current filter')
        self.addAction(self.saveCurrentFilterAction)

        self.manageFiltersAction = QAction(self)
        self.manageFiltersAction.setIcon(QgsApplication.getThemeIcon('/mActionFileOpen.svg'))
        self.manageFiltersAction.setToolTip('Manage filters')
        self.addAction(self.manageFiltersAction)

        self.addAction(TestAction(self))

    def setupConnections(self):
        self.toggleFilterAction.toggled.connect(self.onToggled)
        self.filterFromExtentAction.triggered.connect(self.setFilterFromExtent)
        self.filterWidget.filterChanged.connect(self.updateFilter)
        self.manageFiltersAction.triggered.connect(self.manageFilters)
        self.saveCurrentFilterAction.triggered.connect(self.saveCurrentFilter)

    def updateFilter(self):
        self.onToggled(self.toggleFilterAction.isChecked())

    def onToggled(self, checked: bool) -> None:
        self.udpateConnectionProjectLayersAdded(checked)
        self.updateLayerFilters(checked)

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
        for layer in getPostgisLayers(layers):
            filterCondition = self.filterWidget.currentFilter.filterString(GEOMETRY_COLUMN)
            filterString = f'{FILTER_COMMENT}{filterCondition}'
            layer.setSubsetString(filterString)

    def updateLayerFilters(self, checked: bool):
        for layer in getPostgisLayers(QgsProject.instance().mapLayers().values()):
            if not checked:
                removePluginFilter(layer)
            else:
                addPluginFilter(layer, self.filterWidget.currentFilter)
        refreshLayerTree()

    def setFilterFromExtent(self):
        dlg = ExtentDialog(self.filterWidget, parent=self)
        dlg.show()

    def manageFilters(self):
        dlg = ManageFiltersDialog(self.filterWidget, parent=self)
        dlg.exec()

    def saveCurrentFilter(self):
        saveFilterDefinition(self.filterWidget.currentFilter)


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


def addPluginFilter(layer: QgsVectorLayer, filterDef: FilterDefinition):
    currentFilter = layer.subsetString()
    if FILTER_COMMENT in currentFilter:
        removePluginFilter(layer)
    currentFilter = layer.subsetString()
    connect = " AND " if currentFilter else ""
    newFilter = f'{currentFilter}{FILTER_COMMENT}{connect}{filterDef.filterString(GEOMETRY_COLUMN)}'
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


