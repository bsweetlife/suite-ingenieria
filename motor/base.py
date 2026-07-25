"""
Contratos base del suite.

Toda calculadora se describe con estos objetos. La interfaz (Streamlit) y el
reporte (PDF) se construyen automaticamente a partir de esta descripcion, de modo
que agregar una calculadora nueva NO requiere escribir nada de interfaz: basta con
declarar sus campos de entrada y su funcion de calculo.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Optional, Any


# --------------------------------------------------------------------------- #
#  Entrada
# --------------------------------------------------------------------------- #
@dataclass
class Campo:
    """Un dato de entrada que el usuario introduce."""
    clave: str                      # nombre interno (llave del diccionario)
    etiqueta: str                   # texto visible
    unidad: str = ""                # unidad mostrada al lado
    defecto: float = 0.0            # valor inicial
    ayuda: str = ""                 # tooltip / explicacion
    grupo: str = "Datos"            # agrupa campos en secciones
    tipo: str = "numero"            # "numero" | "entero" | "opcion"
    opciones: Optional[list] = None # solo para tipo "opcion"
    minimo: Optional[float] = None
    maximo: Optional[float] = None
    paso: Optional[float] = None
    avanzado: bool = False          # se esconde en un panel "avanzado"


# --------------------------------------------------------------------------- #
#  Salida
# --------------------------------------------------------------------------- #
@dataclass
class Valor:
    """Un valor calculado que se muestra en los resultados / reporte."""
    clave: str
    etiqueta: str
    valor: float
    unidad: str = ""
    formula: str = ""               # expresion legible (para la memoria)
    decimales: int = 3


@dataclass
class Chequeo:
    """Una verificacion normativa con su veredicto (cumple / no cumple)."""
    nombre: str
    izquierda: str                  # p.ej. "Vu1 = 0.11 kg/cm2"
    relacion: str                   # "<", ">", "<=", ">="
    derecha: str                    # p.ej. "Vc = 7.68 kg/cm2"
    cumple: bool
    comentario: str = ""


@dataclass
class Resultado:
    valores: list[Valor] = field(default_factory=list)
    chequeos: list[Chequeo] = field(default_factory=list)
    resumen: list[Valor] = field(default_factory=list)   # diseno final
    notas: list[str] = field(default_factory=list)
    armado_texto: str = ""                               # armado sugerido (texto)

    @property
    def conforme(self) -> bool:
        return all(c.cumple for c in self.chequeos)


# --------------------------------------------------------------------------- #
#  Calculadora
# --------------------------------------------------------------------------- #
@dataclass
class Calculadora:
    id: str
    nombre: str
    categoria: str
    descripcion: str
    campos: list[Campo]
    funcion: Callable[[dict], Resultado]
    referencia: str = ""
    icono: str = "🧮"
    # Tablas de referencia opcionales: cada una es
    #   {"titulo": str, "nota": str, "columnas": [str], "filas": [[val, ...]]}
    tablas_referencia: list = field(default_factory=list)
    # Guia rapida de suelo opcional: {nombre_material: sigma_adm_kg_cm2}
    guia_suelo: dict = field(default_factory=dict)
    # Campo destino del auto-relleno de la guia de suelo (clave de un Campo)
    guia_suelo_destino: str = ""
    # Esquema opcional: funcion(entradas, resultado) -> list[dict de primitivas]
    esquema: Optional[Callable] = None
    # Dimensionamiento asistido opcional: funcion(entradas) -> {clave: valor sugerido}
    sugerir: Optional[Callable] = None

    def valores_defecto(self) -> dict:
        return {c.clave: c.defecto for c in self.campos}
