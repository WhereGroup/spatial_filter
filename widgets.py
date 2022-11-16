import os

from typing import Optional

from PyQt5 import uic
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QIcon, QColor
from PyQt5.QtWidgets import (
    QToolBar,
    QWidget,
    QAction,
    QPushButton,
    QLineEdit,
    QDialog,
    QVBoxLayout,
    QSizePolicy,
    QDialogButtonBox, QListWidget, QMenu, QActionGroup, QLabel, QFrame, QInputDialog, QTreeView
)
from qgis.gui import QgsExtentWidget, QgsRubberBand
from qgis.core import (
    QgsApplication,
    QgsGeometry,
    QgsProject,
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsVectorLayer,
    QgsWkbTypes,
)
from qgis.utils import iface

from .helpers import removeFilterFromLayer, setLayerException, hasLayerException, addFilterToLayer
from .controller import FilterController
from .models import FilterModel, LayerModel, DataRole
from .filters import Predicate, FilterDefinition, askApply, deleteFilterDefinition, saveFilterDefinition


class ExtentDialog(QDialog):
    def __init__(self, controller: FilterController, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent=parent)
        self.controller = controller
        self.setObjectName("mExtentDialog")
        self.setWindowTitle(self.tr("Set rectangular filter geometry"))
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
        self.extentWidget = QgsExtentWidget(self)
        self.verticalLayout.addWidget(self.extentWidget)
        self.buttonBox = QDialogButtonBox(self)
        self.buttonBox.setOrientation(Qt.Horizontal)
        self.buttonBox.setStandardButtons(QDialogButtonBox.Cancel | QDialogButtonBox.Ok)
        self.verticalLayout.addWidget(self.buttonBox)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)

    def accept(self) -> None:
        if self.extentWidget.isValid():
            self.controller.initFilter()
            self.controller.currentFilter.name = self.tr('New filter from extent')
            self.controller.currentFilter.wkt = QgsGeometry.fromRect(self.extentWidget.outputExtent()).asWkt()
            self.controller.currentFilter.crs = self.extentWidget.outputCrs()
            self.controller.refreshFilter()
        super().accept()


class LayerExceptionsDialog(QDialog):
    def __init__(self, controller: FilterController, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent=parent)
        self.controller = controller
        self.setObjectName("mLayerExceptionsDialog")
        self.setWindowTitle(self.tr("Exclude layers from filter"))
        self.setupUi()
        self.listView.setModel(LayerModel())
        self.adjustSize()

    def setupUi(self):
        sizePolicy = QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.sizePolicy().hasHeightForWidth())
        self.setSizePolicy(sizePolicy)
        self.verticalLayout = QVBoxLayout(self)
        self.listView = QTreeView(self)
        self.listView.header().hide()
        self.verticalLayout.addWidget(self.listView)
        self.buttonBox = QDialogButtonBox(self)
        self.buttonBox.setOrientation(Qt.Horizontal)
        self.buttonBox.setStandardButtons(QDialogButtonBox.Cancel | QDialogButtonBox.Ok)
        self.verticalLayout.addWidget(self.buttonBox)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)

    def accept(self) -> None:
        model = self.listView.model()
        for index in range(model.rowCount()):
            item = model.item(index)
            layer = item.data()
            self.setExceptionForLayer(layer, bool(item.checkState() == Qt.Checked))
        super().accept()

    def setExceptionForLayer(self, layer: QgsVectorLayer, exception: bool) -> None:
        if exception:
            removeFilterFromLayer(layer)
        if not exception and hasLayerException(layer) and self.controller.hasValidFilter():
            addFilterToLayer(layer, self.controller.currentFilter)
        setLayerException(layer, exception)


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
        self.lineEditActiveFilter.setText(self.controller.currentFilter.name if self.controller.currentFilter else '')
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
        if self.controller.currentFilter and not self.controller.currentFilter.isSaved and not askApply():
            return
        selectedIndex = self.listViewNamedFilters.selectedIndexes()[0]
        filterDefinition = self.filterModel.data(index=selectedIndex, role=DataRole)
        filterDefinitionCopy = filterDefinition.copy()
        self.lineEditActiveFilter.setText(filterDefinitionCopy.name)
        self.controller.currentFilter = filterDefinitionCopy
        self.controller.refreshFilter()

    def onDeleteClicked(self):
        selectedIndex = self.listViewNamedFilters.selectedIndexes()[0]
        filterDefinition = self.filterModel.data(index=selectedIndex, role=DataRole)
        deleteFilterDefinition(filterDefinition)
        self.setModel()
        self.controller.refreshFilter()

    def onNameClicked(self):
        if not self.controller.hasValidFilter():
            return
        currentText = self.lineEditActiveFilter.text()
        text, ok = QInputDialog.getText(self, self.tr('Change Name'), self.tr('New Name:'), echo=QLineEdit.Normal, text=currentText)
        if not ok:
            return
        namedFilter = self.controller.currentFilter.copy()
        namedFilter.name = text
        saveFilterDefinition(namedFilter)
        self.setModel()
        self.controller.refreshFilter()


