define(['jquery', 'js/models/xblock_info', 'js/collections/component_template',
        'js/views/pages/library_container'],
    function($, XBlockInfo, ComponentTemplates, LibraryContainerPage) {
        describe('LibraryContainerPage', function() {
            var mockLibraryPageHTML = readFixtures('mock/mock-library-page.underscore');

            beforeEach(function() {
                appendSetFixtures(mockLibraryPageHTML);
            });

            it('Attaches a handler to new compoment button', function() {
                var xblock_info = {
                    category: "library",
                    has_explicit_staff_lock: false,
                    published_on: null,
                    display_name: "Test Lib",
                    graded: false,
                    due_date: "",
                    release_date: null,
                    format: null,
                    due: null,
                    studio_url: "/library/library-v1:TLIB+1",
                    start: "2030-01-01T00:00:00Z",
                    released_to_students: false,
                    edited_on: "Nov 17, 2014 at 07:50 UTC",
                    visibility_state: "unscheduled",
                    ancestor_has_staff_lock: false,
                    published: null,
                    course_graders: "[]",
                    id: "lib-block-v1:TLIB+1+type@library+block@library",
                    has_changes: null
                };
                var options = {
                    el: $('#content'),
                    model: new XBlockInfo(xblock_info, {parse: true}),
                    templates: new ComponentTemplates(),
                    action: 'view',
                    isUnitPage: false
                };
                var view = new LibraryContainerPage(options);
                // Stub jQuery.scrollTo module.
                $.scrollTo = jasmine.createSpy('jQuery.scrollTo');
                $('.new-component-button').click();
                expect($.scrollTo).toHaveBeenCalled();
            });

        });
    }
);
