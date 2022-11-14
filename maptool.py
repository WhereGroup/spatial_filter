from qgis.gui import QgsMapTool, QgsRubberBand
from qgis.core import QgsGeometry, QgsWkbTypes
from qgis.utils import iface

from PyQt5.QtCore import Qt, QPoint, pyqtSignal


class PolygonTool(QgsMapTool):
    sketchFinished = pyqtSignal(QgsGeometry)

    def __init__(self):
        self.rubberBand = None
        self.canvas = iface.mapCanvas()
        super().__init__(self.canvas)

    def reset(self):
        if self.rubberBand:
            self.rubberBand.reset()
            self.canvas.scene().removeItem(self.rubberBand)
            self.rubberBand = None

    def canvasPressEvent(self, event):
        pass

    def canvasReleaseEvent(self, event):
        x = event.pos().x()
        y = event.pos().y()
        thisPoint = QPoint(x, y)

        mapToPixel = self.canvas.getCoordinateTransform()  # QgsMapToPixel instance

        if event.button() == Qt.LeftButton:
            if not self.rubberBand:
                self.rubberBand = QgsRubberBand(self.canvas, geometryType=QgsWkbTypes.PolygonGeometry)
                self.rubberBand.setLineStyle(Qt.DashLine)
                self.rubberBand.setWidth(2)
            self.rubberBand.addPoint(mapToPixel.toMapCoordinates(thisPoint))

        elif event.button() == Qt.RightButton:
            if self.rubberBand and self.rubberBand.numberOfVertices() > 3:
                # Finish rubberband sketch
                self.rubberBand.removeLastPoint()
                geometry = self.rubberBand.asGeometry()
                self.sketchFinished.emit(geometry)
            self.reset()
            self.canvas.refresh()

    def canvasMoveEvent(self, event):
        if not self.rubberBand:
            return
        x = event.pos().x()
        y = event.pos().y()
        thisPoint = QPoint(x, y)
        mapToPixel = self.canvas.getCoordinateTransform()
        self.rubberBand.movePoint(self.rubberBand.numberOfVertices() - 1, mapToPixel.toMapCoordinates(thisPoint))

    def deactivate(self):
        self.reset()
        QgsMapTool.deactivate(self)
