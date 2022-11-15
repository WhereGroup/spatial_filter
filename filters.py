from dataclasses import dataclass
from enum import Enum, IntEnum
from typing import List, Optional

from PyQt5.QtCore import QObject
from PyQt5.QtWidgets import QMessageBox
from qgis.core import QgsVectorLayer, QgsGeometry, QgsCoordinateReferenceSystem
from qgis.utils import iface

from .helpers import tr, saveSettingsValue, readSettingsValue, allSettingsValues, removeSettingsValue, getLayerGeomName
from .settings import SPLIT_STRING


class Predicate(IntEnum):
    INTERSECTS = 1
    WITHIN = 2
    DISJOINT = 3


@dataclass
class FilterDefinition:
    name: str
    wkt: str
    crs: QgsCoordinateReferenceSystem
    predicate: int
    bbox: bool

    def __post_init__(self):
        self.predicate = int(self.predicate)

    def __lt__(self, other):
        return self.name.upper() < other.name.upper()

    @property
    def geometry(self) -> QgsGeometry:
        return QgsGeometry.fromWkt(self.wkt)

    def filterString(self, layer: QgsVectorLayer) -> str:
        """Returns a layer filter string corresponding to the filter definition.

        Args:
            layer (QgsVectorLayer): The layer for which the filter should be applied

        Returns:
            str: A layer filter string
        """
        template = "{spatial_predicate}({geom_name}, ST_TRANSFORM(ST_GeomFromText('{wkt}', {srid}), {layer_srid}))"

        # ST_DISJOINT does not use spatial indexes, but we can use its opposite "NOT ST_INTERSECTS" which does
        spatial_predicate = f"ST_{Predicate(self.predicate).name}"
        if self.predicate == Predicate.DISJOINT:
            spatial_predicate = "NOT ST_INTERSECTS"

        wkt = self.wkt
        if self.bbox:
            rect = QgsGeometry.fromWkt(self.wkt).boundingBox()
            wkt = QgsGeometry.fromRect(rect).asWkt()

        geom_name = getLayerGeomName(layer)
        return template.format(
            spatial_predicate=spatial_predicate,
            geom_name=geom_name,
            wkt=wkt,
            srid=self.crs.postgisSrid(),
            layer_srid=layer.crs().postgisSrid()
        )

    @property
    def storageString(self) -> str:
        """Returns a text serialisation of the FilterDefinition.

        For the CRS just the Auth ID is stored, e.g. EPSG:1234 or PROJ:9876.
        """
        return SPLIT_STRING.join([self.name, self.wkt, self.crs.authid(), str(self.predicate), str(self.bbox)])

    @staticmethod
    def fromStorageString(value: str) -> 'FilterDefinition':
        parameters = value.split(SPLIT_STRING)
        assert len(parameters) == 5, "Malformed FilterDefinition loaded from settings: {value}"
        name, wkt, crs_auth_id, predicate, bbox_str = parameters
        crs = QgsCoordinateReferenceSystem(crs_auth_id)
        bbox = bool(bbox_str == 'True')
        return FilterDefinition(name, wkt, crs, predicate, bbox)

    @staticmethod
    def defaultFilter():
        return FilterDefinition(tr('New Filter'), '', QgsCoordinateReferenceSystem(), Predicate.INTERSECTS, False)

    @property
    def isValid(self) -> bool:
        return all([self.wkt, self.crs.isValid(), self.predicate])

    @property
    def isSaved(self) -> bool:
        return self.storageString == readSettingsValue(self.name)


def loadFilterDefinition(name: str) -> FilterDefinition:
    return FilterDefinition.fromStorageString(readSettingsValue(name))


def loadAllFilterDefinitions() -> List[FilterDefinition]:
    return [FilterDefinition.fromStorageString(value) for value in allSettingsValues()]


def saveFilterDefinition(filterDef: FilterDefinition) -> None:
    if not filterDef:
        iface.messageBar().pushInfo("", tr("No current filter"))
        return
    if not filterDef.isValid:
        iface.messageBar().pushInfo("", tr("Current filter definition is not valid"))
        return
    if not filterDef.name:
        iface.messageBar().pushInfo("", tr("Please provide a name for the filter"))
        return
    if filterDef.isSaved:
        return
    if readSettingsValue(filterDef.name):
        if not askOverwrite(filterDef.name):
            return
    saveSettingsValue(filterDef.name, filterDef.storageString)


def deleteFilterDefinition(filterDef: FilterDefinition) -> None:
    if askDelete(filterDef.name):
        removeSettingsValue(filterDef.name)


def askApply() -> bool:
    txt = tr('Current settings will be lost. Apply anyway?')
    return QMessageBox.question(iface.mainWindow(), tr('Continue?'), txt,
                                QMessageBox.Yes, QMessageBox.No) == QMessageBox.Yes


def askOverwrite(name: str) -> bool:
    txt = tr('Overwrite settings for filter')
    return QMessageBox.question(iface.mainWindow(), tr('Overwrite?'), f'{txt} <i>{name}</i>?',
                                QMessageBox.Yes, QMessageBox.No) == QMessageBox.Yes


def askDelete(name: str) -> bool:
    txt = tr('Delete filter')
    return QMessageBox.question(iface.mainWindow(), tr('Delete?'), f'{txt} <i>{name}</i>?',
                                QMessageBox.Yes, QMessageBox.No) == QMessageBox.Yes
