# QGIS Plugin: Räumlicher Filter
Please scroll down for the English version.

## Deutsch

### Beschreibung

Erstellt und verwaltet räumliche Filter für vektorbasierte PostGIS-Layer im aktuellen QGIS-Projekt. Damit lässt sich die Anzeige und Bearbeitung der Layer auf eine bestimmte Polygongeometrie oder deren minimal umfassendes Rechteck begrenzen. Es ist möglich Ausnahmen für einzelne Layer zu definieren und die Filtergeometrie anzuzeigen.

Die Entwicklung dieses Plugins wurde von der Hessischen Verwaltung für Bodenmanagement und Geoinformation (HVBG) finanziert.

### Installation

Die Installation ist direkt aus dem QGIS-Plugin-Repository möglich. Alternativ kann hier ein Release heruntergeladen werden und der gezippte Order manuell als QGIS-Erweiterung installiert werden. Es sind keine weiteren Abhängigkeiten vorhanden.

### Nutzung

Erstellen Sie einen Filter, indem Sie eine Ebenenausdehnung verwenden, Objekte einer Ebene auswählen oder ein Rechteck bzw. eine Freihandgeometrie zeichnen. Er wird sofort zum Filtern aller PostGIS-Vektorlayer verwendet. Die Filter werden mit dem Projekt gespeichert und können zusätzlich mit einem Namen in den QGIS-Einstellungen abgelegt werden. Es ist möglich, das räumliche Prädikat von "schneidet" auf "enthält" oder "schneidet nicht" zu ändern. Außerdem können einzelne PostGIS-Ebenen vom Filter ausgeschlossen werden. Die Filtergeometrie kann mit einem anpassbaren Stil auf der Karte dargestellt werden.

### Lizenz

General Public License v2

### Entwicklung

[WhereGroup](https://wheregroup.com/): Peter Gipper, Mathias Gröbe, Johannes Kröger

### Beitragen
Bitte Information in der [CONTRIBUTE.md](CONTRIBUTE.md) beachten.

## English

### Description

Create and manage spatial filters that are applied to PostGIS vector layers in the current QGIS project. The plugin allows for filtered viewing and editing of the layer, with the filter being defined by a polygon geometry or a bounding box. It is possible to define exceptions for layers and display the filter geometry on the map canvas.

The development of this plugin was funded by Hessische Verwaltung für Bodenmanagement und Geoinformation (HVBG).

### Installation

You can install the plugin directly from the plugin repository. Otherwise, download a release and install the zipped plugin folder as a QGIS extension. There are no extra dependencies.

### Usage

Create a filter with the plugin by using a layer extent, selecting features on a layer, or drawing a rectangle or a rubber band polygon. It will be used immediately to filter all PostGIS vector layers accordingly. The filters are stored with the project and can be saved to the QGIS settings with a name. The spatial predicate can be changed from "intersects" to "contains" or "disjoint". In addition, PostGIS layers can be excluded from the filter. The filter geometry can also be shown on canvas with an adjustable style.

### License

General Public License v2

### Development

[WhereGroup](https://wheregroup.com/): Peter Gipper, Mathias Gröbe, Johannes Kröger

### Contribute

Please see [CONTRIBUTE.md](CONTRIBUTE.md).

