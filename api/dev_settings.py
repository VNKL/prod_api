from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = '#x87qywyhg^#3hz^&(et)k&k&=7x72&1n)c-*02t8aiuem%v*9'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

CORS_ORIGIN_WHITELIST = [
    'http://localhost:3000',
    'http://localhost:90',
    'http://192.168.1.165:3000',
]
