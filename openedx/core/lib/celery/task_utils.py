"""
    Middleware utilities
"""
from contextlib import contextmanager
import crum

# from crum import CurrentRequestUserMiddleware
from django.conf import settings
from django.http import HttpResponse
from django.test.client import RequestFactory
from openedx.core.djangoapps.theming.middleware import CurrentSiteThemeMiddleware
from six.moves.urllib.parse import urlparse

def get_request_or_stub():
    """
    Return the current request or a stub request.
    If called outside the context of a request, construct a fake
    request that can be used to build an absolute URI.
    This is useful in cases where we need to pass in a request object
    but don't have an active request (for example, in tests, celery tasks, and XBlocks).
    """
    request = crum.get_current_request()

    if request is None:

        # The settings SITE_NAME may contain a port number, so we need to
        # parse the full URL.
        full_url = "http://{site_name}".format(site_name=settings.SITE_NAME)
        parsed_url = urlparse(full_url)

        # Construct the fake request.  This can be used to construct absolute
        # URIs to other paths.
        return RequestFactory(
            SERVER_NAME=parsed_url.hostname,
            SERVER_PORT=parsed_url.port or 80,
        ).get("/")

    else:
        return request

@contextmanager
def emulate_http_request(site=None, user=None, middleware_classes=None):
    """
    Generate a fake HTTP request and run selected middleware on it.
    This is used to enable features that assume they are running as part of an HTTP request handler. Many of these
    features retrieve the "current" request from a thread local managed by crum. They will make a call like
    crum.get_current_request() or something similar.
    Since some tasks are kicked off by a management commands (which does not have an HTTP request) and then executed
    in celery workers there is no "current HTTP request". Instead we just populate the global state that is most
    commonly used on request objects.
    Arguments:
        site (Site): The site that this request should emulate. Defaults to None.
        user (User): The user that initiated this fake request. Defaults to None
        middleware_classes (list): A list of classes that implement Django's middleware interface.
            Defaults to [CurrentRequestUserMiddleware, CurrentSiteThemeMiddleware] if None.
    """
    request = get_request_or_stub()
    request.site = site
    request.user = user

    # TODO: define the default middleware_classes in settings.py
    middleware_classes = middleware_classes or [
        crum.CurrentRequestUserMiddleware,
        CurrentSiteThemeMiddleware,
    ]
    middleware_instances = [klass() for klass in middleware_classes]
    response = HttpResponse()

    for middleware in middleware_instances:
        _run_method_if_implemented(middleware, 'process_request', request)

    try:
        yield
    except Exception as exc:
        for middleware in reversed(middleware_instances):
            _run_method_if_implemented(middleware, 'process_exception', request, exc)
        raise
    else:
        for middleware in reversed(middleware_instances):
            _run_method_if_implemented(middleware, 'process_response', request, response)


def _run_method_if_implemented(instance, method_name, *args, **kwargs):
    if hasattr(instance, method_name):
        return getattr(instance, method_name)(*args, **kwargs)
    else:
        return None
