define(['js/spec_helpers/weight_summary_helpers', 'js/views/modals/assignment_type_summary', 'js/models/assignment_type_summary'],
    function(WeightHelpers, AssignmentTypeSummaryDialog, AssignmentTypeSummaryModel) {
        describe('WeightSummaryModal', function() {
            var modal, showModal;

            showModal = function() {
                var assignmentTypeModel = new AssignmentTypeSummaryModel({
                    title: gettext('Assignment types weight summary'),
                    assignmentTypes: []
                });
                modal = new AssignmentTypeSummaryDialog({
                    model: assignmentTypeModel,
                });
                modal.show();
            };

            /* Before each, install templates required for the base modal
               and validation error modal. */
            beforeEach(function() {
                WeightHelpers.installValidationTemplates();
            });

            afterEach(function() {
                WeightHelpers.hideModalIfShowing(modal);
            });

            it('is visible after show is called', function() {
                showModal();
                expect(WeightHelpers.isShowingModal(modal)).toBeTruthy();
            });

        });
    });
