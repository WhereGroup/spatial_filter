# HVBG Filterplugin
Please scroll down for the English version.
## Deutsch

### Beschreibung

Erstellt und verwaltet räumliche Filter für vektorbasierte PostGIS Layer im aktuellen QGIS Projekt. Damit lässt sich die Anzeige und Bearbeitung der Layer auf eine bestimmte Polygongeometrie oder deren minimal umfassendes Rechteck begrenzen. Es ist möglich Ausnahmen für einzelne Layer zu definieren und die Filtergeometrie anzuzeigen.

Die Entwicklung dieses Plugins wurde von der Hessische Verwaltung für Bodenmanagement und Geoinformation (HVBG) finanziert.

### Installation

Die Installation ist direkt aus dem QGIS Repository möglich. Alternativ kann hier ein Release heruntergeladen werden und der gezippte Order manuell als QGIS-Erweiterung installiert werden. Es sind keine weiteren Abhängigkeiten vorhanden.

### Nutzung
Erstellen Sie einen Filter mit dem Plugin, indem Sie eine Ebenenausdehnung verwenden, ein Objekt auswählen und ein Rechteck oder eine Freihandgeometrie zeichnen. Er wird sofort zum Filtern aller PostGIS-Vektorlayer verwendet. Die Filter werden mit dem Projekt gespeichert und können zusätzlich mit einem Namen in den QGIS-Einstellungen abgelegt werden. Es ist möglich, das räumliche Prädikat von schneidet auf enthält oder disjunkt zu ändern. Außerdem können einzelne PostGIS-Ebenen vom Filter ausgeschlossen werden. Die Filtergeometrie kann auch auf der Karten mit einem anpassbaren Stil dargestellt werden.

### Lizenz

General Public License v2

### Beitragen
Bitte Information in der [CONTRIBUTE.md](CONTRIBUTE.md) beachten.

## English

### Description

Create and manage spatial filters that are applied to PostGIS vector layers in the current project. It allows for the limited viewing and editing of the layer by a polygon geometry or its bounding box. It is possible to define exceptions for layers and display the filter geometry.

The development of this plugin was funded by the Hessische Verwaltung für Bodenmanagement und Geoinformation (HVBG).

### Installation
You can install the plugin directly from the plugin repository. Otherwise, download a release and install the zipped Plugin folder as a QGIS extension. There are no further dependencies.

### Usage

Create a filter with the plugin by using a layer extent, selecting a feature, and drawing a rectangle or a rubber band. It will be used immediately to filter all PostGIS vector layers. The filters are stored with the project and can be saved to the QGIS settings with a name. Changing the spatial predicate from intersects to contains or disjoint is possible. In addition, PostGIS layers can be excluded from the filter. The filter geometry can also be shown on canvas with an adjustable style.


### License

General Public License v2

### Contribute

Please see [CONTRIBUTE.md](CONTRIBUTE.md).

