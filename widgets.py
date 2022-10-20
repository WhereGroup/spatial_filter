import os
from dataclasses import replace

from typing import Optional

from PyQt5 import uic
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QIcon, QPixmap
from PyQt5.QtWidgets import (
    QToolBar,
    QWidget,
    QAction,
    QPushButton,
    QLineEdit,
    QDialog,
    QVBoxLayout,
    QSizePolicy,
    QDialogButtonBox, QListWidget, QMenu, QActionGroup, QLabel, QFrame, QInputDialog
)
from qgis.gui import QgsExtentWidget
from qgis.core import QgsApplication, QgsGeometry, QgsMapLayerType, QgsProject, QgsWkbTypes
from qgis.utils import iface

from .controller import Controller
from .models import FilterModel, DataRole
from .filters import Predicate, saveFilterDefinition, deleteFilterDefinition


class ExtentDialog(QDialog):
    def __init__(self, controller: Controller, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent=parent)
        self.controller = controller
        self.setObjectName("mExtentDialog")
        self.setWindowTitle("Set rectangular filter")
        self.setupUi()
        self.extentWidget.setOriginalExtent(iface.mapCanvas().extent(), QgsProject.instance().crs())
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
            self.controller.currentFilter.wkt = QgsGeometry.fromRect(self.getExtent()).asWkt()
            self.controller.currentFilter.srsid = self.getCrs().srsid()
            self.controller.refreshFilter()
        super().accept()


FORM_CLASS, _ = uic.loadUiType(os.path.join(os.path.dirname(__file__), 'ui', 'named_filters_dialog.ui'))


class ManageFiltersDialog(QDialog, FORM_CLASS):
    lineEditActiveFilter: QLineEdit
    listViewNamedFilters: QListWidget
    buttonName: QPushButton
    buttonApply: QPushButton
    buttonDelete: QPushButton
    buttonClose: QPushButton

    def __init__(self, controller, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent=parent)
        self.controller = controller
        self.setupUi(self)
        self.lineEditActiveFilter.setText(self.controller.currentFilter.name)
        self.lineEditActiveFilter.setReadOnly(True)
        self.setupConnections()
        self.setModel()

    def setupConnections(self):
        self.buttonName.clicked.connect(self.onNameClicked)
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
        filterDefinitionCopy = replace(filterDefinition)
        self.lineEditActiveFilter.setText(filterDefinitionCopy.name)
        self.controller.currentFilter = filterDefinitionCopy
        self.controller.refreshFilter()

    def onDeleteClicked(self):
        selectedIndex = self.listViewNamedFilters.selectedIndexes()[0]
        filterDefinition = self.filterModel.data(index=selectedIndex, role=DataRole)
        deleteFilterDefinition(filterDefinition)
        self.setModel()

    def onNameClicked(self):
        currentText = self.lineEditActiveFilter.text()
        text, ok = QInputDialog.getText(self, 'Change Name', 'New Name:', echo=QLineEdit.Normal, text=currentText)
        if not ok:
            return
        self.lineEditActiveFilter.setText(text)
        self.controller.currentFilter.name = text
        self.controller.refreshFilter()


class PredicateAction(QPushButton):
    predicateChanged = pyqtSignal(Predicate)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent=parent)
        self.setObjectName('mPredicateSelectAction')
        self.setToolTip('Chose geometric predicate')
        self.setIcon(QgsApplication.getThemeIcon('/mActionOptions.svg'))
        self.menu = QMenu(parent=parent)
        self.predicateActionGroup = QActionGroup(self)
        self.predicateActionGroup.setExclusive(True)
        for predicate in Predicate:
            action = QAction(self.menu)
            action.setCheckable(True)
            action.setObjectName(f'mAction{predicate.name}')
            action.setText(predicate.name)
            action.predicate = predicate
            action.triggered.connect(self.onPredicateChanged)
            self.predicateActionGroup.addAction(action)
        self.menu.addActions(self.predicateActionGroup.actions())
        self.setMenu(self.menu)

    def onPredicateChanged(self):
        self.predicateChanged.emit(self.getPredicate())

    def getPredicate(self) -> Predicate:
        currentAction = self.predicateActionGroup.checkedAction()
        if currentAction:
            return currentAction.predicate


