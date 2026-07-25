"""
Validacion del motor de la zapata contra los 24 valores de la hoja Excel original
(Calculos_de_Zapatas__Enrique_Araujo_.xls, hoja "Cálculo de Zap C con Pedestal C").

Ejecutar:   python -m pytest tests/ -v      (o)     python tests/test_zapata.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from calculadoras.zapata_pedestal import _motor

ENTRADA = dict(
    Pu=20870, M=1101.22, sigma_adm=1.5, gamma_asumido=1.2, fc=210, fy=4200,
    H=2.0, gamma_s=2200, gamma_c=2500, b_ped=35, mu=0.1448, B_adop=1.1, d_adop=35,
    phi_corte=0.85, phi_aplast=0.70, phi_flexion=0.90, ju=0.90,
)

# Valores tomados directamente del Excel
EXCEL = {
    "Areq": 16696, "B_calc": 129.213, "sigma_u": 1.25, "d_min": 5.7378,
    "n": 37.5, "c": 2.5, "Mu": 96679.6875, "Vc": 7.6804, "Vu1": 0.105,
    "Vu2": 14745, "bo": 280, "Vc1": 15.3609, "Vu3": 1.7701, "Ag": 1225,
    "Pu_max_col": 153063.75, "Pu_max_base": 948.4536, "Q1": 1058.75,
    "Q2": 3947.625, "Q": 5006.375, "gamma_real": 1.2399, "As": 9.2485,
    "As_m": 8.4077,
}


def test_valores_coinciden_con_excel():
    r = _motor(ENTRADA)
    for clave, esperado in EXCEL.items():
        obtenido = r[clave]
        tol = max(0.01, abs(esperado) * 0.001)
        assert abs(obtenido - esperado) < tol, (
            f"{clave}: obtenido {obtenido:.4f} != Excel {esperado:.4f}")


def test_verificaciones_del_ejemplo_cumplen():
    r = _motor(ENTRADA)
    assert r["corte_ok"]
    assert r["punz_ok"]
    assert r["aplast_col_ok"]
    assert r["aplast_base_ok"]


if __name__ == "__main__":
    test_valores_coinciden_con_excel()
    test_verificaciones_del_ejemplo_cumplen()
    print("OK — el motor reproduce exactamente los 24 valores del Excel.")
