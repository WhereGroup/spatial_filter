from dataclasses import dataclass, replace
from enum import IntEnum
from typing import List

from qgis.PyQt.QtWidgets import QMessageBox

from qgis.core import (
    QgsVectorLayer, 
    QgsGeometry, 
    QgsCoordinateReferenceSystem,
    Qgis
)

if Qgis.QGIS_VERSION_INT > 33600:
    from qgis.core import QgsSensorThingsUtils

from qgis.utils import iface

from .settings import (
    LOCALIZED_PLUGIN_NAME,
    SENSORTHINGS_STORAGE_TYPE
)

from .helpers import (
    tr, 
    saveSettingsValue, 
    readSettingsValue, 
    allSettingsValues, 
    removeSettingsValue,
    getLayerGeomName, 
    matchFormatString,
    reproject_geometry,
    getFilterStartStopString
)


FILTERSTRING_TEMPLATE = "{spatial_predicate}({geom_name}, ST_TRANSFORM(ST_GeomFromText('{wkt}', {srid}), {layer_srid}))"

# sensorthings filter does not support reprojection (st_transform)
# reprojection happens in helpers.py -> addFilterToLayer
FILTERSTRING_TEMPLATE_SENSORTHINGS = "{spatial_predicate}({geom_name}, geography'{wkt}')"


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

    @property
    def boxGeometry(self) -> QgsGeometry:
        return QgsGeometry.fromRect(self.geometry.boundingBox())

    def filterString(self, layer: QgsVectorLayer) -> str:
        """Returns a layer filter string corresponding to the filter definition.

        Args:
            layer (QgsVectorLayer): The layer for which the filter should be applied

        Returns:
            str: A layer filter string
        """
        spatial_predicate = f"ST_{Predicate(self.predicate).name}"
        wkt = self.wkt if not self.bbox else self.boxGeometry.asWkt()
        srid=self.crs.postgisSrid()
        layer_srid=layer.crs().postgisSrid()
        geom_name = getLayerGeomName(layer)

        if layer.storageType() == SENSORTHINGS_STORAGE_TYPE:
            # SensorThings only supports single geometry types
            single_geometry = QgsGeometry.fromWkt(wkt)
            single_geometry.convertToSingleType()

            # SensorThings filter does not support reprojection (st_transform)
            # thats why the reprojection must be executed on client-side.
            reprojected_geometry = reproject_geometry(single_geometry, srid, layer_srid)

            spatial_predicate = spatial_predicate.lower()  # sensorthings specification uses lower case

            return FILTERSTRING_TEMPLATE_SENSORTHINGS.format(
                spatial_predicate=spatial_predicate,
                geom_name=geom_name,
                wkt=reprojected_geometry.asWkt()
            )
        # ST_DISJOINT does not use spatial indexes, but we can use its opposite "NOT ST_INTERSECTS" which does
        if self.predicate == Predicate.DISJOINT:
            spatial_predicate = "NOT ST_INTERSECTS"

        return FILTERSTRING_TEMPLATE.format(
            spatial_predicate=spatial_predicate,
            geom_name=geom_name,
            wkt=wkt,
            srid=srid,
            layer_srid=layer_srid
        )


    @staticmethod
    def fromFilterString(layer: QgsVectorLayer) -> 'FilterDefinition':
        subsetString = layer.subsetString()
        FILTER_START_STRING, FILTER_STOP_STRING = getFilterStartStopString(layer)
        start_index = subsetString.find(FILTER_START_STRING) + len(FILTER_START_STRING)
        stop_index = subsetString.find(FILTER_STOP_STRING)
        filterString = subsetString[start_index: stop_index]
        filterString = filterString.replace(' AND ', '')

        if layer.storageType() == SENSORTHINGS_STORAGE_TYPE:
            params = matchFormatString(FILTERSTRING_TEMPLATE, filterString)
            predicateName = params['spatial_predicate'][len('st_'):]

        else:
            params = matchFormatString(FILTERSTRING_TEMPLATE, filterString)
            predicateName = params['spatial_predicate'][len('ST_'):]
            if filterString.startswith('NOT ST_INTERSECTS'):
                predicateName = 'DISJOINT'#

        predicate = Predicate[predicateName]
        filterDefinition = FilterDefinition(
            name=tr('Unknown filter'),
            wkt=params['wkt'],
            crs=QgsCoordinateReferenceSystem(int(params['srid'])),
            predicate=predicate.value,
            bbox=False
        )
        return updateFilterNameFromStorage(filterDefinition)

    @property
    def storageDict(self) -> dict:
        """Returns a text serialisation of the FilterDefinition.

        For the CRS just the Auth ID is stored, e.g. EPSG:1234 or PROJ:9876.
        """
        return {
            'name': self.name,
            'wkt': self.wkt,
            'srid': self.crs.authid(),
            'predicate': str(self.predicate),
            'bbox': self.bbox
        }

    @staticmethod
    def fromStorageDict(value: dict) -> 'FilterDefinition':
        assert len(value) == 5, f"Malformed FilterDefinition loaded from settings: {value}"
        name = value['name']
        wkt = value['wkt']
        predicate = value['predicate']
        bbox = value['bbox']
        crs = QgsCoordinateReferenceSystem(value['srid'])
        return FilterDefinition(name, wkt, crs, predicate, bbox)

    @staticmethod
    def defaultFilter():
        return FilterDefinition(tr('New Filter'), '', QgsCoordinateReferenceSystem(), Predicate.INTERSECTS, False)

    @property
    def isValid(self) -> bool:
        return all([self.geometry.isGeosValid(), self.crs.isValid(), self.predicate])

    @property
    def isSaved(self) -> bool:
        return self.storageDict == readSettingsValue(self.name)

    def copy(self):
        return replace(self)


