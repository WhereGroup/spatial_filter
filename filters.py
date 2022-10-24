from dataclasses import dataclass
from enum import Enum, IntEnum
from typing import List, Optional

from PyQt5.QtCore import QObject
from PyQt5.QtWidgets import QMessageBox
from qgis.core import QgsVectorLayer, QgsGeometry, QgsCoordinateReferenceSystem
from qgis.utils import iface

from .helpers import saveSettingsValue, readSettingsValue, allSettingsValues, removeSettingsValue, getLayerGeomName


SPLIT_CHAR = '#'


class Predicate(IntEnum):
    INTERSECTS = 1
    WITHIN = 2
    DISJOINT = 3


@dataclass
class FilterDefinition:
    name: str
    wkt: str
    srsid: int
    predicate: int

    def __post_init__(self):
        self.srsid = int(self.srsid)
        self.predicate = int(self.predicate)

    def __lt__(self, other):
        return self.name.upper() < other.name.upper()

    @property
    def crs(self) -> QgsCoordinateReferenceSystem:
        return QgsCoordinateReferenceSystem.fromSrsId(self.srsid)

    @property
    def geometry(self) -> QgsGeometry:
        return QgsGeometry.fromWkt(self.wkt)

    def filterString(self, layer: QgsVectorLayer) -> str:
        template = "ST_{predicate}({geom_name}, ST_TRANSFORM(ST_GeomFromText('{wkt}', {srid}), {layer_srid}))"
        geom_name = getLayerGeomName(layer)
        return template.format(
            predicate=Predicate(self.predicate).name,
            geom_name=geom_name,
            wkt=self.wkt,
            srid=self.crs.postgisSrid(),
            layer_srid=layer.crs().postgisSrid()
        )

    @property
    def storageString(self) -> str:
        return SPLIT_CHAR.join([self.name, self.wkt, str(self.srsid), str(self.predicate)])

    @staticmethod
    def fromStorageString(value: str) -> 'FilterDefinition':
        return FilterDefinition(*value.split(SPLIT_CHAR))

    @property
    def isValid(self) -> bool:
        return all([self.wkt, self.srsid, self.predicate])

    @property
    def isSaved(self) -> bool:
        return self.storageString == readSettingsValue(self.name)


class FilterManager(QObject):
    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent=parent)

    @staticmethod
    def loadFilterDefinition(name: str) -> FilterDefinition:
        return FilterDefinition.fromStorageString(readSettingsValue(name))

    @staticmethod
    def loadAllFilterDefinitions() -> List[FilterDefinition]:
        return [FilterDefinition.fromStorageString(value) for value in allSettingsValues()]

    def saveFilterDefinition(self, filterDef: FilterDefinition) -> None:
        if not filterDef.isValid:
            iface.messageBar().pushInfo("", self.tr("Current filter definition is not valid"))
            return
        if not filterDef.name:
            iface.messageBar().pushInfo("", self.tr("Please provide a name for the filter"))
            return
        if filterDef.isSaved:
            return
        if readSettingsValue(filterDef.name):
            if not self.askOverwrite(filterDef.name):
                return
        saveSettingsValue(filterDef.name, filterDef.storageString)

    def deleteFilterDefinition(self, filterDef: FilterDefinition) -> None:
        if self.askDelete(filterDef.name):
            removeSettingsValue(filterDef.name)

    def askApply(self) -> bool:
        txt = self.tr('Current settings will be lost. Apply anyway?')
        return QMessageBox.question(iface.mainWindow(), self.tr('Continue?'), txt,
                                    QMessageBox.Yes, QMessageBox.No) == QMessageBox.Yes

    def askOverwrite(self, name: str) -> bool:
        txt = self.tr('Overwrite settings for filter')
        return QMessageBox.question(iface.mainWindow(), self.tr('Overwrite?'), f'{txt} <i>{name}</i>?',
                                    QMessageBox.Yes, QMessageBox.No) == QMessageBox.Yes

    def askDelete(self, name: str) -> bool:
        txt = self.tr('Delete filter')
        return QMessageBox.question(iface.mainWindow(), self.tr('Delete?'), f'{txt} <i>{name}</i>?',
                                    QMessageBox.Yes, QMessageBox.No) == QMessageBox.Yes