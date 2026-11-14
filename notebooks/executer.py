"""Exécute en place les notebooks de ce dossier, pour que leurs sorties soient visibles sur GitHub.

Depuis la racine du dépôt, tous les notebooks ou ceux nommés
    venv/bin/python notebooks/executer.py
    venv/bin/python notebooks/executer.py notebooks/02_data_understanding.ipynb

Le noyau communique par des sockets IPC créées dans un dossier temporaire, ce qui évite le
transport TCP sans chiffrement et ne laisse aucun fichier dans le dépôt.
"""

import sys
import tempfile
from pathlib import Path

import nbformat
from jupyter_client.manager import KernelManager
from nbclient import NotebookClient

DOSSIER = Path(__file__).resolve().parent


def executer(chemin: Path) -> None:
    carnet = nbformat.read(chemin, as_version=4)
    with tempfile.TemporaryDirectory() as temporaire:
        noyau = KernelManager(kernel_name="python3", transport="ipc", ip=str(Path(temporaire) / "noyau"))
        try:
            NotebookClient(carnet, km=noyau, timeout=900, record_timing=False,
                           resources={"metadata": {"path": str(DOSSIER)}}).execute()
        finally:
            if noyau.has_kernel:
                noyau.shutdown_kernel(now=True)
    nbformat.write(carnet, chemin)


if __name__ == "__main__":
    chemins = [Path(c) for c in sys.argv[1:]] or sorted(DOSSIER.glob("*.ipynb"))
    for chemin in chemins:
        executer(chemin)
        print(f"{chemin.name} exécuté")
