import django

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}
INSTALLED_APPS = (
    'django.contrib.contenttypes',
    'django.contrib.auth',
    'django.contrib.sites',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    "tests.test_apps.AppTestConfig",
    'idp_user',
)
ROOT_URLCONF = ''  # tests override urlconf, but it still needs to be defined
MIDDLEWARE_CLASSES = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
)
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

USE_TZ = True

APP_ENV = "test"

IDP_USER_APP = {
    "CONSUMER_APP_ENV": "test",
    "APP_IDENTIFIER": "test_app",
    "ROLES": "tests.test_roles.ROLES",
    # "FAUST_APP_PATH": "conf.kafka_consumer.app",
    "IDP_URL": "https://idp-backend-staging.service.cardoai.com",
    "USE_REDIS_CACHE": False,
    "APP_ENTITIES": {
        "test_model": {
            "model": "tests.test_app_entity.AppEntityTest",
            "identifier_attr": "id",
            "label_attr": "name",
        },
    },
}

django.setup()
