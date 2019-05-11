define(['jquery', 'underscore', 'gettext', 'js/views/modals/base_modal'],
    function($, _, gettext, BaseModal) {
        var AssignmentTypeSummaryDialog = BaseModal.extend({

            options: $.extend({}, BaseModal.prototype.options, {
                modalName: 'assignmentsummary',
                modalSize: 'lg',
                addPrimaryActionButton: true,
                primaryActionButtonType: 'cancel',
                primaryActionButtonTitle: gettext('Close'),
                closeIcon: true,
                viewSpecificClasses: "assignment-summary-modal"
            }),

            initialize: function() {
                BaseModal.prototype.initialize.call(this);
                this.template = this.loadTemplate('assignment-type-summary-dialog');
                this.listenTo(this.model, 'change', this.renderContents);
                this.options.title = this.model.get('title');
            },

            getContentHtml: function() {
                return this.template({
                    assignmentTypes: this.model.get('assignmentTypes'),
                    totalMessage: _.template(gettext('Total summary: <%= total %>'))(
                        {total: this.getTotalSummary()})
                });
            },

            getTotalSummary: function() {
                var totalWeight = 0;
                _.each(this.model.get('assignmentTypes'), function(item_value) {
                    totalWeight += parseInt(item_value.get('weight'));
                });
                return totalWeight;
            },

            addActionButtons: function() {
                if (this.options.addPrimaryActionButton) {
                    this.addActionButton(
                        this.options.primaryActionButtonType,
                        this.options.primaryActionButtonTitle,
                        true
                    );
                }
            }
        });
        return AssignmentTypeSummaryDialog;
    }); // end define()
