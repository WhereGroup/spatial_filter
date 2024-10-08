import os

from typing import Optional

from qgis.PyQt import uic
from qgis.PyQt.QtCore import Qt, pyqtSignal
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import (
    QToolBar,
    QWidget,
    QAction,
    QPushButton,
    QLineEdit,
    QDialog,
    QVBoxLayout,
    QSizePolicy,
    QDialogButtonBox, QListWidget, QMenu, QActionGroup, QLabel, QFrame, QTreeView
)

from qgis.gui import QgsExtentWidget, QgsRubberBand, QgsSymbolButton
from qgis.core import QgsApplication, QgsGeometry, QgsProject, QgsCoordinateReferenceSystem, QgsCoordinateTransform, \
    QgsWkbTypes, QgsSymbol, QgsFillSymbol, QgsSettings, QgsVectorLayer
from qgis.utils import iface

from .helpers import removeFilterFromLayer, setLayerException, hasLayerException, addFilterToLayer, class_for_name
from .controller import FilterController
from .models import FilterModel, LayerModel, DataRole
from .filters import Predicate, FilterDefinition, askApply, deleteFilterDefinition, saveFilterDefinition
from .settings import GROUP_SYMBOL, FILTER_SYMBOL


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
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.sizePolicy().hasHeightForWidth())
        self.setSizePolicy(sizePolicy)
        self.verticalLayout = QVBoxLayout(self)
        self.extentWidget = QgsExtentWidget(self)
        self.verticalLayout.addWidget(self.extentWidget)
        self.buttonBox = QDialogButtonBox(self)
        self.buttonBox.setOrientation(Qt.Orientation.Horizontal)
        self.buttonBox.setStandardButtons(QDialogButtonBox.StandardButton.Cancel | QDialogButtonBox.StandardButton.Ok)
        self.verticalLayout.addWidget(self.buttonBox)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)

    def reset(self):
        self.extentWidget.clear()
        self.extentWidget.setOriginalExtent(iface.mapCanvas().extent(), QgsProject.instance().crs())
        self.extentWidget.setMapCanvas(iface.mapCanvas())

    def accept(self) -> None:
        if self.extentWidget.isValid() and QgsGeometry.fromRect(self.extentWidget.outputExtent()).isGeosValid():
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
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.sizePolicy().hasHeightForWidth())
        self.setSizePolicy(sizePolicy)
        self.verticalLayout = QVBoxLayout(self)
        self.listView = QTreeView(self)
        self.listView.header().hide()
        self.verticalLayout.addWidget(self.listView)
        self.buttonBox = QDialogButtonBox(self)
        self.buttonBox.setOrientation(Qt.Orientation.Horizontal)
        self.buttonBox.setStandardButtons(QDialogButtonBox.StandardButton.Cancel | QDialogButtonBox.StandardButton.Ok)
        self.verticalLayout.addWidget(self.buttonBox)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)

    def accept(self) -> None:
        model = self.listView.model()
        for index in range(model.rowCount()):
            item = model.item(index)
            layer = item.data()
            self.setExceptionForLayer(layer, bool(item.checkState() == Qt.CheckState.Checked))
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
    buttonSave: QPushButton
    buttonApply: QPushButton
    buttonDelete: QPushButton
    buttonClose: QPushButton

    def __init__(self, controller, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent=parent)
        self.controller = controller
        self.setupUi(self)
        self.lineEditActiveFilter.setText(self.controller.currentFilter.name if self.controller.currentFilter else '')
        self.setupConnections()
        self.setModel()

    def setupConnections(self):
        self.buttonSave.clicked.connect(self.onSaveClicked)
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

    def onSaveClicked(self):
        if not self.controller.hasValidFilter():
            return
        text = self.lineEditActiveFilter.text()
        namedFilter = self.controller.currentFilter.copy()
        namedFilter.name = text
        saveFilterDefinition(namedFilter)
        self.setModel()


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

        self.menu.addSection(self.tr('Geometric Predicate'))
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

        self.menu.addSection(self.tr('Object of comparison'))
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
    BUTTON_MIN_WIDTH = 50

    def __init__(self, controller: FilterController, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent=parent)
        self.controller = controller
        self.showGeomStatus = True
        self.extentDialog = None
        self.symbol = self.loadFilterSymbol()
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
        self.labelFilterName.setFrameShape(QFrame.Shape.Panel)
        self.labelFilterName.setFrameShadow(QFrame.Shadow.Sunken)
        self.labelFilterName.setMinimumWidth(self.FILTER_LABEL_WIDTH)
        self.addWidget(self.labelFilterName)

        self.toggleVisibilityAction = QAction(self)
        visibilityIcon = QIcon()
        pixmapOn = QgsApplication.getThemeIcon("/mActionShowAllLayers.svg").pixmap(self.iconSize())
        pixmapOff = QgsApplication.getThemeIcon("/mActionHideAllLayers.svg").pixmap(self.iconSize())
        visibilityIcon.addPixmap(pixmapOn, QIcon.Mode.Normal, QIcon.State.On)
        visibilityIcon.addPixmap(pixmapOff, QIcon.Mode.Normal, QIcon.State.Off)
        self.toggleVisibilityAction.setIcon(visibilityIcon)
        self.toggleVisibilityAction.setCheckable(True)
        self.toggleVisibilityAction.setChecked(True)
        self.toggleVisibilityAction.setToolTip(self.tr('Show filter geometry'))
        self.addAction(self.toggleVisibilityAction)

        self.zoomToFilterAction = QAction(self)
        self.zoomToFilterAction.setIcon(QgsApplication.getThemeIcon('/mActionZoomToArea.svg'))
        self.zoomToFilterAction.setToolTip(self.tr('Zoom to filter'))
        self.addAction(self.zoomToFilterAction)

        self.styleFilterButton = QgsSymbolButton(self, self.tr('Filter style'))
        self.styleFilterButton.setMinimumWidth(self.BUTTON_MIN_WIDTH)
        self.styleFilterButton.setSymbolType(QgsSymbol.SymbolType.Fill)
        self.styleFilterButton.setSymbol(self.symbol.clone())
        self.styleFilterButton.setDialogTitle(self.tr('Style filter'))
        self.addWidget(self.styleFilterButton)

        self.addSeparator()

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

        self.addSeparator()

        self.predicateButton = PredicateButton(self)
        self.predicateButton.setIconSize(self.iconSize())
        self.addWidget(self.predicateButton)

        self.layerExceptionsAction = QAction(self)
        self.layerExceptionsAction.setIcon(QgsApplication.getThemeIcon('/mLayoutItemLegend.svg'))
        self.layerExceptionsAction.setToolTip(self.tr('Exclude layers from filter'))
        self.addAction(self.layerExceptionsAction)

        self.manageFiltersAction = QAction(self)
        self.manageFiltersAction.setIcon(QgsApplication.getThemeIcon('/mIconListView.svg'))
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
        self.styleFilterButton.changed.connect(self.onFilterStyleChanged)
        self.zoomToFilterAction.triggered.connect(self.zoomToFilter)

    def onRemoveFilterClicked(self):
        self.controller.removeFilter()

    def onFilterChanged(self, filterDef: Optional[FilterDefinition]):
        if filterDef:
            self.predicateButton.setCurrentPredicateAction(filterDef.predicate)
            self.predicateButton.setCurrentBboxAction(filterDef.bbox)
            self.removeFilterAction.setEnabled(True)
            self.labelFilterName.setEnabled(True)
            self.toggleVisibilityAction.setEnabled(True)
            self.predicateButton.setEnabled(True)
            self.layerExceptionsAction.setEnabled(True)
            self.zoomToFilterAction.setEnabled(True)
            if not self.showGeomStatus:
                self.toggleVisibilityAction.trigger()
        else:
            self.predicateButton.setCurrentPredicateAction(Predicate.INTERSECTS)
            self.predicateButton.setCurrentBboxAction(False)
            self.removeFilterAction.setEnabled(False)
            self.labelFilterName.setEnabled(False)
            self.toggleVisibilityAction.setEnabled(False)
            self.predicateButton.setEnabled(False)
            self.layerExceptionsAction.setEnabled(False)
            self.zoomToFilterAction.setEnabled(False)
        self.changeDisplayedName(filterDef)
        self.onShowGeom(self.showGeomStatus)

    def changeDisplayedName(self, filterDef: FilterDefinition):
        if filterDef and filterDef.isValid:
            self.labelFilterName.setText(filterDef.name)
        else:
            self.labelFilterName.setText(self.tr("No filter geometry set"))

    def startFilterFromExtentDialog(self):
        if not self.extentDialog:
            self.extentDialog = ExtentDialog(self.controller, parent=self)
        self.extentDialog.reset()
        self.extentDialog.show()

    def startLayerExceptionsDialog(self):
        dlg = LayerExceptionsDialog(self.controller, parent=self)
        dlg.exec()

    def startManageFiltersDialog(self):
        dlg = ManageFiltersDialog(self.controller, parent=self)
        dlg.exec()

    def onFilterStyleChanged(self, *args, **kwargs):
        # Always use clone to assign symbols, otherwise QGIS will crash
        self.symbol = self.styleFilterButton.symbol().clone()
        self.saveFilterSymbol()

        if self.showGeomStatus and self.controller.currentFilter:
            self.hideFilterGeom()
            self.showFilterGeom()

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
        """Get filterRubberBand geometry, transform it and show it on canvas"""
        filterRubberBand = QgsRubberBand(iface.mapCanvas(), QgsWkbTypes.GeometryType.PolygonGeometry)
        filterGeom = self.controller.currentFilter.geometry
        if self.controller.currentFilter.bbox:
            filterGeom = self.controller.currentFilter.boxGeometry
        filterCrs = self.controller.currentFilter.crs
        projectCrs = QgsCoordinateReferenceSystem(QgsProject.instance().crs())
        filterProj = QgsCoordinateTransform(filterCrs, projectCrs, QgsProject.instance())
        filterGeom.transform(filterProj)
        filterRubberBand.setToGeometry(filterGeom, None)
        filterRubberBand.setSymbol(self.symbol.clone())
        # Append to global variable
        self.controller.rubberBands.append(filterRubberBand)

    def hideFilterGeom(self):
        """Removes potentially existing rubber bands"""
        while self.controller.rubberBands:
            rubberBand = self.controller.rubberBands.pop()
            iface.mapCanvas().scene().removeItem(rubberBand)

    def saveFilterSymbol(self):
        """Save the current symbol of the filter into the profile settings"""
        symbol = self.symbol.clone()
        # Note: This does not store sub-layers of e.g. a Marker Fill's marker symbols!
        symbol_layers = [[type(sl).__name__, sl.properties()] for sl in symbol.symbolLayers()]
        QgsSettings().setValue(GROUP_SYMBOL + "/Symbol", symbol_layers)

    def loadFilterSymbol(self):
        """Load setting for filter symbol from profile settings"""
        stored_symbol_layers = QgsSettings().value(GROUP_SYMBOL + "/Symbol")
        if stored_symbol_layers:
            # awkward but non-crashing creation with proper object ownerships...
            symbol = QgsFillSymbol()
            symbol.deleteSymbolLayer(0)
            for symbol_layer_type, properties in stored_symbol_layers:
                symbol_layer = class_for_name("qgis.core", symbol_layer_type).create(properties)
                symbol.appendSymbolLayer(symbol_layer.clone())
            return symbol
        else:
            return QgsFillSymbol.createSimple(FILTER_SYMBOL)

    def zoomToFilter(self):
        if self.controller.hasValidFilter():
            iface.mapCanvas().zoomToFeatureExtent(self.controller.currentFilter.geometry.boundingBox())
            iface.mapCanvas().refresh()
