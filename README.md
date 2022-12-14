# QGIS Plugin: Räumlicher Filter
Please scroll down for the English version.

![screenshot](https://user-images.githubusercontent.com/7661092/206454661-e5408810-25bd-4078-9a3b-a54aaff56b53.png)

## Deutsch

### Beschreibung

Erstellt und verwaltet räumliche Filter für vektorbasierte PostGIS-, GeoPackage- und Spatialite-Layer im aktuellen QGIS-Projekt. Damit lässt sich die Anzeige und Bearbeitung der Layer auf eine bestimmte Polygongeometrie oder deren minimal umfassendes Rechteck begrenzen. Es ist möglich Ausnahmen für einzelne Layer zu definieren und die Filtergeometrie anzuzeigen.

Die Entwicklung dieses Plugins wurde von der Hessischen Verwaltung für Bodenmanagement und Geoinformation (HVBG) initialisiert und finanziert.

### Installation

Die Installation ist direkt aus dem QGIS-Plugin-Repository möglich. Alternativ kann hier ein Release heruntergeladen werden und der gezippte Order manuell als QGIS-Erweiterung installiert werden. Es sind keine weiteren Abhängigkeiten vorhanden.

### Nutzung

Erstellen Sie einen Filter, indem Sie eine Ebenenausdehnung verwenden, Objekte einer Ebene auswählen oder ein Rechteck bzw. eine Freihandgeometrie zeichnen. Er wird sofort zum Filtern aller PostGIS-, GeoPackage- und Spatialite-Vektorlayer verwendet. Die Filter werden mit dem Projekt gespeichert und können zusätzlich mit einem Namen in den QGIS-Einstellungen abgelegt werden. Es ist möglich, das räumliche Prädikat von "schneidet" auf "enthält" oder "schneidet nicht" zu ändern. Außerdem können einzelne Layern von der Filterung ausgeschlossen werden. Die Filtergeometrie kann mit einem anpassbaren Stil auf der Karte dargestellt werden.

#### Die Werkzeugleiste
![toolbar_annotated](https://user-images.githubusercontent.com/7661092/207847402-edb72458-570a-4b5a-96d5-8569bd7fdc71.png)
1. Aktuellen Filter entfernen
1. Name des aktuellen Filters
1. Filtergeometrie ein-/ausblenden
1. Auf Filter zoomen
1. Darstellung der Filtergeometrie anpassen
1. Filter erstellen: Rechteckiger Filter
1. Filter erstellen: Filter aus gewählten Features
1. Filter erstellen: Filter-Polygon in der Karte zeichnen
1. Räumlichen Operator auswählen
1. Ausnahmen festlegen
1. Filter verwalten

### Lizenz

General Public License v2

### Entwicklung

[WhereGroup](https://wheregroup.com/): Peter Gipper, Mathias Gröbe, Johannes Kröger

### Beitragen
Bitte Information in der [CONTRIBUTE.md](CONTRIBUTE.md) beachten.

## English

### Description

Create and manage spatial filters that are applied to PostGIS, GeoPackage and Spatialite vector layers in the current QGIS project. The plugin allows for filtered viewing and editing of the layer, with the filter being defined by a polygon geometry or a bounding box. It is possible to define exceptions for layers and display the filter geometry on the map canvas.

The development of this plugin was proposed and funded by Hessische Verwaltung für Bodenmanagement und Geoinformation (HVBG).

### Installation

You can install the plugin directly from the plugin repository. Otherwise, download a release and install the zipped plugin folder as a QGIS extension. There are no extra dependencies.

### Usage

Create a filter with the plugin by using a layer extent, selecting features on a layer, or drawing a rectangle or a rubber band polygon. It will be used immediately to filter all PostGIS, GeoPackage and Spatialite vector layers accordingly. The filters are stored with the project and can be saved to the QGIS settings with a name. The spatial predicate can be changed from "intersects" to "contains" or "disjoint". In addition, specific PostGIS, GeoPackage and Spatialite layers can be excluded from the filtering. The filter geometry can also be shown on canvas with an adjustable style.

#### The Toolbar
![toolbar_annotated](https://user-images.githubusercontent.com/7661092/207847402-edb72458-570a-4b5a-96d5-8569bd7fdc71.png)
1. Remove current filter
1. Name of the current filter
1. Hide filter geometry
1. Zoom to filter
1. Adjust style of the filter geometry
1. Create filter: Rectangular filter
1. Create filter: Filter from selected features
1. Create filter: Draw a filter polygon on the canvas
1. Change geometric predicate
1. Exclude layers from filter
1. Manage filters

### License

General Public License v2

### Development

[WhereGroup](https://wheregroup.com/): Peter Gipper, Mathias Gröbe, Johannes Kröger

### Contribute

Please see [CONTRIBUTE.md](CONTRIBUTE.md).
