from dataclasses import dataclass, replace
from enum import IntEnum
from typing import List
import re

from qgis.PyQt.QtWidgets import QMessageBox
from qgis.core import QgsVectorLayer, QgsGeometry, QgsCoordinateReferenceSystem, QgsCoordinateTransform, QgsProject, QgsWkbTypes
from qgis.utils import iface

from .settings import FILTER_COMMENT_START, FILTER_COMMENT_STOP, LOCALIZED_PLUGIN_NAME
from .helpers import tr, saveSettingsValue, readSettingsValue, allSettingsValues, removeSettingsValue, \
    getLayerGeomName, matchFormatString


FILTERSTRING_SQL_TEMPLATE = "{spatial_predicate}({geom_expr}, ST_TRANSFORM(ST_GeomFromText('{wkt}', {srid}), {layer_srid}))"
# Backward-compatible parser for filters written by older plugin versions.
FILTERSTRING_SQL_TEMPLATE_LEGACY = "{spatial_predicate}({geom_name}, ST_TRANSFORM(ST_GeomFromText('{wkt}', {srid}), {layer_srid}))"
FILTERSTRING_EXPR_TEMPLATE = "{spatial_predicate}(@geometry, geomFromWKT('{wkt}'))"
MAX_REMOTE_FILTER_EXPRESSION_LENGTH = 6000


def crs_from_postgis_srid(srid) -> QgsCoordinateReferenceSystem:
    """Create a CRS from an EPSG/PostGIS SRID without using the deprecated int constructor."""
    crs = QgsCoordinateReferenceSystem(f"EPSG:{int(srid)}")
    if not crs.isValid():
        crs = QgsCoordinateReferenceSystem()
        crs.createFromSrid(int(srid))
    return crs


def geometry2d(geometry: QgsGeometry) -> QgsGeometry:
    """Return a defensive 2D copy of a geometry.

    Spatial filters in this plugin are planimetric. QGIS 3D renderer settings
    and Z/M-enabled layer geometries must not make an otherwise matching
    feature disappear from the 2D spatial filter. Some providers/services also
    react poorly to PolygonZ/MultiPolygonZ WKT in subset expressions.
    """
    geom = QgsGeometry(geometry)
    try:
        abstract_geometry = geom.constGet()
        if abstract_geometry is None:
            return geom
        abstract_geometry = abstract_geometry.clone()
        if QgsWkbTypes.hasZ(abstract_geometry.wkbType()):
            abstract_geometry.dropZValue()
        if QgsWkbTypes.hasM(abstract_geometry.wkbType()):
            abstract_geometry.dropMValue()
        return QgsGeometry(abstract_geometry)
    except Exception:
        return geom


def layer_geometry_sql_expression(layer: QgsVectorLayer) -> str:
    """Return a provider SQL expression for the layer geometry as 2D geometry.

    The filter is intentionally planimetric. Z/M values and QGIS 3D renderer
    settings must not influence whether a feature is inside the filter area.

    GeoPackage/SQLite layers from ALKIS/NAS and similar sources may expose
    OGC geometry collection families such as MultiSurfaceZ or MultiCurveZ. For
    those curved/surface types, provider-side SQL needs an additional
    linearisation step before the normal 2D cast.
    """
    geom_name = getLayerGeomName(layer)
    provider_type = layer.providerType().lower()
    storage_type = layer.storageType().upper()
    is_curved_or_surface = QgsWkbTypes.isCurvedType(layer.wkbType())

    # PostGIS handles explicit 2D forcing reliably and this avoids Z/M-related
    # false negatives for true database layers.
    if provider_type == "postgres" or "POSTGIS" in storage_type:
        geom_expr = geom_name
        if is_curved_or_surface:
            geom_expr = f"ST_CurveToLine({geom_expr})"
        return f"ST_Force2D({geom_expr})"

    if storage_type in {"GPKG", "SQLITE"}:
        # Important: do not wrap GeoPackage/OGR geometries here. In practice,
        # expressions such as CastToXY(ST_CurveToLine(GEOMETRY)) can be accepted
        # by the provider but evaluate to NULL/false for MultiSurfaceZ and
        # MultiCurveZ layers, which makes QGIS hide every feature. The filter
        # geometry itself is already forced to 2D before it is written as WKT;
        # OGR/SQLite spatial predicates then evaluate the layer geometry
        # planimetrically and handle Z-enabled MultiSurface/MultiCurve layers
        # much more robustly.
        return geom_name

    return geom_name


