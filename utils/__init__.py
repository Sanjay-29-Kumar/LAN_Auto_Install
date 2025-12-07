"""utils package marker

Having an __init__.py makes `utils` an explicit package which avoids
ambiguous import resolution when running top-level scripts.
"""

__all__ = ["config", "dynamic_installer", "virus_scanner"]
