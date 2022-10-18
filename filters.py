from dataclasses import dataclass
from enum import Enum, IntEnum

from PyQt5.QtWidgets import QMessageBox
from qgis.core import QgsGeometry, QgsCoordinateReferenceSystem
from qgis.utils import iface

from .helpers import saveValue, readValue


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

    @property
    def crs(self) -> QgsCoordinateReferenceSystem:
        return QgsCoordinateReferenceSystem.fromSrsId(self.srsid)

    @property
    def geometry(self) -> QgsGeometry:
        return QgsGeometry.fromWkt(self.wkt)

    def filterString(self, geom_name):
        template = "ST_{predicate}({geom_name}, ST_GeomFromText('{wkt}', {srid}))"
        return template.format(
            predicate=Predicate(self.predicate).name,
            geom_name=geom_name,
            wkt=self.wkt,
            srid=self.crs.postgisSrid()
        )

    @property
    def storageString(self):
        return SPLIT_CHAR.join([self.name, self.wkt, self.srsid, self.predicate])

    @staticmethod
    def fromStorageString(value: str):
        return FilterDefinition(*value.split(SPLIT_CHAR))


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