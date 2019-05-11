define(['backbone', 'underscore', 'gettext'], function(Backbone, _, gettext) {
    var CourseGrader = Backbone.Model.extend({
        defaults: {
            'type': '',    // must be unique w/in collection (ie. w/in course)
            'min_count': 1,
            'drop_count': 0,
            'short_label': '', // what to use in place of type if space is an issue
            'weight': 0, // int 0..100
            'actual_count': 0 // Current count of subsections assigned to this grader
        },
        parse: function(attrs) {
        // round off values while converting them to integer
            if (attrs['weight']) {
                attrs.weight = Math.round(attrs.weight);
            }
            if (attrs['min_count']) {
                attrs.min_count = Math.round(attrs.min_count);
            }
            if (attrs['drop_count']) {
                attrs.drop_count = Math.round(attrs.drop_count);
            }
            return attrs;
        },
        validate: function(attrs) {
            var errors = {};
            if (_.has(attrs, 'type')) {
                if (_.isEmpty(attrs['type'])) {
                    errors.type = 'The assignment type must have a name.';
                }
                else {
                // FIXME somehow this.collection is unbound sometimes. I can't track down when
                    var existing = this.collection && this.collection.some(function(other) { return (other.cid != this.cid) && (other.get('type') == attrs['type']); }, this);
                    if (existing) {
                        errors.type = gettext("There's already another assignment type with this name.");
                    }
                }
            }
            if (_.has(attrs, 'weight')) {
                var intWeight = Math.round(attrs.weight); // see if this ensures value saved is int
                if (!isFinite(intWeight) || /\D+/.test(attrs.weight) || intWeight < 0 || intWeight > 100) {
                    errors.weight = gettext('Please enter an integer between 0 and 100.');
                }
                else {
                    attrs.weight = intWeight;
                    if (this.collection) {
                    // Check if the sum of weights of each assignment type is equal to 100%
                    // if don't, add string error to validation model.
                        var totalWeight = this.collection.models.reduce(function(subtotal, grader) {
                            return subtotal + parseInt(grader.get('weight'));
                        }, 0);
                        if (!(totalWeight === 100))
                            errors.weight = gettext('Total weight must be 100%.');
                    }
                }
            }
            if (_.has(attrs, 'min_count')) {
                var intMinCount = Math.round(attrs.min_count);
                if (!isFinite(intMinCount) || /\D+/.test(attrs.min_count) || intMinCount < 1) {
                    errors.min_count = gettext('Please enter an integer greater than 0.');
                }
                else attrs.min_count = intMinCount;
            }
            if (_.has(attrs, 'drop_count')) {
                var dropCount = attrs.drop_count;
                var intDropCount = Math.round(dropCount);
                if (!isFinite(intDropCount) || /\D+/.test(dropCount) || (_.isString(dropCount) && _.isEmpty(dropCount.trim())) || intDropCount < 0) {
                    errors.drop_count = gettext('Please enter non-negative integer.');
                }
                else attrs.drop_count = intDropCount;
            }
            if (_.has(attrs, 'min_count') && _.has(attrs, 'drop_count') && !_.has(errors, 'min_count') && !_.has(errors, 'drop_count') && attrs.drop_count > attrs.min_count) {
                var template = _.template(
                gettext('Cannot drop more <%= types %> assignments than are assigned.')
            );
                errors.drop_count = template({types: attrs.type});
            }
            if (!_.isEmpty(errors)) return errors;
        }
    });

    return CourseGrader;
}); // end define()