def _filter_geometry_sql(filter_def: 'FilterDefinition', layer: QgsVectorLayer) -> str:
    wkt = filter_def.boxGeometry.asWkt() if filter_def.bbox else filter_def.geometry.asWkt()
    return "ST_TRANSFORM(ST_GeomFromText('{wkt}', {srid}), {layer_srid})".format(
        wkt=wkt.replace("'", "''"),
        srid=filter_def.crs.postgisSrid(),
        layer_srid=layer.crs().postgisSrid(),
    )


def _sqlite_exact_spatial_filter_sql(filter_def: 'FilterDefinition', layer: QgsVectorLayer) -> str:
    """Build a stricter GeoPackage/SQLite spatial predicate.

    ST_Intersects on some GPKG/OGR builds can behave like an envelope hit for
    complex MultiSurface/MultiCurve geometries. NOT ST_Disjoint usually forces
    the exact topological test and avoids visible false positives outside the
    drawn filter geometry.
    """
    geom_expr = layer_geometry_sql_expression(layer)
    filter_geom = _filter_geometry_sql(filter_def, layer)
    if filter_def.predicate == Predicate.INTERSECTS:
        return f"NOT ST_Disjoint({geom_expr}, {filter_geom})"
    if filter_def.predicate == Predicate.DISJOINT:
        return f"ST_Disjoint({geom_expr}, {filter_geom})"
    if filter_def.predicate == Predicate.WITHIN:
        return f"ST_Within({geom_expr}, {filter_geom})"
    return f"NOT ST_Disjoint({geom_expr}, {filter_geom})"


class Predicate(IntEnum):
    INTERSECTS = 1
    WITHIN = 2
    DISJOINT = 3


class RemoteFilterStrategy(IntEnum):
    """Strategy for WFS/OAPIF layers where long geometry filters may overload URLs/servers."""
    AUTO = 1
    EXACT = 2
    SIMPLIFIED = 3
    BBOX = 4


@dataclass
class RemoteFilterCandidate:
    expression: str
    geometry: QgsGeometry
    strategy: RemoteFilterStrategy
    used_bbox: bool = False


class RemoteFilterStrategyBuilder:
    """Builds robust provider-expression filters for WFS and OGC API Features layers.

    In AUTO mode the class tries to keep the filter exact. Only if the generated
    expression becomes too long, it falls back to a simplified geometry and then
    to the bounding box. This avoids Request-URI-too-long errors without
    unnecessarily reducing spatial precision.
    """

    def __init__(self, filter_def: 'FilterDefinition', layer: QgsVectorLayer):
        self.filter_def = filter_def
        self.layer = layer

    def build(self) -> RemoteFilterCandidate:
        selected_strategy = RemoteFilterStrategy(self.filter_def.remote_strategy)

        if self.filter_def.bbox or selected_strategy == RemoteFilterStrategy.BBOX:
            return self._candidate(self.filter_def.boxGeometry, use_bbox=True, strategy=RemoteFilterStrategy.BBOX)

        exact = self._candidate(self.filter_def.geometry, strategy=RemoteFilterStrategy.EXACT)
        if selected_strategy == RemoteFilterStrategy.EXACT:
            return exact
        if selected_strategy == RemoteFilterStrategy.SIMPLIFIED:
            return self._simplified_or_bbox()
        if len(exact.expression) <= MAX_REMOTE_FILTER_EXPRESSION_LENGTH:
            return exact

        return self._simplified_or_bbox()

    def _simplified_or_bbox(self) -> RemoteFilterCandidate:
        simplified = self._candidate(self._simplified_geometry(), strategy=RemoteFilterStrategy.SIMPLIFIED)
        if simplified.geometry and simplified.geometry.isGeosValid() and len(simplified.expression) <= MAX_REMOTE_FILTER_EXPRESSION_LENGTH:
            return simplified
        return self._candidate(self.filter_def.boxGeometry, use_bbox=True, strategy=RemoteFilterStrategy.BBOX)

    def _simplified_geometry(self) -> QgsGeometry:
        geometry = geometry2d(self.filter_def.geometry)
        bbox = geometry.boundingBox()
        diagonal = ((bbox.width() ** 2) + (bbox.height() ** 2)) ** 0.5
        tolerance = max(diagonal / 2000.0, 0.001)
        simplified = geometry.simplify(tolerance)
        if simplified and not simplified.isEmpty() and simplified.isGeosValid():
            return simplified
        return geometry

    def _candidate(self, geometry: QgsGeometry, use_bbox: bool = False,
                   strategy: RemoteFilterStrategy = RemoteFilterStrategy.EXACT) -> RemoteFilterCandidate:
        transformed_geometry = geometry2d(geometry)
        if self.filter_def.crs.isValid() and self.layer.crs().isValid() and self.filter_def.crs != self.layer.crs():
            transform = QgsCoordinateTransform(self.filter_def.crs, self.layer.crs(), QgsProject.instance())
            transformed_geometry.transform(transform)

        spatial_predicate = Predicate(self.filter_def.predicate).name.lower()
        if use_bbox:
            spatial_predicate = "bbox"

        expression = FILTERSTRING_EXPR_TEMPLATE.format(
            spatial_predicate=spatial_predicate,
            wkt=transformed_geometry.asWkt(),
        )
        return RemoteFilterCandidate(expression, transformed_geometry, strategy, use_bbox)


