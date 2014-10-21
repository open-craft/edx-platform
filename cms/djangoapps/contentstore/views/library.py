"""
Views related to content libraries.
A content library is an optional branch that contains a flat list of XBlocks
which can be re-used in the "normal" branches of the course or other courses.
"""
from __future__ import absolute_import

import json
import logging

from contentstore.views.item import create_xblock_info
from django.http import HttpResponse, HttpResponseBadRequest, Http404
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.conf import settings
from django.utils.translation import ugettext as _
from django_future.csrf import ensure_csrf_cookie
from edxmako.shortcuts import render_to_response
from opaque_keys.edx.keys import CourseKey
from opaque_keys.edx.locator import LibraryLocator, CourseLocator, LibraryUsageLocator
from xmodule.library_module import LibraryDescriptor
from xmodule.modulestore.exceptions import ItemNotFoundError
from xmodule.modulestore import ModuleStoreEnum
from xmodule.modulestore.django import modulestore

from .access import has_course_access
from .component import get_component_templates
from util.json_request import JsonResponse

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

        store = modulestore()

        try:
            library = store.get_library(library_key)
            if library is None:
                raise ItemNotFoundError  # Inconsistency: mixed modulestore returns None, whereas split raises exception
        except ItemNotFoundError:
            if store.has_course(library_key.for_branch(None)):
                # There is a course, but no library [yet]
                if "create" in request.GET:
                    # Create the library branch & root XBlock:
                    store.create_branch(
                        org=library_key.org,
                        course=library_key.course,
                        run=library_key.run,
                        branch='library',
                        user_id=request.user.id,
                        fields={"display_name": "New Library"},
                        root_category='library',
                        root_block_id='library',
                    )
                    return JsonResponse({
                        "result": "success",
                    })
                return HttpResponse(
                    "<html><body>"
                    "No library exists for {course_id}. Would you like to create one? "
                    "<a href=\"?create\">Yes</a>"
                    "</body></html>"
                    .format(course_id=library_key.for_branch(None))
                )
            else:
                raise Http404

        if not isinstance(library, LibraryDescriptor):
            return HttpResponseBadRequest("Course key specified is not a library.")

        if request.method == 'GET':
            return library_blocks_view(request, library, response_format)
        return HttpResponseBadRequest("Invalid request method.")

    # List all courses with a library:
    split_store = modulestore()._get_modulestore_by_type(ModuleStoreEnum.Type.split)
    libraries = []
    for i in split_store.find_matching_course_indexes("library"):
        libraries.append({
            "version": "{}".format(i["versions"]["library"]),
            "library": i["course"],
            "org": i["org"],
        })
    return JsonResponse(libraries)


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

    assert isinstance(library.location.course_key, LibraryLocator)
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