class FilterToolbar(QToolBar):

    def __init__(self, controller: Controller, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent=parent)
        self.controller = controller
        self.setWindowTitle('Filter Toolbar')
        self.setObjectName('mFilterToolbar')
        self.setupUi()
        self.setupConnections()
        self.controller.onToggled(False)

    def setupUi(self):
        self.layout().setSpacing(5)
        self.toggleFilterAction = QAction(self)
        self.toggleFilterAction.setToolTip('Toggle filter on/off')
        icon = QIcon()
        pixmapOn = QPixmap(os.path.join(os.path.dirname(__file__), "icons", "filter_on.png"))
        pixmapOff = QPixmap(os.path.join(os.path.dirname(__file__), "icons", "filter_off.png"))
        icon.addPixmap(pixmapOn, QIcon.Normal, QIcon.On)
        icon.addPixmap(pixmapOff, QIcon.Normal, QIcon.Off)
        self.toggleFilterAction.setIcon(icon)
        self.toggleFilterAction.setCheckable(True)
        self.addAction(self.toggleFilterAction)

        self.labelFilterName = QLabel(self)
        self.labelFilterName.setFrameShape(QFrame.Panel)
        self.labelFilterName.setFrameShadow(QFrame.Sunken)
        self.labelFilterName.setMinimumWidth(150)
        self.addWidget(self.labelFilterName)

        self.toggleVisibilityAction = QAction(self)
        visibilityIcon = QIcon()
        pixmapOn = QgsApplication.getThemeIcon("/mActionShowAllLayers.svg").pixmap(self.iconSize())
        pixmapOff = QgsApplication.getThemeIcon("/mActionHideAllLayers.svg").pixmap(self.iconSize())
        visibilityIcon.addPixmap(pixmapOn, QIcon.Normal, QIcon.On)
        visibilityIcon.addPixmap(pixmapOff, QIcon.Normal, QIcon.Off)
        self.toggleVisibilityAction.setIcon(visibilityIcon)
        self.toggleVisibilityAction.setCheckable(True)
        self.addAction(self.toggleVisibilityAction)

        self.filterFromExtentAction = QAction(self)
        self.filterFromExtentAction.setIcon(QgsApplication.getThemeIcon('/mActionAddBasicRectangle.svg'))
        self.filterFromExtentAction.setToolTip('Set rectangular filter geometry')
        self.addAction(self.filterFromExtentAction)

        self.filterFromSelectionAction = QAction(self)
        self.filterFromSelectionAction.setIcon(QgsApplication.getThemeIcon('/mActionAddPolygon.svg'))
        self.filterFromSelectionAction.setToolTip('Set filter geometry from selection')
        self.addAction(self.filterFromSelectionAction)

        self.predicateAction = PredicateAction(self)
        self.addWidget(self.predicateAction)

        self.saveCurrentFilterAction = QAction(self)
        self.saveCurrentFilterAction.setIcon(QgsApplication.getThemeIcon('/mActionFileSave.svg'))
        self.saveCurrentFilterAction.setToolTip('Save current filter')
        self.addAction(self.saveCurrentFilterAction)

        self.manageFiltersAction = QAction(self)
        self.manageFiltersAction.setIcon(QgsApplication.getThemeIcon('/mActionFileOpen.svg'))
        self.manageFiltersAction.setToolTip('Manage filters')
        self.addAction(self.manageFiltersAction)

    def setupConnections(self):
        self.toggleFilterAction.toggled.connect(self.controller.onToggled)
        self.filterFromExtentAction.triggered.connect(self.setFilterFromExtent)
        self.manageFiltersAction.triggered.connect(self.manageFilters)
        self.saveCurrentFilterAction.triggered.connect(self.saveCurrentFilter)
        self.predicateAction.predicateChanged.connect(self.setFilterPredicate)
        self.filterFromSelectionAction.triggered.connect(self.setFilterFromSelection)
        self.controller.nameChanged.connect(self.labelFilterName.setText)

    def setFilterPredicate(self, predicate: Predicate):
        self.controller.currentFilter.predicate = predicate.value
        self.controller.refreshFilter()

    def setFilterFromExtent(self):
        dlg = ExtentDialog(self.controller, parent=self)
        dlg.show()

    def setFilterFromSelection(self):
        layer = iface.activeLayer()
        if not layer or not layer.type() == QgsMapLayerType.VectorLayer:
            iface.messageBar().pushInfo('', 'Polygon-Layer auswählen')
            return
        if not layer.geometryType() == QgsWkbTypes.PolygonGeometry:
            iface.messageBar().pushInfo('', 'Polygon-Layer auswählen')
            return
        if not layer.selectedFeatureCount():
            iface.messageBar().pushInfo('', 'Keine Features gewählt')
            return
        crs = iface.activeLayer().crs()
        geom = QgsGeometry.fromWkt('GEOMETRYCOLLECTION()')
        for feature in layer.selectedFeatures():
            geom = geom.combine(feature.geometry())

        self.controller.currentFilter.srsid = crs.srsid()
        self.controller.currentFilter.wkt = geom.asWkt()
        self.controller.refreshFilter()

    def manageFilters(self):
        dlg = ManageFiltersDialog(self.controller, parent=self)
        dlg.exec()

    def saveCurrentFilter(self):
        saveFilterDefinition(self.controller.currentFilter)