@dataclass
class FilterDefinition:
    name: str
    wkt: str
    crs: QgsCoordinateReferenceSystem
    predicate: int
    bbox: bool
    remote_strategy: int = RemoteFilterStrategy.AUTO

    def __post_init__(self):
        self.predicate = int(self.predicate)
        self.remote_strategy = int(self.remote_strategy)

    def __lt__(self, other):
        return self.name.upper() < other.name.upper()

    @property
    def geometry(self) -> QgsGeometry:
        return geometry2d(QgsGeometry.fromWkt(self.wkt))

    @property
    def boxGeometry(self) -> QgsGeometry:
        return geometry2d(QgsGeometry.fromRect(self.geometry.boundingBox()))

    def filterString(self, layer: QgsVectorLayer) -> str:
        """Returns a layer filter string corresponding to the filter definition.

        Args:
            layer (QgsVectorLayer): The layer for which the filter should be applied

        Returns:
            str: A layer filter string
        """
        provider_type = layer.providerType().lower()

        if provider_type in {"wfs", "oapif"}:
            return self._expressionFilterString(layer)

        return self._sqlFilterString(layer)

    def _sqlFilterString(self, layer: QgsVectorLayer) -> str:
        # ST_DISJOINT does not use spatial indexes, but we can use its opposite "NOT ST_INTERSECTS" which does
        spatial_predicate = f"ST_{Predicate(self.predicate).name}"
        if self.predicate == Predicate.DISJOINT:
            spatial_predicate = "NOT ST_INTERSECTS"

        wkt = self.geometry.asWkt()
        if self.bbox:
            wkt = self.boxGeometry.asWkt()

        storage_type = layer.storageType().upper()
        if storage_type in {"GPKG", "SQLITE"}:
            return _sqlite_exact_spatial_filter_sql(self, layer)

        geom_expr = layer_geometry_sql_expression(layer)

        return FILTERSTRING_SQL_TEMPLATE.format(
            spatial_predicate=spatial_predicate,
            geom_expr=geom_expr,
            wkt=wkt.replace("'", "''"),
            srid=self.crs.postgisSrid(),
            layer_srid=layer.crs().postgisSrid()
        )

    def _expressionFilterString(self, layer: QgsVectorLayer) -> str:
        return RemoteFilterStrategyBuilder(self, layer).build().expression

    @staticmethod
    def fromFilterString(subsetString: str) -> 'FilterDefinition':
        start_index = subsetString.find(FILTER_COMMENT_START) + len(FILTER_COMMENT_START)
        stop_index = subsetString.find(FILTER_COMMENT_STOP)
        filterString = subsetString[start_index: stop_index].strip()
        if filterString.upper().startswith('AND '):
            filterString = filterString[4:].strip()

        for parser in (_filterDefinitionFromSqlStringRobust, _filterDefinitionFromExpressionStringRobust):
            try:
                return updateFilterNameFromStorage(parser(filterString))
            except Exception:
                continue

        raise ValueError(f"Unsupported filter string format: {filterString}")

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
            'bbox': self.bbox,
            'remote_strategy': str(self.remote_strategy)
        }

    @staticmethod
    def fromStorageDict(value: dict) -> 'FilterDefinition':
        assert len(value) in (5, 6), f"Malformed FilterDefinition loaded from settings: {value}"
        name = value['name']
        wkt = value['wkt']
        predicate = value['predicate']
        bbox = value['bbox']
        remote_strategy = value.get('remote_strategy', RemoteFilterStrategy.AUTO)
        crs = QgsCoordinateReferenceSystem(value['srid'])
        return FilterDefinition(name, wkt, crs, predicate, bbox, remote_strategy)

    @staticmethod
    def defaultFilter():
        return FilterDefinition(tr('New Filter'), '', QgsCoordinateReferenceSystem(), Predicate.INTERSECTS, False, RemoteFilterStrategy.AUTO)

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


