from pathlib import Path
from datetime import timedelta
import os
import dj_database_url

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-+z+ho1-s^ego0t&*+&m0az+#9zw7hxl9^shgk0p*d6spc%7fym')

DEBUG = os.environ.get('DEBUG', 'False') == 'True'

ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', '*').split(',')

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'cloudinary_storage',        # doit être AVANT staticfiles
    'django.contrib.staticfiles',
    'cloudinary',
    'rest_framework',
    'rest_framework_simplejwt',
    'corsheaders',
    'api',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

# ─── BASE DE DONNÉES ───────────────────────────────────────────
# PostgreSQL via DATABASE_URL (Render), fallback SQLite en dev local
DATABASE_URL = os.environ.get('DATABASE_URL')
if DATABASE_URL:
    DATABASES = {
        'default': dj_database_url.parse(
            DATABASE_URL,
            conn_max_age=600,
            conn_health_checks=True,
        )
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'fr-fr'
TIME_ZONE = 'Africa/Porto-Novo'
USE_I18N = True
USE_TZ = True

# ─── FICHIERS STATIQUES ────────────────────────────────────────
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'


# ─── IMAGES — CLOUDINARY ───────────────────────────────────────
CLOUDINARY_STORAGE = {
    'CLOUD_NAME': os.environ.get('CLOUDINARY_CLOUD_NAME', 'dg0qjrn62'),
    'API_KEY':    os.environ.get('CLOUDINARY_API_KEY', '319389817628572'),
    'API_SECRET': os.environ.get('CLOUDINARY_API_SECRET', ''),
}

# Django 5.1+ a supprimé le support de DEFAULT_FILE_STORAGE et
# STATICFILES_STORAGE (dépréciés depuis 4.2) : ces réglages étaient
# silencieusement ignorés avec Django 5.2.3, faisant retomber Django
# sur le stockage fichier local par défaut (éphémère sur Render) sans
# aucune erreur visible. STORAGES est la seule façon valide de
# configurer le stockage media/statique sur cette version.
STORAGES = {
    "default": {
        "BACKEND": "cloudinary_storage.storage.MediaCloudinaryStorage",
    },
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
}

# django-cloudinary-storage 0.3.0 accède encore directement à
# settings.STATICFILES_STORAGE dans sa propre commande collectstatic
# personnalisée (pas via le dict STORAGES), et plante avec une
# AttributeError si ce réglage est totalement absent. On le garde en
# parallèle de STORAGES, sans conflit : Django utilise STORAGES,
# cette ligne sert uniquement à satisfaire ce contrôle interne de la
# librairie tierce.
#
# Pas de compression whitenoise ici : cette API REST n'a quasiment
# aucun fichier statique personnalisé (juste l'admin Django intégré),
# et les variantes compressées de whitenoise plantaient sur des
# fichiers admin standards (problème de résolution d'import CSS
# relatif et/ou de timing de compression concurrente).
STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.StaticFilesStorage'

MEDIA_URL = '/media/'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

AUTH_USER_MODEL = 'api.Utilisateur'

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
}

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(days=7),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=30),
}

# ─── CORS ──────────────────────────────────────────────────────
CORS_ALLOWED_ORIGINS = [
    'https://swift-africa-app-front-nine.vercel.app',
    'https://swift-africa-app-front.vercel.app',
    'https://swift-africa-app.vercel.app',
    'http://localhost:3000',
    'http://localhost:3001',
    'http://127.0.0.1:3000',
]

CORS_ALLOWED_ORIGIN_REGEXES = [
    r'^https://swift-africa-app(-front)?.*\.vercel\.app$',
]

CORS_ALLOW_CREDENTIALS = True

CORS_ALLOW_HEADERS = [
    'accept',
    'authorization',
    'content-type',
    'origin',
    'x-requested-with',
]


