from qgis.gui import QgsMapTool, QgsRubberBand
from qgis.core import QgsGeometry, QgsWkbTypes
from PyQt5.QtCore import Qt, QPoint, pyqtSignal
from qgis.utils import iface


class PolygonTool(QgsMapTool):
    sketchFinished = pyqtSignal(QgsGeometry)

    def __init__(self):
        self.canvas = iface.mapCanvas()
        super().__init__(self.canvas)
        self.rubberBand = None

    def reset(self):
        if self.rubberBand:
            self.rubberBand.reset()
            self.canvas.scene().removeItem(self.rubberBand)
            self.rubberBand = None

    def canvasPressEvent(self, event):
        pass

    def canvasReleaseEvent(self, event):

        # Get the click coordinates
        x = event.pos().x()
        y = event.pos().y()
        thisPoint = QPoint(x, y)

        # QgsMapToPixel instance - t
        mapToPixel = self.canvas.getCoordinateTransform()

        if event.button() == Qt.LeftButton:
            if self.rubberBand is None:
                # Create line rubber band
                self.rubberBand = QgsRubberBand(self.canvas, geometryType=QgsWkbTypes.PolygonGeometry)
                self.rubberBand.setLineStyle(Qt.DashLine)
                self.rubberBand.setWidth(2)

            self.rubberBand.addPoint(mapToPixel.toMapCoordinates(thisPoint))

        elif event.button() == Qt.RightButton:
            if self.rubberBand:
                if self.rubberBand.numberOfVertices() > 3:
                    # Finish rubberband sketch
                    self.rubberBand.removeLastPoint()
                    geometry = self.rubberBand.asGeometry()

                    self.sketchFinished.emit(geometry)

            self.reset()
            self.canvas.refresh()

    def canvasMoveEvent(self, event):
        x = event.pos().x()
        y = event.pos().y()
        thisPoint = QPoint(x, y)

        if self.rubberBand:
            self.mapToPixel = self.canvas.getCoordinateTransform()
            self.rubberBand.movePoint(self.rubberBand.numberOfVertices() - 1,
                                      self.mapToPixel.toMapCoordinates(thisPoint))

    def deactivate(self):
        self.reset()
        QgsMapTool.deactivate(self)
