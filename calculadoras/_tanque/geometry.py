"""
Geometria derivada del tanque subterraneo (Sec. 3.1 de la especificacion).

CONVENCION DE DIMENSIONES (nota critica de la especificacion): "largo" y
"ancho" pueden interpretarse de tres formas distintas y el programa NO asume
ninguna -- el usuario elige explicitamente con `convencion_dimensiones`:

  - "cara_interior": largo/ancho = luz libre INTERIOR (lo que ocupa el agua).
        int = dato ;  ext = int + 2.espesor_muro
  - "cara_exterior": largo/ancho = dimension EXTERIOR total del cajon.
        ext = dato ;  int = ext - 2.espesor_muro
  - "eje_a_eje":      largo/ancho = distancia entre EJES (centros) de muros
        opuestos.       ext = dato + espesor_muro ;  int = ext - 2.espesor_muro

ADVERTENCIA SOBRE LA FUENTE: la especificacion trae un caso de prueba (Sec. 8,
Caso 1) rotulado "eje a eje" con entrada 4.70 x 2.70 m y espera un exterior de
5.10 x 3.10 m con muro de 0.20 m. Esa relacion (ext = dato + 2.espesor, no
+1.espesor) es matematicamente la de la convencion "cara_interior", no la de
"eje a eje" tal como se define arriba (la definicion estandar de "eje a eje"
suma UN espesor, no dos, para llegar al exterior). Se documenta aqui en vez de
forzar la formula de "eje_a_eje" para que cuadre con ese numero: el test de
este modulo (tests/test_tanque_geometry.py) reproduce el Caso 1 usando
convencion_dimensiones="cara_interior", que es la que sus numeros reproducen
exactamente. Confirmar con el ingeniero cual convencion se querio decir
realmente antes de dar por buena la etiqueta "eje a eje" del caso de prueba.
"""
from __future__ import annotations

CONVENCIONES = ("cara_interior", "cara_exterior", "eje_a_eje")


def dimensiones_ext_int(largo: float, ancho: float, espesor_muro: float, convencion: str) -> dict:
    if convencion == "cara_interior":
        int_x, int_y = largo, ancho
        ext_x, ext_y = int_x + 2 * espesor_muro, int_y + 2 * espesor_muro
    elif convencion == "cara_exterior":
        ext_x, ext_y = largo, ancho
        int_x, int_y = ext_x - 2 * espesor_muro, ext_y - 2 * espesor_muro
    elif convencion == "eje_a_eje":
        ext_x, ext_y = largo + espesor_muro, ancho + espesor_muro
        int_x, int_y = ext_x - 2 * espesor_muro, ext_y - 2 * espesor_muro
    else:
        raise ValueError(f"Convencion de dimensiones desconocida: {convencion!r}")
    return dict(ext_x=ext_x, ext_y=ext_y, int_x=int_x, int_y=int_y)


