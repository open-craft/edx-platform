/**
 * PagedXBlockContainerPage is a variant of XBlockContainerPage that supports Pagination.
 */
define(["jquery", "js/views/pages/paged_container", "js/views/library_container"],
    function ($, PagedContainerPage, LibraryContainerView) {
        'use strict';
        var LibraryContainerPage = PagedContainerPage.extend({

            viewClass: LibraryContainerView,

            events: {
                'click .new-component-button': 'scrollToNewComponentButtons',
            },

            scrollToNewComponentButtons: function(event) {
                event.preventDefault();
                $.scrollTo(this.$('.add-xblock-component'));
            }

        });
        return LibraryContainerPage;
    });
