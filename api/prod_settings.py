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

CORS_ORIGIN_WHITELIST = [
    'http://localhost:90',
    'http://localhost:80',
    'http://localhost',
    'http://77.223.106.195:90',
    'http://77.223.106.195:80',
    'http://77.223.106.195'
]
