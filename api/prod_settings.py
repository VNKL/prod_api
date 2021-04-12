import os


SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY')

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': os.environ.get('DB_NAME'),
        'USER': os.environ.get('DB_USER'),
        'PASSWORD': os.environ.get('DB_PASS'),
        'HOST': os.environ.get('DB_HOST'),
        'PORT': os.environ.get('DB_PORT')

    }
}

ALLOWED_HOSTS = ['.localhost', 'api', 'nginx', 'front', '77.223.106.195',
                 'from-shame-to-fame.ru', '.from-shame-to-fame.ru', 'www.from-shame-to-fame.ru',
                 'http://from-shame-to-fame.ru']

CORS_ORIGIN_WHITELIST = [
    'http://localhost:90',
    'http://localhost:80',
    'http://localhost',
    'http://77.223.106.195:90',
    'http://77.223.106.195:80',
    'http://77.223.106.195',
    'http://from-shame-to-fame.ru',
]

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
    'DEFAULT_RENDERER_CLASSES': (
        'rest_framework.renderers.JSONRenderer',
    )
}
