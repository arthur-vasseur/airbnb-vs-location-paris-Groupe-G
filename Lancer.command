#!/bin/bash
# Lanceur Mac : double-cliquer sur ce fichier.
# Au premier lancement, installe les bibliothèques (1 à 2 minutes), puis ouvre l'application.

cd "$(dirname "$0")" || exit 1

if ! command -v python3 >/dev/null 2>&1 || \
   ! python3 -c 'import sys; sys.exit(sys.version_info < (3, 11))'; then
    echo "Python 3.11 ou plus récent est nécessaire."
    echo "Installez-le depuis https://www.python.org/downloads/ puis relancez ce fichier."
    read -r -p "Appuyez sur Entrée pour fermer."
    exit 1
fi

if [ ! -x .venv/bin/streamlit ]; then
    echo "Premier lancement : installation des bibliothèques…"
    python3 -m venv .venv && .venv/bin/pip install -q -r requirements.txt || {
        echo "L'installation a échoué."
        read -r -p "Appuyez sur Entrée pour fermer."
        exit 1
    }
fi

echo "L'application s'ouvre dans le navigateur. Fermez cette fenêtre pour l'arrêter."
(sleep 4 && open http://localhost:8501) &
.venv/bin/streamlit run app.py --server.headless true --server.port 8501
