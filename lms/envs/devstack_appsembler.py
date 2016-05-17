# devstack_appsembler.py

from .devstack import *
from .appsembler import *

INSTALLED_APPS += (
    'appsembler.intercom_integration',
    'appsembler.enrollment',
)
TEMPLATE_CONTEXT_PROCESSORS += ('appsembler.intercom_integration.context_processors.intercom',)
