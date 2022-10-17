import os

from typing import Optional, List

from PyQt5.QtGui import QIcon, QPixmap
from PyQt5.QtWidgets import QToolBar, QWidget, QComboBox, QAction
from qgis.core import QgsApplication, QgsProject

from .filters import Predicate, FilterDefinition, saveFilterDefinition, loadFilterDefinition


class FilterBox(QComboBox):
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent=parent)
        self.addItem("Kein aktiver Filter", None)
        self.addItem("Filter 1", )


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
        storageString = filter.toStorageString()
        newFilter = FilterDefinition.fromStorageString(storageString)
        saveFilterDefinition(newFilter)
        otherFilter = loadFilterDefinition('filter1')
        for layer in QgsProject.instance().mapLayers().values():
            print(layer.name())




class FilterToolbar(QToolBar):

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent=parent)
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

        filterBox = FilterBox(self)
        self.filterActions.append(filterBox)
        self.addWidget(filterBox)

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




