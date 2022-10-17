from dataclasses import dataclass
from enum import Enum

from PyQt5.QtWidgets import QMessageBox
from qgis.core import QgsGeometry, QgsCoordinateReferenceSystem
from qgis.utils import iface

from .helpers import saveValue, readValue

SPLIT_CHAR = '#'


class Predicate(Enum):
    INTERSECTS = 1
    WITHIN = 2
    DISJOINT = 3


@dataclass
class FilterDefinition:
    name: str
    wkt: str
    srsid: int
    predicate: int

    def toStorageString(self):
        return f"{self.name}{SPLIT_CHAR}{self.wkt}{SPLIT_CHAR}{self.srsid}{SPLIT_CHAR}{self.predicate}"

    @staticmethod
    def fromStorageString(value: str):
        return FilterDefinition(*value.split(SPLIT_CHAR))

    def crs(self) -> QgsCoordinateReferenceSystem:
        return QgsCoordinateReferenceSystem.fromSrsId(self.srsid)

    def geometry(self) -> QgsGeometry:
        return QgsGeometry.fromWkt(self.wkt)


class Filter:
    definition: FilterDefinition

    def __init__(self, definition: FilterDefinition):
        self.definition = definition



def saveFilterDefinition(filter: FilterDefinition):
    value = readValue(filter.name)
    if value:
        if FilterDefinition.fromStorageString(value) == filter:
            return
        if not askOverwrite(filter.name):
            return
    saveValue(filter.name, filter.toStorageString())


def loadFilterDefinition(name: str) -> FilterDefinition:
    return FilterDefinition.fromStorageString(readValue(name))


def askOverwrite(name: str) -> bool:
    txt = f'Overwrite Settings for Filter <i>{name}</i>?'
    return QMessageBox.question(iface.mainWindow(), 'Overwrite?', txt, QMessageBox.Yes, QMessageBox.No) == QMessageBox.Yes