class PredicateButton(QPushButton):
    MENU_WIDTH = 250

    predicateChanged = pyqtSignal(Predicate)
    bboxChanged = pyqtSignal(bool)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent=parent)
        predicateActionNames = {
            Predicate.INTERSECTS: self.tr('intersects'),
            Predicate.WITHIN: self.tr('within'),
            Predicate.DISJOINT: self.tr('disjoint'),
        }
        self.setObjectName('mPredicateSelectAction')
        self.setToolTip(self.tr('Geometric predicate'))
        self.setIcon(QgsApplication.getThemeIcon('/mActionOptions.svg'))
        self.menu = QMenu(parent=parent)

        self.sectionPredicates = self.menu.addSection(self.tr('Geometric Predicate'))
        self.predicateActionGroup = QActionGroup(self)
        self.predicateActionGroup.setExclusive(True)
        for predicate in Predicate:
            action = QAction(self.menu)
            action.setCheckable(True)
            if predicate == Predicate.INTERSECTS:
                action.setChecked(True)
            action.setText(predicateActionNames.get(predicate))
            action.predicate = predicate
            action.triggered.connect(self.onPredicateChanged)
            self.predicateActionGroup.addAction(action)
        self.menu.addActions(self.predicateActionGroup.actions())

        self.sectionComparison = self.menu.addSection(self.tr('Object of comparison'))
        self.bboxActionGroup = QActionGroup(self)
        self.bboxActionGroup.setExclusive(True)
        self.bboxTrueAction = QAction(self.menu)
        self.bboxTrueAction.setCheckable(True)
        self.bboxTrueAction.setText(self.tr('BBOX'))
        self.bboxTrueAction.bbox = True
        self.bboxTrueAction.triggered.connect(self.onBboxChanged)
        self.bboxFalseAction = QAction(self.menu)
        self.bboxFalseAction.setCheckable(True)
        self.bboxFalseAction.setChecked(True)
        self.bboxFalseAction.setText(self.tr('GEOM'))
        self.bboxFalseAction.bbox = False
        self.bboxFalseAction.triggered.connect(self.onBboxChanged)

        self.bboxActionGroup.addAction(self.bboxTrueAction)
        self.bboxActionGroup.addAction(self.bboxFalseAction)
        self.menu.addActions(self.bboxActionGroup.actions())

        self.menu.setMinimumWidth(self.MENU_WIDTH)
        self.setMenu(self.menu)
        self.setFlat(True)

    def onPredicateChanged(self):
        self.predicateChanged.emit(self.getPredicate())

    def getPredicate(self) -> Predicate:
        currentAction = self.predicateActionGroup.checkedAction()
        if currentAction:
            return currentAction.predicate

    def setCurrentPredicateAction(self, predicate: int):
        for action in self.predicateActionGroup.actions():
            if action.predicate == Predicate(predicate):
                action.triggered.disconnect()
                action.setChecked(True)
                action.triggered.connect(self.onPredicateChanged)

    def setCurrentBboxAction(self, bbox: bool):
        action = self.bboxTrueAction if bbox else self.bboxFalseAction
        action.triggered.disconnect()
        action.setChecked(True)
        action.triggered.connect(self.onBboxChanged)

    def onBboxChanged(self):
        self.bboxChanged.emit(self.getBbox())

    def getBbox(self):
        currentAction = self.bboxActionGroup.checkedAction()
        if currentAction:
            return currentAction.bbox


