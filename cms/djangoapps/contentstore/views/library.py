"""
Views related to content libraries.
A content library is a structure containing XBlocks which can be re-used in the
multiple courses.
"""
from __future__ import absolute_import

import json
import logging

from contentstore.views.item import create_xblock_info
from contentstore.utils import reverse_library_url
from django.http import HttpResponseBadRequest, Http404
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.conf import settings
from django.utils.translation import ugettext as _
from django_future.csrf import ensure_csrf_cookie
from edxmako.shortcuts import render_to_response
from opaque_keys import InvalidKeyError
from opaque_keys.edx.keys import CourseKey
from opaque_keys.edx.locator import LibraryLocator, LibraryUsageLocator
from xmodule.library_module import LibraryDescriptor
from xmodule.modulestore.exceptions import ItemNotFoundError, DuplicateCourseError
from xmodule.modulestore import ModuleStoreEnum
from xmodule.modulestore.django import modulestore

from .access import has_course_access
from .component import get_component_templates
from student.roles import CourseCreatorRole
from student import auth
from util.json_request import expect_json, JsonResponse

__all__ = ['library_handler']

log = logging.getLogger(__name__)

LIBRARIES_ENABLED = settings.FEATURES.get('ENABLE_CONTENT_LIBRARIES', False)


@login_required
@ensure_csrf_cookie
def library_handler(request, library_key_string=None):
    """
    RESTful interface to most content library related functionality.
    """
    if not LIBRARIES_ENABLED:
        raise Http404  # Should never happen because we test the feature in urls.py also

    response_format = 'html'
    if request.REQUEST.get('format', 'html') == 'json' or 'application/json' in request.META.get('HTTP_ACCEPT', 'text/html'):
        response_format = 'json'

    if library_key_string:
        library_key = CourseKey.from_string(library_key_string)
        if not isinstance(library_key, LibraryLocator):
            raise Http404  # This is not a library
        if not has_course_access(request.user, library_key):
            raise PermissionDenied()

        try:
            library = modulestore().get_library(library_key)
            if library is None:
                raise ItemNotFoundError  # Inconsistency: mixed modulestore returns None, whereas split raises exception
        except ItemNotFoundError:
            raise Http404

        if not isinstance(library, LibraryDescriptor):
            return HttpResponseBadRequest("Key specified is not a library.")

        if request.method == 'GET':
            return library_blocks_view(request, library, response_format)
        return HttpResponseBadRequest("Invalid request method.")

    elif request.method == 'POST':
        # Create a new library:
        return _create_library(request)
    else:
        # List all accessible libraries:
        libraries = []
        for lib in modulestore().get_libraries():
            key = lib.location.library_key
            if not has_course_access(request.user, key):
                continue
            libraries.append({
                "display_name": lib.display_name,
                "library_key": unicode(key),
            })
        return JsonResponse(libraries)


@expect_json
def _create_library(request):
    """
    Helper method for creating a new library.
    """
    if not auth.has_access(request.user, CourseCreatorRole()):
        raise PermissionDenied()
    try:
        org = request.json['org']
        library = request.json.get('number', None)
        if library is None:
            library = request.json['library']
        display_name = request.json['display_name']
        store = modulestore()
        with store.default_store(ModuleStoreEnum.Type.split):
            new_lib = store.create_library(
                org=org,
                library=library,
                user_id=request.user.id,
                fields={"display_name": display_name},
            )
    except KeyError as error:
        return JsonResponse({
            "ErrMsg": _("Unable to create library - missing expected JSON key '{err}'").format(err=error.message)}
        )
    except InvalidKeyError as error:
        return JsonResponse({
            "ErrMsg": _("Unable to create library - invalid data.\n\n{err}").format(name=display_name, err=error.message)}
        )
    except DuplicateCourseError as error:
        return JsonResponse({
            "ErrMsg": _("Unable to create library - one already exists with that key.\n\n{err}").format(err=error.message)}
        )
   
    lib_key_str = unicode(new_lib.location.library_key)
    return JsonResponse({
        'url': reverse_library_url('library_handler', lib_key_str),
        'library_key': lib_key_str,
    })


def library_blocks_view(request, library, response_format):
    """
    The main view of a course's content library.
    Shows all the XBlocks in the library, and allows adding/editing/deleting
    them.
    Can be called with response_format="json" to get a JSON-formatted list of
    the XBlocks in the library along with library metadata.
    """
    children = library.children
    if response_format == "json":
        # The JSON response for this request is short and sweet:
        prev_version = library.runtime.course_entry.structure['previous_version']
        return JsonResponse({
            "display_name": library.display_name,
            "library_id": unicode(library.location.course_key),  # library.course_id raises UndefinedContext - fix?
            "version": unicode(library.runtime.course_entry.course_key.version),
            "previous_version": unicode(prev_version) if prev_version else None,
            "blocks": [unicode(x) for x in children],
        })

    xblock_info = create_xblock_info(library, include_ancestor_info=False, graders=[])

    component_templates = get_component_templates(library)

    assert isinstance(library.location.library_key, LibraryLocator)
    assert isinstance(library.location, LibraryUsageLocator)

    return render_to_response('library.html', {
        'context_library': library,
        'action': 'view',
        'xblock': library,
        'xblock_locator': library.location,
        'unit': None,
        'component_templates': json.dumps(component_templates),
        'xblock_info': xblock_info,
    })