def loadFilterDefinition(name: str) -> FilterDefinition:
    return FilterDefinition.fromStorageDict(readSettingsValue(name))


def loadAllFilterDefinitions() -> List[FilterDefinition]:
    return [FilterDefinition.fromStorageDict(value) for value in allSettingsValues()]


def saveFilterDefinition(filterDef: FilterDefinition) -> None:
    if not filterDef:
        iface.messageBar().pushInfo(LOCALIZED_PLUGIN_NAME, tr("No current filter"))
        return
    if not filterDef.isValid:
        iface.messageBar().pushInfo(LOCALIZED_PLUGIN_NAME, tr("Current filter definition is not valid"))
        return
    if not filterDef.name:
        iface.messageBar().pushInfo(LOCALIZED_PLUGIN_NAME, tr("Please provide a name for the filter"))
        return
    if filterDef.isSaved:
        return
    if readSettingsValue(filterDef.name):
        if not askOverwrite(filterDef.name):
            return
    saveSettingsValue(filterDef.name, filterDef.storageDict)


def deleteFilterDefinition(filterDef: FilterDefinition) -> None:
    if askDelete(filterDef.name):
        removeSettingsValue(filterDef.name)


def updateFilterNameFromStorage(filterDef: FilterDefinition) -> FilterDefinition:
    for storageFilter in loadAllFilterDefinitions():
        if filterDef.crs == storageFilter.crs and filterDef.wkt == storageFilter.wkt:
            storageFilter.predicate = filterDef.predicate
            return storageFilter
        if filterDef.crs == storageFilter.crs and filterDef.wkt == storageFilter.boxGeometry.asWkt():
            storageFilter.predicate = filterDef.predicate
            storageFilter.bbox = True
            return storageFilter
    return filterDef


def askApply() -> bool:
    txt = tr('Current settings will be lost. Apply anyway?')
    return QMessageBox.question(iface.mainWindow(), tr('Continue?'), txt,
                                QMessageBox.StandardButton.Yes, QMessageBox.StandardButton.No) == QMessageBox.StandardButton.Yes


def askOverwrite(name: str) -> bool:
    txt = tr('Overwrite settings for filter')
    return QMessageBox.question(iface.mainWindow(), tr('Overwrite?'), f'{txt} <i>{name}</i>?',
                                QMessageBox.StandardButton.Yes, QMessageBox.StandardButton.No) == QMessageBox.StandardButton.Yes


def askDelete(name: str) -> bool:
    txt = tr('Delete filter')
    return QMessageBox.question(iface.mainWindow(), tr('Delete?'), f'{txt} <i>{name}</i>?',
                                QMessageBox.StandardButton.Yes, QMessageBox.StandardButton.No) == QMessageBox.StandardButton.Yes
