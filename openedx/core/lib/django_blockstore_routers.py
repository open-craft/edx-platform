from lms.djangoapps.blockstore.apps.bundles.models import (
    Collection,
    Bundle,
    BundleVersion,
    Draft,
    BundleLink
)

class BlockstoreRouter:

    DATABASE_NAME = 'blockstore'
    models = [Collection, Bundle, BundleVersion, Draft, BundleLink ]

    def db_for_read(self, model, **hints):  # pylint: disable=unused-argument
        if model in self.models:
            return self.DATABASE_NAME

    def db_for_write(self, model, **hints):  # pylint: disable=unused-argument
        if model in self.models:
            return self.DATABASE_NAME

    def allow_migrate(self, db, app_label, model_name=None, **hints):  # pylint: disable=unused-argument
        """
        Only sync StudentModuleHistoryExtended to StudentModuleHistoryExtendedRouter.DATABASE_Name
        """
        if model_name is not None:
            model = hints.get('model')
            if model is not None and model in self.models:
                return db == self.DATABASE_NAME
        if db == self.DATABASE_NAME:
            return False

        return None