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
from xmodule.library_module import LibraryDescriptor
from xmodule.modulestore.exceptions import ItemNotFoundError
from xmodule.modulestore import ModuleStoreEnum
from xmodule.modulestore.django import modulestore

from .access import has_course_access
from util.json_request import JsonResponse

__all__ = ['library_handler']

log = logging.getLogger(__name__)

LIBRARIES_ENABLED = settings.FEATURES.get('ENABLE_CONTENT_LIBRARIES', False)

@login_required
@ensure_csrf_cookie
def library_handler(request, course_key_string=None):
    """
    RESTful interface to most content library related functionality.
    """
    if not LIBRARIES_ENABLED:
        raise Http404  # Should never happen because we test the feature in urls.py also

    response_format = 'html'
    if request.REQUEST.get('format', 'html') == 'json' or 'application/json' in request.META.get('HTTP_ACCEPT', 'text/html'):
        response_format = 'json'

    if course_key_string:
        course_key = CourseKey.from_string(course_key_string)
        if not has_course_access(request.user, course_key):
            raise PermissionDenied()

        if course_key.deprecated:
            # Only courses stored in Split Mongo will work, and split requires Locators, not deprecated keys
            return HttpResponseBadRequest("This course's modulestore does not support content libraries.")

        if not course_key.branch:
            course_key = course_key.for_branch("library")

        store = modulestore()

        try:
            library = store.get_course(course_key, remove_branch=False)
            if library is None:
                raise ItemNotFoundError  # Inconsistency: mixed modulestore returns None, whereas split raises exception
        except ItemNotFoundError:
            if store.has_course(course_key.for_branch(None)):
                # There is a course, but no library
                # TODO: Create a library if one does not exist.
                raise NotImplementedError("Cannot yet create libraries. Edit mongo manually to create a library branch.")
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
            "course": i["course"],
            "org": i["org"],
            "run": i["run"],
        })
    return JsonResponse(libraries)

def library_blocks_view(request, library, response_format):
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
    
    course = modulestore().get_course(library.location.course_key.for_branch(None))
    xblock_info = create_xblock_info(library, include_ancestor_info=False, graders=[])

    from .component import get_component_templates
    component_templates = get_component_templates(course)

    return render_to_response('library.html', {
            'context_course': course,  # Needed only for display of menus at top of page.
            'action': 'view',
            'xblock': library,
            'xblock_locator': library.location,
            'unit': None,
            'component_templates': json.dumps(component_templates),
            'xblock_info': xblock_info,
        })
