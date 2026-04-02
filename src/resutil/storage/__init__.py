from .storage import Storage

__all__ = ["GCS", "GDrive", "ResutilServerStorage", "Storage"]


def __getattr__(name):
    if name == "GCS":
        from .gcs.gcs import GCS
        return GCS
    if name == "GDrive":
        from .gdrive.gdrive import GDrive
        return GDrive
    if name == "ResutilServerStorage":
        from .server.server import ResutilServerStorage
        return ResutilServerStorage
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
