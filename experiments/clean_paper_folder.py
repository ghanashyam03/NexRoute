"""
Clean Paper Folder Utility for NexRoute Paper.

Keeps ONLY essential LaTeX files, official Elsevier style packages/logos,
and referenced publication figures in C:\\Users\\ghana\\OneDrive\\Desktop\\NexRoute_Paper.
Removes large 15MB gr1.eps, duplicate EPS logos, build artifacts (.aux, .log, .synctex), and unreferenced exploratory plots.
"""

import os
from pathlib import Path
import shutil

PAPER_DIR = Path(r"C:\Users\ghana\OneDrive\Desktop\NexRoute_Paper")
FIG_DIR = PAPER_DIR / "figures"

# Files to keep in top-level PAPER_DIR
KEEP_TOP_LEVEL = {
    "PROCS_KES2026.tex",
    "README",
    "ecrc.sty",
    "elsarticle.cls",
    "elsarticle-harv.bst",
    "framed.sty",
    "SDlogo-3p.pdf",
    "elsevier-logo-3p.pdf",
    "Procs.pdf",
    "gr1.pdf",
    "figures"
}

# Figures to keep in FIG_DIR
KEEP_FIGURES = {
    "figure_mechanism_vsl_interference.pdf",
    "figure_mechanism_vsl_interference.png",
    "figure_threshold_gating_mechanism.pdf",
    "figure_threshold_gating_mechanism.png",
    "figure_threshold_gating_sensitivity.pdf",
    "figure_threshold_gating_sensitivity.png"
}


def clean_paper_directory():
    print(f"Cleaning paper directory: {PAPER_DIR}...")
    removed_bytes = 0
    removed_count = 0

    # 1. Clean top-level directory
    for item in PAPER_DIR.iterdir():
        if item.name not in KEEP_TOP_LEVEL:
            try:
                sz = item.stat().st_size if item.is_file() else 0
                if item.is_file():
                    item.unlink()
                elif item.is_dir():
                    shutil.rmtree(item)
                removed_bytes += sz
                removed_count += 1
                print(f"  Removed top-level: {item.name} ({sz / 1024 / 1024:.2f} MB)")
            except Exception as e:
                print(f"  Error removing {item.name}: {e}")

    # 2. Clean figures directory
    if FIG_DIR.exists():
        for item in FIG_DIR.iterdir():
            if item.name not in KEEP_FIGURES:
                try:
                    sz = item.stat().st_size
                    item.unlink()
                    removed_bytes += sz
                    removed_count += 1
                    print(f"  Removed figure: {item.name} ({sz / 1024:.1f} KB)")
                except Exception as e:
                    print(f"  Error removing figure {item.name}: {e}")

    print(f"\nCleanup Complete! Removed {removed_count} files/folders, freeing {removed_bytes / 1024 / 1024:.2f} MB.")


if __name__ == "__main__":
    clean_paper_directory()
