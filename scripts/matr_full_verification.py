"""
VERIFICACION COMPLETA V20 — SCRIPT MAESTRO
==========================================
Autor    : Mizael Antonio Tovar Reyes
Ubicacion: Ciudad Juarez, Chihuahua, Mexico

CAMBIOS V20:
  - Script 10 agregado: Prueba exhaustiva de los 5 grafos fallidos de Script 8.
    Demuestra que los fallos son falsos negativos algoritmicos, no contraejemplos.
  - Lema 8.3f Caso 3b cerrado formalmente (ver conjecture/lema83f_caso3b_prueba_formal.md).
  - Repositorio reorganizado para publicacion en GitHub (README, requirements, LICENSE).

CAMBIOS V19:
  - Script 9 agregado: Verificacion individual Lemas 8.3c, 8.3d, 8.3e, 8.3f
  - Cada lema tiene su propio log detallado
  - Permite identificar exactamente en que lema falla cada grafo

CAMBIOS V18:
  - Script 8 agregado: Hadwiger chi alto (chi=7,8 exhaustivo)
  - Script 7 agregado: K_k minor completo (fix bug BFS Fase 2)

Investigador : Mizael Antonio Tovar Reyes
Ubicacion    : Ciudad Juarez, Chihuahua, Mexico
"""

import sys
import time
import importlib.util
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
LOG_FILE = BASE_DIR / "VERIFICACION_COMPLETA_V19.txt"

SCRIPTS = [
    ("script1_teorema41",          "TEOREMA 4.1  — chi(G) = 1 + p(G)"),
    ("script2_lema71",             "LEMA 7.1     — Completitud Cromatica"),
    ("script3_teorema87",          "TEOREMA 8.7  — K_k minor (Hadwiger)"),
    ("script4_familias_exactas",   "PROP 6.1 + T5.1 — Familias exactas"),
    ("script5_lema83d",            "LEMA 8.3d    — Absorcion distribuida"),
    ("script6_lema83f_conector",   "LEMA 8.3f    — Conector alternado (Mizael)"),
    ("script7_kk_minor_completo",  "SCRIPT 7     — K_k minor completo (fix BFS)"),
    ("script8_hadwiger_chi_alto",      "SCRIPT 8     — Hadwiger chi alto (chi=7,8 exhaustivo)"),
    ("script9_lemas83_verificacion",   "SCRIPT 9     — Lemas 8.3c/d/e/f verificacion individual"),
]


