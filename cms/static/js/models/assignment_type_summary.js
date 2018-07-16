define(['backbone', 'underscore', 'gettext'], function(Backbone, _, gettext) {
    var AssignmentTypeSummary = Backbone.Model.extend({
        defaults: {
            'title': '',
            'assignmentTypes': []
        }
    });

    return AssignmentTypeSummary;
}); // end define()
