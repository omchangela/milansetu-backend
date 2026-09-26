"""
Django settings for config project.
"""

from pathlib import Path
import os
from urllib.parse import urlparse
from dotenv import load_dotenv
from datetime import timedelta

# Load .env from the backend directory
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / '.env')


def _parse_allowed_hosts(raw: str) -> list[str]:
    """Strip schemes, ports, and paths so ALLOWED_HOSTS contains hostnames only."""
    hosts: list[str] = []
    for entry in raw.split(','):
        value = entry.strip()
        if not value:
            continue
        if '://' in value:
            value = urlparse(value).hostname or value
        if '/' in value:
            value = value.split('/', 1)[0]
        if ':' in value and not value.startswith('['):
            value = value.split(':', 1)[0]
        if value:
            hosts.append(value)
    return hosts


# ─── Security ────────────────────────────────────────────────────────────────

SECRET_KEY = os.environ.get('SECRET_KEY')
DEBUG = os.environ.get('DEBUG', 'False') == 'True'
ALLOWED_HOSTS = _parse_allowed_hosts(os.environ.get('ALLOWED_HOSTS', ''))

# ─── Custom user model ────────────────────────────────────────────────────────
AUTH_USER_MODEL = 'users.User'


# ─── Applications ────────────────────────────────────────────────────────────

INSTALLED_APPS = [
    # Django built-ins (required)
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Third-party
    'rest_framework',
    'corsheaders',
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',
    # Local
    'authentication',
    'users',
    'common',
    'milansetu',
]


# ─── Middleware ───────────────────────────────────────────────────────────────

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',          # must be first
    'django.middleware.security.SecurityMiddleware',
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


# ─── Database (PostgreSQL) ───────────────────────────────────────────────────

def _build_database_config() -> dict:
    database_url = os.environ.get('DATABASE_URL', '').strip()
    db_host = os.environ.get('DB_HOST', '').strip()
    
    # Check if we should use MySQL
    is_mysql = False
    if database_url.startswith('mysql://'):
        is_mysql = True
    elif db_host and ('mysql' in db_host or 'aivencloud.com' in db_host):
        is_mysql = True
    elif os.environ.get('DB_ENGINE') == 'mysql':
        is_mysql = True

    if is_mysql:
        # Resolve connection variables
        name = os.environ.get('DB_NAME', 'defaultdb')
        user = os.environ.get('DB_USER')
        password = os.environ.get('DB_PASSWORD')
        host = db_host
        port = os.environ.get('DB_PORT', '3306')

        if database_url.startswith('mysql://'):
            # Parse MySQL database URL
            from urllib.parse import urlsplit
            url = urlsplit(database_url)
            name = url.path.lstrip('/')
            netloc = url.netloc
            if '@' in netloc:
                auth, host_port = netloc.split('@', 1)
                if ':' in auth:
                    user, password = auth.split(':', 1)
                else:
                    user = auth
            else:
                host_port = netloc
            
            if ':' in host_port:
                host, port = host_port.split(':', 1)
            else:
                host = host_port
                port = '3306'

        config = {
            'ENGINE': 'django.db.backends.mysql',
            'NAME': name,
            'USER': user,
            'PASSWORD': password,
            'HOST': host,
            'PORT': port,
        }

        # Check for CA certificate options
        ssl_ca = os.environ.get('DB_SSL_CA')
        ssl_config = {}
        if ssl_ca:
            # If the certificate content itself is provided, write it to a local ca.pem file
            if '-----BEGIN CERTIFICATE-----' in ssl_ca:
                ca_path = os.path.join(BASE_DIR, 'ca.pem')
                try:
                    with open(ca_path, 'w') as f:
                        f.write(ssl_ca.strip())
                    ssl_config['ca'] = ca_path
                except Exception:
                    pass
            else:
                # If it's a file path, we can either use it relative to BASE_DIR or as absolute
                if not os.path.isabs(ssl_ca):
                    ssl_config['ca'] = os.path.join(BASE_DIR, ssl_ca)
                else:
                    ssl_config['ca'] = ssl_ca
        else:
            # Check if a ca.pem file exists in the base directory as fallback
            ca_path = os.path.join(BASE_DIR, 'ca.pem')
            if os.path.exists(ca_path):
                ssl_config['ca'] = ca_path

        # Determine if we should verify the SSL CA certificate
        ssl_verify = os.environ.get('DB_SSL_VERIFY', 'True') == 'True'

        if ssl_config:
            if ssl_verify:
                config['OPTIONS'] = {'ssl': ssl_config}
            else:
                import ssl as python_ssl
                ctx = python_ssl.create_default_context(cafile=ssl_config.get('ca'))
                ctx.check_hostname = False
                ctx.verify_mode = python_ssl.CERT_NONE
                config['OPTIONS'] = {'ssl': ctx}
        else:
            config['OPTIONS'] = {'ssl': {}}
        return {'default': config}

    # Otherwise, fall back to PostgreSQL (or SQLite/dj_database_url if provided)
    if database_url:
        import dj_database_url
        ssl_require = not database_url.startswith('sqlite://')
        config = dj_database_url.parse(
            database_url,
            conn_max_age=600,
            ssl_require=ssl_require,
        )
        return {'default': config}

    return {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.environ.get('DB_NAME'),
            'USER': os.environ.get('DB_USER'),
            'PASSWORD': os.environ.get('DB_PASSWORD'),
            'HOST': os.environ.get('DB_HOST'),
            'PORT': os.environ.get('DB_PORT', '5432'),
            'OPTIONS': {
                'sslmode': 'require',
            },
        }
    }


