"""Configuracion comun de los tests: que 'import server' funcione desde la carpeta tests/."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
