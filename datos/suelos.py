"""
Tablas de referencia de suelos (valores aproximados de manual).

Transcritas de las tablas clasicas de propiedades de suelos:
  - Propiedades: angulo de friccion interna (Ø), cohesion (c) y peso especifico (γ).
  - Capacidad portante admisible (σadm) por tipo de material y granulometria.

ADVERTENCIA: son valores ORIENTATIVOS de referencia. El σadm y γ de diseño deben
tomarse del estudio geotecnico del proyecto, no de esta tabla.
"""

# Tabla de propiedades aproximadas (izquierda de la imagen)
# Columnas: Material | Ø friccion (°) | c cohesion (kg/cm²) | γ peso esp. (tn/m³)
TABLA_PROPIEDADES = {
    "titulo": "Propiedades aproximadas del suelo (Ø, c, γ)",
    "nota": "Ø = ángulo de fricción interna · c = cohesión · γ = peso específico. Valores orientativos.",
    "columnas": ["Material", "Ø (°)", "c (kg/cm²)", "γ (tn/m³)"],
    "filas": [
        ["Gravas compactas", "35", "—", "2.0"],
        ["Gravas sueltas", "33", "—", "—"],
        ["Arena compacta", "32", "0.01", "2.0"],
        ["Arena suelta", "30", "—", "1.8"],
        ["Limo arenoso", "25", "—", "—"],
        ["Arcilla arenosa", "20", "0.02", "2.2"],
        ["Arcilla magra", "—", "0.05", "—"],
        ["Arcilla grasa", "—", "0.10", "—"],
        ["Arcilla muy grasa", "15", "hasta 0.50", "—"],
        ["Tierra orgánica", "—", "—", "2.2"],
    ],
}

# Tabla de capacidad portante admisible (derecha de la imagen)
# Columnas: Material | Ø grano (mm) | σadm (kg/cm²)
TABLA_CAPACIDAD = {
    "titulo": "Capacidad portante admisible σadm por material",
    "nota": "σadm orientativo según tipo de material y granulometría. Confirmar con estudio geotécnico.",
    "columnas": ["Material", "Ø grano (mm)", "σadm (kg/cm²)"],
    "filas": [
        ["Arcillas", "0.0006", "0.45"],
        ["Limos finos", "0.002", "0.80"],
        ["Limos medios", "0.006", "0.80"],
        ["Limos gruesos", "0.020", "0.80"],
        ["Arenas finas", "0.060", "1.00"],
        ["Arenas medias", "0.200", "1.50"],
        ["Arenas gruesas", "0.600", "2.50"],
        ["Gravas finas", "2", "3.00"],
        ["Gravas medias", "6", "4.50"],
        ["Gravas gruesas", "60", "6.00"],
        ["Canto rodado", "—", "6.00"],
        ["Roca disgregable", "200", "8.00"],
        ["Roca homogénea", "—", "> 30.00"],
    ],
}

# Guia rapida: material -> σadm de referencia (kg/cm²), tomada de la tabla de capacidad.
GUIA_SIGMA_ADM = {
    "Arcillas": 0.45,
    "Limos": 0.80,
    "Arenas finas": 1.00,
    "Arenas medias": 1.50,
    "Arenas gruesas": 2.50,
    "Gravas finas": 3.00,
    "Gravas medias": 4.50,
    "Gravas gruesas": 6.00,
    "Canto rodado": 6.00,
    "Roca disgregable": 8.00,
    "Roca homogénea": 30.00,
}

TABLAS_SUELO = [TABLA_CAPACIDAD, TABLA_PROPIEDADES]
