"""Health check: import every analysis package, print its version, report SETUP OK or failures."""
import importlib
import sys

# (pip name, import name)
PACKAGES = [
    ("pandas", "pandas"),
    ("numpy", "numpy"),
    ("geopandas", "geopandas"),
    ("rasterio", "rasterio"),
    ("scikit-image", "skimage"),
    ("scipy", "scipy"),
    ("scikit-learn", "sklearn"),
    ("statsmodels", "statsmodels"),
    ("pulp", "pulp"),
    ("libpysal", "libpysal"),
    ("esda", "esda"),
    ("plotly", "plotly"),
    ("streamlit", "streamlit"),
    ("pdfplumber", "pdfplumber"),
    ("pyarrow", "pyarrow"),
    ("requests", "requests"),
]


def main():
    print(f"Python {sys.version.split()[0]} at {sys.executable}")
    failed = []
    for pip_name, module_name in PACKAGES:
        try:
            module = importlib.import_module(module_name)
            version = getattr(module, "__version__", "unknown")
            print(f"  OK    {pip_name:<14} {version}")
        except Exception as exc:
            failed.append(pip_name)
            print(f"  FAIL  {pip_name:<14} {type(exc).__name__}: {exc}")

    if failed:
        print("SETUP FAILED: " + ", ".join(failed))
        sys.exit(1)
    print("SETUP OK")


if __name__ == "__main__":
    main()
