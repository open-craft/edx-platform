from lms.lib.courseware_search.lms_filter_generator import LmsSearchFilterGenerator


class EsmeCustomSearchFilterGenerator(LmsSearchFilterGenerator):
    def exclude_dictionary(self, **kwargs):
        exclude_dictionary = super().exclude_dictionary(**kwargs)
        exclude_dictionary['invitation_only'] = True
        exclude_dictionary['catalog_visibility'] = 'none'
        return exclude_dictionary
