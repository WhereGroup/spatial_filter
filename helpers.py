from typing import Any, List

from qgis.core import QgsSettings

from .settings import GROUP


def saveValue(key: str, value: Any):
    settings = QgsSettings()
    settings.beginGroup(GROUP)
    settings.setValue(key, value)
    settings.endGroup()


def readValue(key: str, defaultValue: Any = None) -> Any:
    settings = QgsSettings()
    settings.beginGroup(GROUP)
    value = settings.value(key, defaultValue)
    settings.endGroup()
    return value


def allValues(defaultValue: Any = None) -> List[Any]:
    settings = QgsSettings()
    settings.beginGroup(GROUP)
    values = [settings.value(key, defaultValue) for key in settings.allKeys()]
    settings.endGroup()
    return values


def removeValue(key: str) -> None:
    settings = QgsSettings()
    settings.beginGroup(GROUP)
    settings.remove(key)
    settings.endGroup()



def refreshLayerTree() -> None:
    pass
