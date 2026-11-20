# Runtime hook de PyInstaller para el backend congelado (lo carga electron-builder.backend.spec).
# El backend relanza procesos hijo como `sys.executable -B -m <modulo> ...` (p. ej. el lector
# aislado del almacén, app.services.readers.worker). En un build congelado sys.executable es
# drakter-backend, que ignora -m y arrancaría otro servidor. Este hook atiende ese caso:
# ejecuta el módulo pedido (que ya va dentro del bundle) y termina.
import sys

if getattr(sys, "frozen", False):
    _argv = sys.argv[1:]
    while _argv and _argv[0] in ("-B", "-I", "-u", "-E", "-s"):
        _argv = _argv[1:]
    if len(_argv) >= 2 and _argv[0] == "-m":
        import runpy

        _module = _argv[1]
        sys.argv = [_module, *_argv[2:]]
        runpy.run_module(_module, run_name="__main__", alter_sys=True)
        sys.exit(0)
