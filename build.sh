#!/usr/bin/env bash
set -e

echo "=== Installation des dépendances ==="
pip install -r requirements.txt

echo "=== Migrations base de données ==="
python manage.py migrate --noinput

echo "=== Fichiers statiques ==="
python manage.py collectstatic --noinput --clear

echo "=== Vérification de l'API ==="
python manage.py check

echo "=== Build terminé avec succès ==="