def _filterDefinitionFromSqlString(filterString: str, params: dict) -> FilterDefinition:
    predicateName = params['spatial_predicate'][len('ST_'):]
    if filterString.startswith('NOT ST_INTERSECTS'):
        predicateName = 'DISJOINT'

    predicate = Predicate[predicateName]
    return FilterDefinition(
        name=tr('Unknown filter'),
        wkt=params['wkt'],
        crs=crs_from_postgis_srid(params['srid']),
        predicate=predicate.value,
        bbox=False,
        remote_strategy=RemoteFilterStrategy.AUTO
    )


def _filterDefinitionFromExpressionString(filterString: str, params: dict) -> FilterDefinition:
    predicate_name = params['spatial_predicate'].upper()
    bbox = predicate_name == 'BBOX'
    if bbox:
        predicate_name = 'INTERSECTS'

    predicate = Predicate[predicate_name]
    return FilterDefinition(
        name=tr('Unknown filter'),
        wkt=params['wkt'],
        crs=QgsCoordinateReferenceSystem(),
        predicate=predicate.value,
        bbox=bbox,
        remote_strategy=RemoteFilterStrategy.AUTO
    )


def _filterDefinitionFromSqlStringRobust(filterString: str) -> FilterDefinition:
    """Parse SQL subset strings written by this plugin.

    The older generic format-string parser does not cope reliably with nested
    geometry expressions such as CastToXY(ST_CurveToLine(GEOMETRY)) and long
    MultiPolygon WKT. A narrow regex is safer here: the plugin only needs to
    recover the spatial predicate, filter WKT and source SRID.
    """
    pattern = re.compile(
        r"^\s*(?P<neg>NOT\s+)?(?P<pred>ST_(?:INTERSECTS|WITHIN|DISJOINT))\s*\("
        r".*?ST_GeomFromText\s*\(\s*'(?P<wkt>.*?)'\s*,\s*(?P<srid>\d+)\s*\)"
        r"\s*,\s*(?P<layer_srid>\d+)\s*\)\s*\)\s*$",
        re.IGNORECASE | re.DOTALL,
    )
    match = pattern.match(filterString)
    if not match:
        raise ValueError("not a plugin SQL filter")

    predicate_name = match.group('pred').upper()[len('ST_'):]
    if match.group('neg') and predicate_name == 'INTERSECTS':
        predicate_name = 'DISJOINT'
    elif match.group('neg') and predicate_name == 'DISJOINT':
        predicate_name = 'INTERSECTS'

    predicate = Predicate[predicate_name]
    return FilterDefinition(
        name=tr('Unknown filter'),
        wkt=match.group('wkt'),
        crs=crs_from_postgis_srid(match.group('srid')),
        predicate=predicate.value,
        bbox=False,
        remote_strategy=RemoteFilterStrategy.AUTO,
    )


def _filterDefinitionFromExpressionStringRobust(filterString: str) -> FilterDefinition:
    pattern = re.compile(
        r"^\s*(?P<pred>intersects|within|disjoint|bbox)\s*\(\s*@geometry\s*,\s*geomFromWKT\s*\(\s*'(?P<wkt>.*?)'\s*\)\s*\)\s*$",
        re.IGNORECASE | re.DOTALL,
    )
    match = pattern.match(filterString)
    if not match:
        raise ValueError("not a plugin expression filter")

    predicate_name = match.group('pred').upper()
    bbox = predicate_name == 'BBOX'
    if bbox:
        predicate_name = 'INTERSECTS'

    predicate = Predicate[predicate_name]
    return FilterDefinition(
        name=tr('Unknown filter'),
        wkt=match.group('wkt'),
        crs=QgsCoordinateReferenceSystem(),
        predicate=predicate.value,
        bbox=bbox,
        remote_strategy=RemoteFilterStrategy.AUTO,
    )
