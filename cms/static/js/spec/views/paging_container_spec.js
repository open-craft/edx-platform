define([ "jquery", "underscore", "js/common_helpers/ajax_helpers", "URI", "js/models/xblock_info",
    "js/views/paged_container", "js/views/paging_header", "js/views/paging_footer"],
    function ($, _, AjaxHelpers, URI, XBlockInfo, PagedContainer, PagingContainer, PagingFooter) {

        var htmlResponseTpl = _.template('' +
            '<div class="xblock-container-paging-parameters" data-start="<%= start %>" data-displayed="<%= displayed %>" data-total="<%= total %>"/>'
        );

        function getResponseHtml(options){
            return '<div class="xblock" data-request-token="request_token">' +
                readFixtures('paging-header.underscore') +
                htmlResponseTpl(options) +
                readFixtures('paging-footer.underscore') +
                '</div>'
        }

        var PAGE_SIZE = 3;

        var mockFirstPage = {
            resources: [],
            html: getResponseHtml({
                start: 0,
                displayed: PAGE_SIZE,
                total: PAGE_SIZE + 1
            })
        };

        var mockSecondPage = {
            resources: [],
            html: getResponseHtml({
                start: PAGE_SIZE,
                displayed: 1,
                total: PAGE_SIZE + 1
            })
        };

        var mockEmptyPage = {
            resources: [],
            html: getResponseHtml({
                start: 0,
                displayed: 0,
                total: 0
            })
        };

        var respondWithMockAssets = function(requests) {
            var requestIndex = requests.length - 1;
            var request = requests[requestIndex];
            var url = new URI(request.url);
            var queryParameters = url.query(true); // Returns an object with each query parameter stored as a value
            var page = queryParameters.page_numer;
            var response = page === "0" ? mockFirstPage : mockSecondPage;
            AjaxHelpers.respondWithJson(requests, response, requestIndex);
        };

        var MockPagingView = PagedContainer.extend({
            view: 'container_preview',
            el: $("<div><div class='xblock' data-request-token='test_request_token'/></div>"),
            model: new XBlockInfo({}, {parse: true})
        });

        describe("Paging", function() {
            var pagingContainer;

            beforeEach(function () {
                var feedbackTpl = readFixtures('system-feedback.underscore');
                setFixtures($("<script>", { id: "system-feedback-tpl", type: "text/template" }).text(feedbackTpl));
                pagingContainer = new MockPagingView({ page_size: PAGE_SIZE });
            });

            describe("pagingContainer", function () {
                describe("setPage", function () {
                    it('can set the current page', function () {
                        var requests = AjaxHelpers.requests(this);
                        pagingContainer.setPage(0);
                        respondWithMockAssets(requests);
                        expect(pagingContainer.collection.currentPage).toBe(0);
                        pagingContainer.setPage(1);
                        respondWithMockAssets(requests);
                        expect(pagingContainer.collection.currentPage).toBe(1);
                    });

                    it('should not change page after a server error', function () {
                        var requests = AjaxHelpers.requests(this);
                        pagingContainer.setPage(0);
                        respondWithMockAssets(requests);
                        pagingContainer.setPage(1);
                        requests[1].respond(500);
                        expect(pagingContainer.collection.currentPage).toBe(0);
                    });
                });

                describe("nextPage", function () {
                    it('does not move forward after a server error', function () {
                        var requests = AjaxHelpers.requests(this);
                        pagingContainer.setPage(0);
                        respondWithMockAssets(requests);
                        pagingContainer.nextPage();
                        requests[1].respond(500);
                        expect(pagingContainer.collection.currentPage).toBe(0);
                    });

                    it('can move to the next page', function () {
                        var requests = AjaxHelpers.requests(this);
                        pagingContainer.setPage(0);
                        respondWithMockAssets(requests);
                        pagingContainer.nextPage();
                        respondWithMockAssets(requests);
                        expect(pagingContainer.collection.currentPage).toBe(1);
                    });

                    it('can not move forward from the final page', function () {
                        var requests = AjaxHelpers.requests(this);
                        pagingContainer.setPage(1);
                        respondWithMockAssets(requests);
                        pagingContainer.nextPage();
                        expect(requests.length).toBe(1);
                    });
                });

                describe("previousPage", function () {

                    it('can move back a page', function () {
                        var requests = AjaxHelpers.requests(this);
                        pagingContainer.setPage(1);
                        respondWithMockAssets(requests);
                        pagingContainer.previousPage();
                        respondWithMockAssets(requests);
                        expect(pagingContainer.collection.currentPage).toBe(0);
                    });

                    it('can not move back from the first page', function () {
                        var requests = AjaxHelpers.requests(this);
                        pagingContainer.setPage(0);
                        respondWithMockAssets(requests);
                        pagingContainer.previousPage();
                        expect(requests.length).toBe(1);
                    });

                    it('does not move back after a server error', function () {
                        var requests = AjaxHelpers.requests(this);
                        pagingContainer.setPage(1);
                        respondWithMockAssets(requests);
                        pagingContainer.previousPage();
                        requests[1].respond(500);
                        expect(pagingContainer.collection.currentPage).toBe(1);
                    });
                });
            });

            describe("pagingContainer.pagingHeader", function () {
                describe("Next page button", function () {
                    beforeEach(function () {
                        // Render the page and header so that they can react to events
                        pagingContainer.render();
                    });

                    it('does not move forward if a server error occurs', function () {
                        var requests = AjaxHelpers.requests(this);
                        pagingContainer.setPage(0);
                        respondWithMockAssets(requests);
                        pagingContainer.pagingHeader.$('.next-page-link').click();
                        requests[1].respond(500);
                        expect(pagingContainer.collection.currentPage).toBe(0);
                    });

                    it('can move to the next page', function () {
                        var requests = AjaxHelpers.requests(this);
                        pagingContainer.setPage(0);
                        respondWithMockAssets(requests);
                        pagingContainer.pagingHeader.$('.next-page-link').click();
                        respondWithMockAssets(requests);
                        expect(pagingContainer.collection.currentPage).toBe(1);
                    });

                    it('should be enabled when there is at least one more page', function () {
                        var requests = AjaxHelpers.requests(this);
                        pagingContainer.setPage(0);
                        respondWithMockAssets(requests);
                        expect(pagingContainer.pagingHeader.$('.next-page-link')).not.toHaveClass('is-disabled');
                    });

                    it('should be disabled on the final page', function () {
                        var requests = AjaxHelpers.requests(this);
                        pagingContainer.setPage(1);
                        respondWithMockAssets(requests);
                        expect(pagingContainer.pagingHeader.$('.next-page-link')).toHaveClass('is-disabled');
                    });

                    it('should be disabled on an empty page', function () {
                        var requests = AjaxHelpers.requests(this);
                        pagingContainer.setPage(0);
                        AjaxHelpers.respondWithJson(requests, mockEmptyPage);
                        expect(pagingContainer.pagingHeader.$('.next-page-link')).toHaveClass('is-disabled');
                    });
                });

                describe("Previous page button", function () {
                    beforeEach(function () {
                        // Render the page and header so that they can react to events
                        pagingContainer.render();
                        pagingContainer.pagingHeader.render();
                    });

                    it('does not move back if a server error occurs', function () {
                        var requests = AjaxHelpers.requests(this);
                        pagingContainer.setPage(1);
                        respondWithMockAssets(requests);
                        pagingContainer.pagingHeader.$('.previous-page-link').click();
                        requests[1].respond(500);
                        expect(pagingContainer.collection.currentPage).toBe(1);
                    });

                    it('can go back a page', function () {
                        var requests = AjaxHelpers.requests(this);
                        pagingContainer.setPage(1);
                        respondWithMockAssets(requests);
                        pagingContainer.pagingHeader.$('.previous-page-link').click();
                        respondWithMockAssets(requests);
                        expect(pagingContainer.collection.currentPage).toBe(0);
                    });

                    it('should be disabled on the first page', function () {
                        var requests = AjaxHelpers.requests(this);
                        pagingContainer.setPage(0);
                        respondWithMockAssets(requests);
                        expect(pagingContainer.pagingHeader.$('.previous-page-link')).toHaveClass('is-disabled');
                    });

                    it('should be enabled on the second page', function () {
                        var requests = AjaxHelpers.requests(this);
                        pagingContainer.setPage(1);
                        respondWithMockAssets(requests);
                        expect(pagingContainer.pagingHeader.$('.previous-page-link')).not.toHaveClass('is-disabled');
                    });

                    it('should be disabled for an empty page', function () {
                        var requests = AjaxHelpers.requests(this);
                        pagingContainer.setPage(0);
                        AjaxHelpers.respondWithJson(requests, mockEmptyPage);
                        expect(pagingContainer.pagingHeader.$('.previous-page-link')).toHaveClass('is-disabled');
                    });
                });

                describe("Page metadata section", function() {
                    it('shows the correct metadata for the current page', function () {
                        var requests = AjaxHelpers.requests(this),
                            message;
                        pagingContainer.setPage(0);
                        respondWithMockAssets(requests);
                        message = pagingContainer.pagingHeader.$('.meta').html().trim();
                        expect(message).toBe('<p>Showing <span class="count-current-shown">1-3</span>' +
                            ' out of <span class="count-total">4 total</span>, ' +
                            'sorted by <span class="sort-order">Date</span> descending</p>');
                    });

                    it('shows the correct metadata when sorted ascending', function () {
                        var requests = AjaxHelpers.requests(this),
                            message;
                        pagingContainer.setPage(0);
                        pagingContainer.toggleSortOrder('name-col');
                        respondWithMockAssets(requests);
                        message = pagingContainer.pagingHeader.$('.meta').html().trim();
                        expect(message).toBe('<p>Showing <span class="count-current-shown">1-3</span>' +
                            ' out of <span class="count-total">4 total</span>, ' +
                            'sorted by <span class="sort-order">Date added</span> ascending</p>');
                    });
                });

                describe("Children count label", function () {
                    it('should show correct count on first page', function () {
                        var requests = AjaxHelpers.requests(this);
                        pagingContainer.setPage(0);
                        respondWithMockAssets(requests);
                        expect(pagingContainer.pagingHeader.$('.count-current-shown')).toHaveHtml('1-3');
                    });

                    it('should show correct count on second page', function () {
                        var requests = AjaxHelpers.requests(this);
                        pagingContainer.setPage(1);
                        respondWithMockAssets(requests);
                        expect(pagingContainer.pagingHeader.$('.count-current-shown')).toHaveHtml('4-4');
                    });

                    it('should show correct count for an empty collection', function () {
                        var requests = AjaxHelpers.requests(this);
                        pagingContainer.setPage(0);
                        AjaxHelpers.respondWithJson(requests, mockEmptyPage);
                        expect(pagingContainer.pagingHeader.$('.count-current-shown')).toHaveHtml('0-0');
                    });
                });

                describe("Children total label", function () {
                    it('should show correct total on the first page', function () {
                        var requests = AjaxHelpers.requests(this);
                        pagingContainer.setPage(0);
                        respondWithMockAssets(requests);
                        expect(pagingContainer.pagingHeader.$('.count-total')).toHaveText('4 total');
                    });

                    it('should show correct total on the second page', function () {
                        var requests = AjaxHelpers.requests(this);
                        pagingContainer.setPage(1);
                        respondWithMockAssets(requests);
                        expect(pagingContainer.pagingHeader.$('.count-total')).toHaveText('4 total');
                    });

                    it('should show zero total for an empty collection', function () {
                        var requests = AjaxHelpers.requests(this);
                        pagingContainer.setPage(0);
                        AjaxHelpers.respondWithJson(requests, mockEmptyPage);
                        expect(pagingContainer.pagingHeader.$('.count-total')).toHaveText('0 total');
                    });
                });
            });

            describe("PagingFooter", function () {
                var pagingFooter;

                beforeEach(function () {
                    var pagingFooterTpl = readFixtures('paging-footer.underscore');
                    appendSetFixtures($("<script>", { id: "paging-footer-tpl", type: "text/template" }).text(pagingFooterTpl));
                    pagingFooter = new PagingFooter({view: pagingContainer});
                });

                describe("Next page button", function () {
                    beforeEach(function () {
                        // Render the page and header so that they can react to events
                        pagingContainer.render();
                        pagingFooter.render();
                    });

                    it('does not move forward if a server error occurs', function () {
                        var requests = AjaxHelpers.requests(this);
                        pagingContainer.setPage(0);
                        respondWithMockAssets(requests);
                        pagingFooter.$('.next-page-link').click();
                        requests[1].respond(500);
                        expect(pagingContainer.collection.currentPage).toBe(0);
                    });

                    it('can move to the next page', function () {
                        var requests = AjaxHelpers.requests(this);
                        pagingContainer.setPage(0);
                        respondWithMockAssets(requests);
                        pagingFooter.$('.next-page-link').click();
                        respondWithMockAssets(requests);
                        expect(pagingContainer.collection.currentPage).toBe(1);
                    });

                    it('should be enabled when there is at least one more page', function () {
                        var requests = AjaxHelpers.requests(this);
                        pagingContainer.setPage(0);
                        respondWithMockAssets(requests);
                        expect(pagingFooter.$('.next-page-link')).not.toHaveClass('is-disabled');
                    });

                    it('should be disabled on the final page', function () {
                        var requests = AjaxHelpers.requests(this);
                        pagingContainer.setPage(1);
                        respondWithMockAssets(requests);
                        expect(pagingFooter.$('.next-page-link')).toHaveClass('is-disabled');
                    });

                    it('should be disabled on an empty page', function () {
                        var requests = AjaxHelpers.requests(this);
                        pagingContainer.setPage(0);
                        AjaxHelpers.respondWithJson(requests, mockEmptyPage);
                        expect(pagingFooter.$('.next-page-link')).toHaveClass('is-disabled');
                    });
                });

                describe("Previous page button", function () {
                    beforeEach(function () {
                        // Render the page and header so that they can react to events
                        pagingContainer.render();
                        pagingFooter.render();
                    });

                    it('does not move back if a server error occurs', function () {
                        var requests = AjaxHelpers.requests(this);
                        pagingContainer.setPage(1);
                        respondWithMockAssets(requests);
                        pagingFooter.$('.previous-page-link').click();
                        requests[1].respond(500);
                        expect(pagingContainer.collection.currentPage).toBe(1);
                    });

                    it('can go back a page', function () {
                        var requests = AjaxHelpers.requests(this);
                        pagingContainer.setPage(1);
                        respondWithMockAssets(requests);
                        pagingFooter.$('.previous-page-link').click();
                        respondWithMockAssets(requests);
                        expect(pagingContainer.collection.currentPage).toBe(0);
                    });

                    it('should be disabled on the first page', function () {
                        var requests = AjaxHelpers.requests(this);
                        pagingContainer.setPage(0);
                        respondWithMockAssets(requests);
                        expect(pagingFooter.$('.previous-page-link')).toHaveClass('is-disabled');
                    });

                    it('should be enabled on the second page', function () {
                        var requests = AjaxHelpers.requests(this);
                        pagingContainer.setPage(1);
                        respondWithMockAssets(requests);
                        expect(pagingFooter.$('.previous-page-link')).not.toHaveClass('is-disabled');
                    });

                    it('should be disabled for an empty page', function () {
                        var requests = AjaxHelpers.requests(this);
                        pagingContainer.setPage(0);
                        AjaxHelpers.respondWithJson(requests, mockEmptyPage);
                        expect(pagingFooter.$('.previous-page-link')).toHaveClass('is-disabled');
                    });
                });

                describe("Current page label", function () {
                    it('should show 1 on the first page', function () {
                        var requests = AjaxHelpers.requests(this);
                        pagingContainer.setPage(0);
                        respondWithMockAssets(requests);
                        expect(pagingFooter.$('.current-page')).toHaveText('1');
                    });

                    it('should show 2 on the second page', function () {
                        var requests = AjaxHelpers.requests(this);
                        pagingContainer.setPage(1);
                        respondWithMockAssets(requests);
                        expect(pagingFooter.$('.current-page')).toHaveText('2');
                    });

                    it('should show 1 for an empty collection', function () {
                        var requests = AjaxHelpers.requests(this);
                        pagingContainer.setPage(0);
                        AjaxHelpers.respondWithJson(requests, mockEmptyPage);
                        expect(pagingFooter.$('.current-page')).toHaveText('1');
                    });
                });

                describe("Page total label", function () {
                    it('should show the correct value with more than one page', function () {
                        var requests = AjaxHelpers.requests(this);
                        pagingContainer.setPage(0);
                        respondWithMockAssets(requests);
                        expect(pagingFooter.$('.total-pages')).toHaveText('2');
                    });

                    it('should show page 1 when there are no assets', function () {
                        var requests = AjaxHelpers.requests(this);
                        pagingContainer.setPage(0);
                        AjaxHelpers.respondWithJson(requests, mockEmptyPage);
                        expect(pagingFooter.$('.total-pages')).toHaveText('1');
                    });
                });

                describe("Page input field", function () {
                    var input;

                    beforeEach(function () {
                        pagingFooter.render();
                    });

                    it('should initially have a blank page input', function () {
                        var requests = AjaxHelpers.requests(this);
                        pagingContainer.setPage(0);
                        respondWithMockAssets(requests);
                        expect(pagingFooter.$('.page-number-input')).toHaveValue('');
                    });

                    it('should handle invalid page requests', function () {
                        var requests = AjaxHelpers.requests(this);
                        pagingContainer.setPage(0);
                        respondWithMockAssets(requests);
                        pagingFooter.$('.page-number-input').val('abc');
                        pagingFooter.$('.page-number-input').trigger('change');
                        expect(pagingContainer.collection.currentPage).toBe(0);
                        expect(pagingFooter.$('.page-number-input')).toHaveValue('');
                    });

                    it('should switch pages via the input field', function () {
                        var requests = AjaxHelpers.requests(this);
                        pagingContainer.setPage(0);
                        respondWithMockAssets(requests);
                        pagingFooter.$('.page-number-input').val('2');
                        pagingFooter.$('.page-number-input').trigger('change');
                        AjaxHelpers.respondWithJson(requests, mockSecondPage);
                        expect(pagingContainer.collection.currentPage).toBe(1);
                        expect(pagingFooter.$('.page-number-input')).toHaveValue('');
                    });

                    it('should handle AJAX failures when switching pages via the input field', function () {
                        var requests = AjaxHelpers.requests(this);
                        pagingContainer.setPage(0);
                        respondWithMockAssets(requests);
                        pagingFooter.$('.page-number-input').val('2');
                        pagingFooter.$('.page-number-input').trigger('change');
                        requests[1].respond(500);
                        expect(pagingContainer.collection.currentPage).toBe(0);
                        expect(pagingFooter.$('.page-number-input')).toHaveValue('');
                    });
                });
            });
        });
    });