def geometria_derivada(d: dict) -> dict:
    """Geometria completa a partir del diccionario de entradas.

    Claves esperadas en `d`: largo, ancho, alto_libre, espesor_muro,
    espesor_losa_piso, espesor_losa_techo, ancho_ala (0 = sin ala),
    convencion_dimensiones, num_camaras (1 o 2), division_orientacion
    ("longitudinal" | "transversal" | "ninguna"), espesor_muro_divisorio.

    "longitudinal": el muro divisorio corre PARALELO al largo (se extiende
    toda la luz int_x) y divide el ancho (int_y) en dos. "transversal": el
    muro corre PERPENDICULAR al largo (se extiende todo el ancho int_y) y
    divide el largo (int_x) en dos -- p.ej. dos camaras de int_x/2 x int_y
    cada una, el caso tipico de un tanque mas largo que ancho.
    """
    dims = dimensiones_ext_int(d["largo"], d["ancho"], d["espesor_muro"], d["convencion_dimensiones"])
    ext_x, ext_y, int_x, int_y = dims["ext_x"], dims["ext_y"], dims["int_x"], dims["int_y"]
    if int_x <= 0 or int_y <= 0:
        raise ValueError(
            "Dimension interior no positiva: el espesor de muro es demasiado grande "
            "para las dimensiones dadas (revisar convencion_dimensiones)."
        )
    espesor_muro = d["espesor_muro"]
    if espesor_muro >= min(int_x, int_y) / 2:
        raise ValueError(
            "Espesor de muro >= mitad del ancho interior menor: geometria fisicamente "
            "inconsistente (las dos caras interiores se cruzarian)."
        )

    ancho_ala = d.get("ancho_ala", 0.0)
    if ancho_ala < 0:
        raise ValueError("El ancho del ala no puede ser negativo.")
    losa_x = ext_x + 2 * ancho_ala
    losa_y = ext_y + 2 * ancho_ala
    perimetro_exterior = 2 * (ext_x + ext_y)

    espesor_losa_piso = d["espesor_losa_piso"]
    espesor_losa_techo = d["espesor_losa_techo"]
    alto_libre = d["alto_libre"]
    altura_exterior = espesor_losa_piso + alto_libre + espesor_losa_techo

    # Envolvente exterior (para flotacion, sin incluir el ala -- ver
    # flotation.py: el ala se trata aparte, con pesos netos/sumergidos).
    volumen_exterior = ext_x * ext_y * altura_exterior

    num_camaras = int(d.get("num_camaras", 1))
    espesor_muro_div = d.get("espesor_muro_divisorio") or 0.0
    division = d.get("division_orientacion", "ninguna")

    volumen_interior_neto = int_x * int_y * alto_libre
    if num_camaras >= 2 and division != "ninguna" and espesor_muro_div > 0:
        if division == "longitudinal":
            # Muro paralelo al largo: se extiende toda la luz int_x y divide
            # el ancho (int_y) en dos.
            volumen_interior_neto -= espesor_muro_div * int_x * alto_libre
        elif division == "transversal":
            # Muro perpendicular al largo: se extiende todo el ancho (int_y)
            # y divide el largo (int_x) en dos.
            volumen_interior_neto -= espesor_muro_div * int_y * alto_libre

    volumen_concreto_estructura = volumen_exterior - volumen_interior_neto

    # Descomposicion por elemento (losa de piso, losa de techo, muros): a
    # diferencia de "volumen_concreto_estructura" (resta de envolventes,
    # informativo/de control -- ver test_tanque_geometry.py), esta version
    # permite asignar el peso unitario CORRECTO a cada elemento, porque en el
    # Tipo B (Sec. 4) las losas son concreto armado pero los muros son
    # mamposteria (peso unitario distinto). Para este caso (Tipo A, un solo
    # material), ambos metodos coinciden dentro de ~1% -- confirma que la
    # discrepancia de la Sec. 8 Caso 2 no es un problema de metodo.
    volumen_losa_piso = ext_x * ext_y * espesor_losa_piso
    volumen_losa_techo = ext_x * ext_y * espesor_losa_techo
    perimetro_eje_muro = perimetro_exterior - 4 * espesor_muro
    # longitud_muros_centerline: longitud total de eje de muro (perimetral +
    # divisorio), SIN multiplicar por espesor -- la usa volumen_muros (con el
    # espesor de cada muro, que puede diferir del divisorio) y tambien
    # cualquier elemento corrido bajo todos los muros con su PROPIA seccion
    # (p.ej. sobrecimiento/viga de riostra, Sec. "Sobrecimiento" de la memoria).
    longitud_muros_centerline = perimetro_eje_muro
    volumen_muros = perimetro_eje_muro * espesor_muro * alto_libre
    if num_camaras >= 2 and division != "ninguna" and espesor_muro_div > 0:
        luz_muro_divisorio = int_x if division == "longitudinal" else int_y
        longitud_muros_centerline += luz_muro_divisorio
        volumen_muros += luz_muro_divisorio * espesor_muro_div * alto_libre

    return dict(
        ext_x=ext_x, ext_y=ext_y, int_x=int_x, int_y=int_y,
        losa_x=losa_x, losa_y=losa_y, perimetro_exterior=perimetro_exterior,
        altura_exterior=altura_exterior, volumen_exterior=volumen_exterior,
        volumen_interior_neto=volumen_interior_neto,
        volumen_concreto_estructura=volumen_concreto_estructura,
        volumen_losa_piso=volumen_losa_piso, volumen_losa_techo=volumen_losa_techo,
        volumen_muros=volumen_muros, longitud_muros_centerline=longitud_muros_centerline,
        num_camaras=num_camaras, division_orientacion=division,
    )
