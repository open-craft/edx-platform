/**
 * Provides helper methods for invoking Weight summary modal in Jasmine tests.
 */
define(['jquery', 'js/spec_helpers/modal_helpers', 'common/js/spec_helpers/template_helpers'],
    function($, ModalHelpers, TemplateHelpers) {
        var installSummaryTemplates;

        installSummaryTemplates = function() {
            ModalHelpers.installModalTemplates();
            TemplateHelpers.installTemplate('assignment-type-summary-dialog');
        };

        return $.extend(ModalHelpers, {
            'installSummaryTemplates': installSummaryTemplates
        });
    });