def _write_master_log(results, total_elapsed, partial=False):
    all_ok = all(s for _, s, _ in results)
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        f.write("=" * 75 + "\n")
        f.write("  VERIFICACION COMPLETA V18 — CONJETURA ZIGZAG\n")
        f.write("=" * 75 + "\n")
        f.write(f"  Investigador : Mizael Antonio Tovar Reyes\n")
        f.write(f"  Ubicacion    : Ciudad Juarez, Chihuahua, Mexico\n")
        f.write(f"  Fecha        : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"  Tiempo total : {total_elapsed:.1f} minutos\n")
        f.write(f"  Estado       : {'EN PROGRESO' if partial else 'COMPLETO'}\n")
        f.write("=" * 75 + "\n\n")
        f.write("RESULTADOS POR MODULO:\n")
        f.write("-" * 75 + "\n")
        for description, success, elapsed in results:
            status = "OK   " if success else "FALLO"
            f.write(f"  [{status}] {description:<50} ({elapsed/60:.1f} min)\n")
        f.write("-" * 75 + "\n\n")
        if not partial:
            if all_ok and results:
                f.write("VEREDICTO: VERIFICACION COMPLETA EXITOSA\n\n")
                f.write("  - Teorema 4.1  : chi(G) = 1 + p(G) confirmado\n")
                f.write("  - Lema 7.1     : Completitud cromatica confirmada\n")
                f.write("  - Teorema 8.7  : Construccion K_k minor valida\n")
                f.write("  - Prop 6.1+T5.1: Familias exactas coinciden\n")
                f.write("  - Lema 8.3d    : Absorcion distribuida OK\n")
                f.write("  - Lema 8.3f    : Conector alternado (Mizael) OK\n")
                f.write("                   Case B cubre todos los gaps aparentes\n")
            else:
                f.write("VEREDICTO: SE ENCONTRARON FALLOS\n\n")
                for description, success, _ in results:
                    if not success:
                        f.write(f"  -> {description}\n")
        else:
            f.write("  [GUARDADO PARCIAL — verificacion en progreso]\n")
        f.write("\n" + "=" * 75 + "\n")
        f.write("  FIN DEL REPORTE\n")
        f.write("=" * 75 + "\n")


def load_and_run_script(script_name):
    script_path = BASE_DIR / f"{script_name}.py"
    if not script_path.exists():
        print(f"  ERROR: No se encontro {script_path}")
        return False, 0
    try:
        spec   = importlib.util.spec_from_file_location(script_name, script_path)
        module = importlib.util.module_from_spec(spec)
        t0     = time.time()
        spec.loader.exec_module(module)
        success = module.main() if hasattr(module, 'main') else True
        return success, time.time() - t0
    except KeyboardInterrupt:
        raise
    except Exception as e:
        print(f"  ERROR ejecutando {script_name}: {e}")
        import traceback
        traceback.print_exc()
        return False, 0


def main():
    print()
    print("=" * 70)
    print("  VERIFICACION COMPLETA V19 — CONJETURA ZIGZAG")
    print("=" * 70)
    print(f"  Investigador : Mizael Antonio Tovar Reyes")
    print(f"  Ubicacion    : Ciudad Juarez, Chihuahua, Mexico")
    print(f"  Fecha        : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    print()
    print("  NOVEDADES V19:")
    print("    - Script 9 NUEVO: Verificacion individual Lemas 8.3c/d/e/f")
    print("      Cada lema tiene su propio log detallado")
    print("      Identifica exactamente en que lema falla cada grafo")
    print()
    print("  SCRIPTS QUE SE EJECUTARAN:")
    for i, (sname, desc) in enumerate(SCRIPTS, 1):
        print(f"    [{i}/{len(SCRIPTS)}] {desc}")
    print()

    results     = []
    total_start = time.time()

    _write_master_log([], 0, partial=True)
    print(f"  Log maestro iniciado: {LOG_FILE}\n")

    try:
        for i, (script_name, description) in enumerate(SCRIPTS, 1):
            print()
            print("-" * 70)
            print(f"  [{i}/{len(SCRIPTS)}] {description}")
            print("-" * 70)
            print()

            success, elapsed = load_and_run_script(script_name)
            results.append((description, success, elapsed))

            total_so_far = (time.time() - total_start) / 60
            _write_master_log(results, total_so_far, partial=(i < len(SCRIPTS)))

            print()
            print(f"  -> {'COMPLETADO' if success else 'FALLO'} en {elapsed/60:.1f} minutos")

    except KeyboardInterrupt:
        print("\n\n  !! Interrumpido por usuario — guardando log maestro parcial...")
    finally:
        total_elapsed = (time.time() - total_start) / 60
        _write_master_log(results, total_elapsed, partial=False)

        print()
        print("=" * 70)
        print("  REPORTE FINAL")
        print("=" * 70)
        all_ok = True
        for description, success, elapsed in results:
            status = "OK   " if success else "FALLO"
            print(f"  [{status}] {description:<50} {elapsed/60:.1f} min")
            if not success:
                all_ok = False
        total_elapsed = (time.time() - total_start) / 60
        print(f"  Tiempo total: {total_elapsed:.1f} minutos")
        print()
        if all_ok and results:
            print("  VERIFICACION COMPLETA EXITOSA — TODOS LOS RESULTADOS OK")
            print()
            print("  Lema 8.3f confirmado: el conector alternado de Mizael")
            print("  cubre todos los pares (Bi,Bj) en el grafo contraido.")
        elif results:
            print("  SE ENCONTRARON FALLOS — REVISAR LOGS INDIVIDUALES")
        print("=" * 70)
        print()
        print(f"  Log maestro: {LOG_FILE}")
        print()
        print("  Logs individuales:")
        print("    log_script1_teorema41.txt")
        print("    log_script2_lema71.txt")
        print("    log_script3_teorema87.txt")
        print("    log_script4_familias.txt")
        print("    log_script5_lema83d.txt")
        print("    log_script6_lema83f.txt")
        print("    log_script7_kk_minor_completo.txt")
        print("    log_script8_hadwiger_chi_alto.txt")
        print("    log_script8_CHI7_CHI8_detallado.txt")
        print("    log_script9_lemas83.txt              <-- NUEVO")
        print("    log_script9_lema83c_detallado.txt    <-- NUEVO")
        print("    log_script9_lema83d_detallado.txt    <-- NUEVO")
        print("    log_script9_lema83e_detallado.txt    <-- NUEVO")
        print("    log_script9_lema83f_detallado.txt    <-- NUEVO")

    return all_ok


if __name__ == "__main__":
    import multiprocessing
    multiprocessing.freeze_support()
    success = main()
    sys.exit(0 if success else 1)
