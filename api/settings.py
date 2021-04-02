"""
Django settings for api project.

Generated by 'django-admin startproject' using Django 3.1.6.

For more information on this file, see
https://docs.djangoproject.com/en/3.1/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/3.1/ref/settings/
"""
import datetime
from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/3.1/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = '#x87qywyhg^#3hz^&(et)k&k&=7x72&1n)c-*02t8aiuem%v*9'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ['*']


# Application definition

INSTALLED_APPS = [
    'api.users',
    'api.accounts',
    'api.parsers',
    'api.analyzers',
    'api.charts',
    'api.grabbers',
    'api.ads',
    'api.related',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'corsheaders',
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

ROOT_URLCONF = 'api.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'api.wsgi.application'


# Database
# https://docs.djangoproject.com/en/3.1/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'prod_db',
        'USER': 'admin',
        'PASSWORD': 'BS0880BSayamahaRGX612j',
        'HOST': 'db',
        'PORT': 5432
    }
}


REST_FRAMEWORK = {
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 10,
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_jwt.authentication.JSONWebTokenAuthentication',
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework.authentication.BasicAuthentication',
    ],
}


# Password validation
# https://docs.djangoproject.com/en/3.1/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/3.1/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'Europe/Moscow'

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/3.1/howto/static-files/

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'static'
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'


CORS_ORIGIN_WHITELIST = [
    'http://localhost:3000',
    'http://localhost:90',
    'http://192.168.1.165:3000',
]

JWT_AUTH = {
    # how long the original token is valid for
    'JWT_EXPIRATION_DELTA': datetime.timedelta(days=10),

    # allow refreshing of tokens
    'JWT_ALLOW_REFRESH': True,

    # this is the maximum time AFTER the token was issued that
    # it can be refreshed.  exprired tokens can't be refreshed.
    'JWT_REFRESH_EXPIRATION_DELTA': datetime.timedelta(days=7),

    'JWT_RESPONSE_PAYLOAD_HANDLER': 'api.utils.my_jwt_response_handler'
}


# VK API SETTINGS
VK_API_VERSION = 5.96
NEW_RELEASES_BLOCK_ID = 'PUlYRhcOWlJqSVhBFw5JBScfCBpaU0kb'
CHART_BLOCK_ID = 'PUlYRhcOWFVqSVhBFw5JBScfCBpaU0kb'
NEW_RELEASES_SECTION_ID = 'PUlQVA8GR0R3W0tMF2teRGpJUVQPGVpScVNdQwMGW0pkXktMF1ETFioEGxMXGElSZFFYWhcFXkR8WkVUBwJJXHNfW0YCDF9ecxY'
CORE_AUDIO_OWNERS = ['4744', '3717', '-200']

RUCAPTCHA_KEY = 'b900c2e8222b8f9c116f12e3af17d757'

CHARTS = ['am', 'vk', 'ok', 'dz', 'it', 'ms', 'sz', 'yt', 'ym', 'zv', 'sp']
CHARTS_FULL_NAMES = {
    'am': 'Apple Music',
    'vk': 'VK+BOOM',
    'ok': 'OK+BOOM',
    'dz': 'DEEZER',
    'it': 'iTunes',
    'ms': 'Mooscle',
    'sz': 'Shazam',
    'yt': 'YouTube',
    'ym': 'Яндекс.Музыка',
    'zv': 'СберЗвук',
    'sp': 'Spotify',
}

EXECUTE_FALSES_METHODS = [
    'wall.getById'
]

VK_PLAYLISTS = {
    'https://vk.com/music/playlist/-147845620_508_3f101f84a2440c9aea': 'Лучшее за неделю',
    'https://vk.com/music/playlist/-147845620_5_c09c1c34cdf7190efb': 'Сегодня в плеере',
    'https://vk.com/music/playlist/-147845620_7_0f65d6c656c168d69d': 'Русские хиты',
    'https://vk.com/music/playlist/-147845620_6_7ee1eedd8f1885d658': 'Русский хип-хоп',
    'https://vk.com/music/playlist/-147845620_9_f33614ce29048fcc18': 'Танцевальная музыка',
    'https://vk.com/music/playlist/-147845620_8_85b003d4cb8f95a0b1': 'Зарубежный поп',
    'https://vk.com/music/playlist/-147845620_356_ee28db0cec433ef23d': 'Иностранный хип-хоп',
    'https://vk.com/music/playlist/-147845620_2169_42b7d75273b0c38866': 'Поющие блогеры',
    'https://vk.com/music/playlist/-147845620_10_aa4735c1f37b362e48': 'Иностранный рок',
    'https://vk.com/music/playlist/-147845620_1097_cd415b5dfec1a8099c': 'Где-то слышал',
    'https://vk.com/music/playlist/-147845620_932_cc389fc792330bd782': 'Новый русский рок',
    'https://vk.com/music/playlist/-147845620_814_9f41b009a707a6a92f': 'Находки недели',
}

FEAT_SPLIT_SIMPOLS = [', ', ' feat. ', ' ft. ', ' Feat. ', ' FEAT. ', ' feat ', ' ft ', ' Feat ', ' FEAT ']

VK_APP_ID = 7669131
VK_APP_SECRET = 'RD3Ff9rNTL9ezAZNdg5d'
