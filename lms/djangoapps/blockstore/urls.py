"""blockstore URL Configuration
The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.11/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Add an import:  from blog import urls as blog_urls
    2. Add a URL to urlpatterns:  url(r'^blog/', include(blog_urls))
"""
import os

from auth_backends.urls import oauth2_urlpatterns
from django.conf import settings
from django.conf.urls import include, url
from django.conf.urls.static import static
from django.contrib import admin

from edx_api_doc_tools import make_api_info, make_docs_urls

from lms.djangoapps.blockstore.apps.core import views as core_views
from lms.djangoapps.blockstore.apps.bundles.tests.storage_utils import url_for_test_media

admin.autodiscover()

api_info = make_api_info(
    title="Blockstore API",
    version="v1",
    description="APIs for Openedx Blockstore"
)


urlpatterns = oauth2_urlpatterns + [
    url(r'^admin/', admin.site.urls),
    url(r'^api/', include('lms.djangoapps.blockstore.apps.rest_api.urls', namespace='blockstore_api')),
    # Use the same auth views for all logins, including those originating from the browseable API.
    url(r'^api-auth/', include((oauth2_urlpatterns, 'auth_backends'), namespace='rest_framework')),
    url(r'^auto_auth/$', core_views.AutoAuth.as_view(), name='auto_auth'),
    url(r'^health/$', core_views.health, name='health'),
] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
