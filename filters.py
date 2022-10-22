from dataclasses import dataclass
from enum import Enum, IntEnum
from typing import List, Optional

from PyQt5.QtCore import QObject
from PyQt5.QtWidgets import QMessageBox
from qgis.core import QgsGeometry, QgsCoordinateReferenceSystem
from qgis.utils import iface

from .helpers import saveValue, readValue, allValues, removeValue


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

    def filterString(self, geom_name) -> str:
        template = "ST_{predicate}(ST_TRANSFORM({geom_name}, {srid}), ST_GeomFromText('{wkt}', {srid}))"
        return template.format(
            predicate=Predicate(self.predicate).name,
            geom_name=geom_name,
            wkt=self.wkt,
            srid=self.crs.postgisSrid()
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
        return self.storageString == readValue(self.name)


class FilterManager(QObject):
    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent=parent)

    @staticmethod
    def loadFilterDefinition(name: str) -> FilterDefinition:
        return FilterDefinition.fromStorageString(readValue(name))

    @staticmethod
    def loadAllFilterDefinitions() -> List[FilterDefinition]:
        return [FilterDefinition.fromStorageString(value) for value in allValues()]

    def saveFilterDefinition(self, filterDef: FilterDefinition) -> None:
        if not filterDef.isValid:
            iface.messageBar().pushInfo("", self.tr("Current filter definition is not valid"))
            return
        if not filterDef.name:
            iface.messageBar().pushInfo("", self.tr("Please provide a name for the filter"))
            return
        if filterDef.isSaved:
            return
        if readValue(filterDef.name):
            if not self.askOverwrite(filterDef.name):
                return
        saveValue(filterDef.name, filterDef.storageString)

    def deleteFilterDefinition(self, filterDef: FilterDefinition) -> None:
        if self.askDelete(filterDef.name):
            removeValue(filterDef.name)

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