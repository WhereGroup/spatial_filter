from dataclasses import dataclass
from enum import Enum, IntEnum
from typing import List

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


def saveFilterDefinition(filterDef: FilterDefinition) -> None:
    value = readValue(filterDef.name)
    if value:
        if FilterDefinition.fromStorageString(value) == filterDef:
            return
        if not askOverwrite(filterDef.name):
            return
    saveValue(filterDef.name, filterDef.storageString)


def loadFilterDefinition(name: str) -> FilterDefinition:
    return FilterDefinition.fromStorageString(readValue(name))


def loadAllFilterDefinitions() -> List[FilterDefinition]:
    return [FilterDefinition.fromStorageString(value) for value in allValues()]


def deleteFilterDefinition(filterDef: FilterDefinition) -> None:
    if askDelete(filterDef.name):
        removeValue(filterDef.name)


def askOverwrite(name: str) -> bool:
    txt = f'Overwrite Settings for Filter <i>{name}</i>?'
    return QMessageBox.question(iface.mainWindow(), 'Overwrite?', txt, QMessageBox.Yes, QMessageBox.No) == QMessageBox.Yes


def askDelete(name: str) -> bool:
    txt = f'Delete Filter <i>{name}</i>?'
    return QMessageBox.question(iface.mainWindow(), 'Delete?', txt, QMessageBox.Yes, QMessageBox.No) == QMessageBox.Yes