DATABASES = _build_database_config()



# ─── Password validation ──────────────────────────────────────────────────────

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]


# ─── Internationalisation ─────────────────────────────────────────────────────

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True


# ─── Static & Media ───────────────────────────────────────────────────────────

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'static'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# ─── CORS ─────────────────────────────────────────────────────────────────────

def _parse_comma_separated_list(raw: str, default: list[str]) -> list[str]:
    if not raw:
        return default
    # Replace newlines, tabs, and escape sequences to clean user input
    cleaned = raw.replace('\\n', ',').replace('\n', ',').replace('\\r', '').replace('\r', '')
    parsed = []
    for entry in cleaned.split(','):
        val = entry.strip().strip('"').strip("'")
        if val:
            parsed.append(val)
    return parsed

CORS_ALLOWED_ORIGINS = _parse_comma_separated_list(
    os.environ.get('CORS_ALLOWED_ORIGINS', ''),
    default=[
        'http://localhost:5173',
        'http://127.0.0.1:5173',
        'https://gprasadreddyofficial-lab.github.io',
    ]
)
CORS_ALLOW_CREDENTIALS = True   # needed so the browser sends the CSRF cookie


# ─── CSRF ─────────────────────────────────────────────────────────────────────

CSRF_TRUSTED_ORIGINS = _parse_comma_separated_list(
    os.environ.get('CSRF_TRUSTED_ORIGINS', ''),
    default=[
        'http://localhost:5173',
        'http://127.0.0.1:5173',
        'https://gprasadreddyofficial-lab.github.io',
        'https://milansetu-backend.onrender.com',
    ]
)
# Cookie is readable by JS so the frontend can attach it as a header
CSRF_COOKIE_HTTPONLY = False
CSRF_COOKIE_SAMESITE = 'Lax'


# ─── Django REST Framework ────────────────────────────────────────────────────

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'UNAUTHENTICATED_USER': None,
}


# ─── Simple JWT ───────────────────────────────────────────────────────────────

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=60),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'AUTH_HEADER_TYPES': ('Bearer',),
    'SIGNING_KEY': os.environ.get('JWT_SIGNING_KEY', os.environ.get('SECRET_KEY')),
}
