import csv
import logging

from rest_framework.authentication import SessionAuthentication
from edx_rest_framework_extensions.auth.jwt.authentication import JwtAuthentication
from edx_rest_framework_extensions.auth.session.authentication import SessionAuthenticationAllowInactiveUser
from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from .tasks import migrate_progress, OUTCOME_MIGRATED

log = logging.getLogger(__name__)


class MigrateProgressView(APIView):
    """
    Migrates user progress for a set of user pairs.
    Only admins can use this.
    """

    authentication_classes = (
        JwtAuthentication,
        SessionAuthentication,
        SessionAuthenticationAllowInactiveUser,
    )

    permission_classes = (
        permissions.IsAuthenticated,
        permissions.IsAdminUser,
    )

    def post(self, request):
        """
        **Use Cases**

            Migrate progress (enrollment, block completions, submissions,
            student module) from one user to another.

        **Example Requests**:

            POST /api/user/v1/completion/migrate/
            {
                "recepient_address": "devops@example.com",
            }

            ``Content-type`` header of request should be ``multipart/form-data``.
            Also note, that "recepient_address" field is not required,
            but multipart-encoded csv file is required.

            Example structure of required csv file:
            ```
            course,source_email,dest_email,outcome
            course-v1:a+b+c,a@example.com,b@example.com,course key invalid
            ```

        **Example POST Responses**

            * If attached csv file doesn't contain any of the required fields
            (``course``, ``source_email``, ``dest_email``), status code of the
            response will be 400.

            * If migration task successfully scheduled, status code will be 204.

        """
        csv_file = request.FILES['file']
        recepient_address = request.POST.get('recepient_address')

        reader = csv.DictReader(csv_file)

        if not {'course', 'source_email', 'dest_email'}.issubset(set(reader.fieldnames)):
            log.warning('Received invalid csv.')
            return Response(status=400)

        # Extract list to be used in migration task
        migrate_list = [
            (row['course'], row['source_email'], row['dest_email']) for row in reader
            if row.get('outcome') != OUTCOME_MIGRATED  # Ignore lines marked as migrated
        ]

        # Start background task to migrate progress for given users
        migrate_progress.delay(
            migrate_list,
            [recepient_address] if recepient_address else None
        )

        log.info('Scheduled user progress migration. Items to process: %s', len(migrate_list))

        return Response(status=204)