class FilterToolbar(QToolBar):
    LAYOUT_SPACING = 5
    FILTER_LABEL_WIDTH = 150

    def __init__(self, controller: FilterController, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent=parent)
        self.controller = controller
        self.showGeomStatus = False
        self.setWindowTitle(self.tr('Filter Toolbar'))
        self.setObjectName('mFilterToolbar')
        self.setupUi()
        self.setupConnections()
        self.controller.refreshFilter()

    def setupUi(self):
        self.layout().setSpacing(self.LAYOUT_SPACING)

        self.removeFilterAction = QAction(self)
        self.removeFilterAction.setIcon(QgsApplication.getThemeIcon('/mActionDeleteModelComponent.svg'))
        self.removeFilterAction.setToolTip(self.tr('Remove current filter'))
        self.addAction(self.removeFilterAction)

        self.labelFilterName = QLabel(self)
        self.labelFilterName.setFrameShape(QFrame.Panel)
        self.labelFilterName.setFrameShadow(QFrame.Sunken)
        self.labelFilterName.setMinimumWidth(self.FILTER_LABEL_WIDTH)
        self.addWidget(self.labelFilterName)

        self.toggleVisibilityAction = QAction(self)
        visibilityIcon = QIcon()
        pixmapOn = QgsApplication.getThemeIcon("/mActionShowAllLayers.svg").pixmap(self.iconSize())
        pixmapOff = QgsApplication.getThemeIcon("/mActionHideAllLayers.svg").pixmap(self.iconSize())
        visibilityIcon.addPixmap(pixmapOn, QIcon.Normal, QIcon.On)
        visibilityIcon.addPixmap(pixmapOff, QIcon.Normal, QIcon.Off)
        self.toggleVisibilityAction.setIcon(visibilityIcon)
        self.toggleVisibilityAction.setCheckable(True)
        self.toggleVisibilityAction.setToolTip(self.tr('Show filter geometry'))
        self.addAction(self.toggleVisibilityAction)

        self.filterFromExtentAction = QAction(self)
        self.filterFromExtentAction.setIcon(QgsApplication.getThemeIcon('/mActionAddBasicRectangle.svg'))
        self.filterFromExtentAction.setToolTip(self.tr('Rectangular filter'))
        self.addAction(self.filterFromExtentAction)

        self.filterFromSelectionAction = QAction(self)
        self.filterFromSelectionAction.setIcon(QgsApplication.getThemeIcon('/mActionAddPointCloudLayer.svg'))
        self.filterFromSelectionAction.setToolTip(self.tr('Filter from selected features'))
        self.addAction(self.filterFromSelectionAction)

        self.sketchingToolAction = QAction(self)
        self.sketchingToolAction.setIcon(QgsApplication.getThemeIcon('/mActionAddPolygon.svg'))
        self.sketchingToolAction.setToolTip(self.tr('Draw a filter polygon on the canvas'))
        self.addAction(self.sketchingToolAction)

        self.predicateButton = PredicateButton(self)
        self.predicateButton.setIconSize(self.iconSize())
        self.addWidget(self.predicateButton)

        self.layerExceptionsAction = QAction(self)
        self.layerExceptionsAction.setIcon(QgsApplication.getThemeIcon('/mIconLayerTree.svg'))
        self.layerExceptionsAction.setToolTip(self.tr('Exclude layers from filter'))
        self.addAction(self.layerExceptionsAction)

        self.manageFiltersAction = QAction(self)
        self.manageFiltersAction.setIcon(QgsApplication.getThemeIcon('/mActionFileOpen.svg'))
        self.manageFiltersAction.setToolTip(self.tr('Manage filters'))
        self.addAction(self.manageFiltersAction)

    def setupConnections(self):
        self.removeFilterAction.triggered.connect(self.onRemoveFilterClicked)
        self.filterFromExtentAction.triggered.connect(self.startFilterFromExtentDialog)
        self.layerExceptionsAction.triggered.connect(self.startLayerExceptionsDialog)
        self.manageFiltersAction.triggered.connect(self.startManageFiltersDialog)
        self.predicateButton.predicateChanged.connect(self.controller.setFilterPredicate)
        self.predicateButton.bboxChanged.connect(self.controller.setFilterBbox)
        self.filterFromSelectionAction.triggered.connect(self.controller.setFilterFromSelection)
        self.controller.filterChanged.connect(self.onFilterChanged)
        self.toggleVisibilityAction.toggled.connect(self.onShowGeom)
        self.sketchingToolAction.triggered.connect(self.controller.startSketchingTool)

    def onRemoveFilterClicked(self):
        self.controller.removeFilter()

    def onFilterChanged(self, filterDef: Optional[FilterDefinition]):
        if not filterDef:
            self.predicateButton.setCurrentPredicateAction(Predicate.INTERSECTS)
            self.predicateButton.setCurrentBboxAction(False)
            self.removeFilterAction.setEnabled(False)
            self.labelFilterName.setEnabled(False)
            self.toggleVisibilityAction.setEnabled(False)
            self.predicateButton.setEnabled(False)
            self.layerExceptionsAction.setEnabled(False)
        else:
            self.predicateButton.setCurrentPredicateAction(filterDef.predicate)
            self.predicateButton.setCurrentBboxAction(filterDef.bbox)
            self.removeFilterAction.setEnabled(True)
            self.labelFilterName.setEnabled(True)
            self.toggleVisibilityAction.setEnabled(True)
            self.predicateButton.setEnabled(True)
            self.layerExceptionsAction.setEnabled(True)
        self.changeDisplayedName(filterDef)
        self.onShowGeom(self.showGeomStatus)

    def changeDisplayedName(self, filterDef: FilterDefinition):
        if filterDef and filterDef.isValid:
            self.labelFilterName.setText(filterDef.name)
            # self.setItalicName(not filterDef.isSaved)
        else:
            self.labelFilterName.setText(self.tr("No filter geometry set"))
            # self.setItalicName(True)

    def setItalicName(self, italic: bool):
        font = self.labelFilterName.font()
        font.setItalic(italic)
        self.labelFilterName.setFont(font)

    def startFilterFromExtentDialog(self):
        dlg = ExtentDialog(self.controller, parent=self)
        dlg.show()

    def startLayerExceptionsDialog(self):
        dlg = LayerExceptionsDialog(self.controller, parent=self)
        dlg.exec()

    def startManageFiltersDialog(self):
        dlg = ManageFiltersDialog(self.controller, parent=self)
        dlg.exec()

    def onShowGeom(self, checked: bool):
        self.showGeomStatus = checked
        if checked and self.controller.currentFilter:
            tooltip = self.tr('Hide filter geometry')
            self.hideFilterGeom()
            self.showFilterGeom()
        else:
            tooltip = self.tr('Show filter geometry')
            self.hideFilterGeom()
        self.toggleVisibilityAction.setToolTip(tooltip)

    def showFilterGeom(self):
        # Get filterRubberBand geometry, transform it and show it on canvas
        filterRubberBand = QgsRubberBand(iface.mapCanvas(), QgsWkbTypes.PolygonGeometry)
        filterGeom = self.controller.currentFilter.geometry
        if self.controller.currentFilter.bbox:
            filterGeom = QgsGeometry.fromRect(filterGeom.boundingBox())
        filterCrs = self.controller.currentFilter.crs
        projectCrs = QgsCoordinateReferenceSystem(QgsProject.instance().crs())
        filterProj = QgsCoordinateTransform(filterCrs, projectCrs, QgsProject.instance())
        filterGeom.transform(filterProj)
        filterRubberBand.setToGeometry(filterGeom, None)
        filterRubberBand.setFillColor(QColor(0, 0, 255, 127))
        filterRubberBand.setStrokeColor(QColor(0, 0, 0))
        filterRubberBand.setWidth(2)
        # Append to global variable
        self.controller.rubberBands.append(filterRubberBand)

    def hideFilterGeom(self):
        """Removes potentially existing rubber bands"""
        while self.controller.rubberBands:
            rubberBand = self.controller.rubberBands.pop()
            iface.mapCanvas().scene().removeItem(rubberBand)
