define([ "jquery", "underscore", "js/common_helpers/ajax_helpers", "URI", "js/models/xblock_info",
    "js/views/library_container", "js/views/paging_header", "js/views/paging_footer"],
    function ($, _, AjaxHelpers, URI, XBlockInfo, LibraryContainer, PagingHeader, PagingFooter) {

        var htmlResponseTpl = _.template('' +
            '<div class="xblock-container-paging-parameters" ' +
                'data-start="<%= start %>" ' +
                'data-displayed="<%= displayed %>" ' +
                'data-total="<%= total %>" ' +
                'data-previews="<%= previews %>"></div>'
        );

        var getResponseHtml = function (options){
            var default_values = {
                start: 0,
                displayed: PAGE_SIZE,
                total: PAGE_SIZE + 1,
                previews: true
            };
            var eff_options = _.extend(default_values, options);
            return '<div class="xblock" data-request-token="request_token">' +
                '<div class="container-paging-header"></div>' +
                htmlResponseTpl(eff_options) +
                '<div class="container-paging-footer"></div>' +
                '</div>'
        };

        var makePage = function(html_parameters) {
            return {
                resources: [],
                html: getResponseHtml(html_parameters)
            };
        };

        var PAGE_SIZE = 3;

        var mockFirstPage = makePage({
                start: 0,
                displayed: PAGE_SIZE,
                total: PAGE_SIZE + 1
            });

        var mockSecondPage = makePage({
                start: PAGE_SIZE,
                displayed: 1,
                total: PAGE_SIZE + 1
            });

        var mockEmptyPage = makePage({
                start: 0,
                displayed: 0,
                total: 0
            });

        var respondWithMockPage = function(requests, response_override) {
            var requestIndex = requests.length - 1;
            var request = requests[requestIndex];
            var url = new URI(request.url);
            var queryParameters = url.query(true); // Returns an object with each query parameter stored as a value
            var page = queryParameters.page_number;
            var response = page === "0" ? mockFirstPage : mockSecondPage;
            if (typeof response_override !== 'undefined') {
                response = response_override;
            }
            AjaxHelpers.respondWithJson(requests, response, requestIndex);
        };

        var MockPagingView = LibraryContainer.extend({
            view: 'container_preview',
            el: $("<div><div class='xblock' data-request-token='test_request_token'/></div>"),
            model: new XBlockInfo({}, {parse: true}),
            page_size: PAGE_SIZE,
            page_reload_callback: function() {}
        });

        describe("Library Container", function() {
            var LibraryContainer;

            beforeEach(function () {
                var feedbackTpl = readFixtures('system-feedback.underscore');
                setFixtures($("<script>", { id: "system-feedback-tpl", type: "text/template" }).text(feedbackTpl));
                LibraryContainer = new MockPagingView({page_size: PAGE_SIZE});
            });

            describe("Container", function () {
                describe("rendering", function(){
                    beforeEach(function() {
                        spyOn(LibraryContainer, 'page_reload_callback');
                        spyOn(LibraryContainer, 'update_previews_callback');
                    });

                    it('does not call page_reload_callback on inital render', function(){
                        var requests = AjaxHelpers.requests(this);
                        LibraryContainer.render();
                        respondWithMockPage(requests);
                        expect(LibraryContainer.page_reload_callback).not.toHaveBeenCalled();
                        expect(LibraryContainer.update_previews_callback).toHaveBeenCalled();
                    });

                    it('calls page_reload_callback on page change render', function(){
                        var requests = AjaxHelpers.requests(this);
                        LibraryContainer.setPage(1);
                        respondWithMockPage(requests);
                        expect(LibraryContainer.page_reload_callback).toHaveBeenCalledWith(LibraryContainer.$el);
                        expect(LibraryContainer.update_previews_callback).toHaveBeenCalledWith(true);
                    });

                    it('should set show_previews', function() {
                       var requests = AjaxHelpers.requests(this);
                       expect(LibraryContainer.collection.show_children_previews).toBe(true); //precondition check

                       LibraryContainer.setPage(0);
                       respondWithMockPage(requests, makePage({previews: false}));
                       expect(LibraryContainer.collection.show_children_previews).toBe(false);

                       LibraryContainer.setPage(0);
                       respondWithMockPage(requests, makePage({previews: true}));
                       expect(LibraryContainer.collection.show_children_previews).toBe(true);
                   });
                });

                describe("setPage", function () {
                    it('can set the current page', function () {
                        var requests = AjaxHelpers.requests(this);
                        LibraryContainer.setPage(0);
                        respondWithMockPage(requests);
                        expect(LibraryContainer.collection.currentPage).toBe(0);
                        LibraryContainer.setPage(1);
                        respondWithMockPage(requests);
                        expect(LibraryContainer.collection.currentPage).toBe(1);
                    });

                    it('should not change page after a server error', function () {
                        var requests = AjaxHelpers.requests(this);
                        LibraryContainer.setPage(0);
                        respondWithMockPage(requests);
                        LibraryContainer.setPage(1);
                        requests[1].respond(500);
                        expect(LibraryContainer.collection.currentPage).toBe(0);
                    });
                });

                describe("nextPage", function () {
                    it('does not move forward after a server error', function () {
                        var requests = AjaxHelpers.requests(this);
                        LibraryContainer.setPage(0);
                        respondWithMockPage(requests);
                        LibraryContainer.nextPage();
                        requests[1].respond(500);
                        expect(LibraryContainer.collection.currentPage).toBe(0);
                    });

                    it('can move to the next page', function () {
                        var requests = AjaxHelpers.requests(this);
                        LibraryContainer.setPage(0);
                        respondWithMockPage(requests);
                        LibraryContainer.nextPage();
                        respondWithMockPage(requests);
                        expect(LibraryContainer.collection.currentPage).toBe(1);
                    });

                    it('can not move forward from the final page', function () {
                        var requests = AjaxHelpers.requests(this);
                        LibraryContainer.setPage(1);
                        respondWithMockPage(requests);
                        LibraryContainer.nextPage();
                        expect(requests.length).toBe(1);
                    });
                });

                describe("previousPage", function () {

                    it('can move back a page', function () {
                        var requests = AjaxHelpers.requests(this);
                        LibraryContainer.setPage(1);
                        respondWithMockPage(requests);
                        LibraryContainer.previousPage();
                        respondWithMockPage(requests);
                        expect(LibraryContainer.collection.currentPage).toBe(0);
                    });

                    it('can not move back from the first page', function () {
                        var requests = AjaxHelpers.requests(this);
                        LibraryContainer.setPage(0);
                        respondWithMockPage(requests);
                        LibraryContainer.previousPage();
                        expect(requests.length).toBe(1);
                    });

                    it('does not move back after a server error', function () {
                        var requests = AjaxHelpers.requests(this);
                        LibraryContainer.setPage(1);
                        respondWithMockPage(requests);
                        LibraryContainer.previousPage();
                        requests[1].respond(500);
                        expect(LibraryContainer.collection.currentPage).toBe(1);
                    });
                });
            });

            describe("PagingHeader", function () {

                beforeEach(function () {
                    var pagingFooterTpl = readFixtures('paging-header.underscore');
                    appendSetFixtures($("<script>", { id: "paging-header-tpl", type: "text/template" }).text(pagingFooterTpl));
                });

                describe("Next page button", function () {
                    beforeEach(function () {
                        LibraryContainer.render();
                    });

                    it('does not move forward if a server error occurs', function () {
                        var requests = AjaxHelpers.requests(this);
                        LibraryContainer.setPage(0);
                        respondWithMockPage(requests);
                        LibraryContainer.pagingHeader.$('.next-page-link').click();
                        requests[1].respond(500);
                        expect(LibraryContainer.collection.currentPage).toBe(0);
                    });

                    it('can move to the next page', function () {
                        var requests = AjaxHelpers.requests(this);
                        LibraryContainer.setPage(0);
                        respondWithMockPage(requests);
                        LibraryContainer.pagingHeader.$('.next-page-link').click();
                        respondWithMockPage(requests);
                        expect(LibraryContainer.collection.currentPage).toBe(1);
                    });

                    it('should be enabled when there is at least one more page', function () {
                        var requests = AjaxHelpers.requests(this);
                        LibraryContainer.setPage(0);
                        respondWithMockPage(requests);
                        expect(LibraryContainer.pagingHeader.$('.next-page-link')).not.toHaveClass('is-disabled');
                    });

                    it('should be disabled on the final page', function () {
                        var requests = AjaxHelpers.requests(this);
                        LibraryContainer.setPage(1);
                        respondWithMockPage(requests);
                        expect(LibraryContainer.pagingHeader.$('.next-page-link')).toHaveClass('is-disabled');
                    });

                    it('should be disabled on an empty page', function () {
                        var requests = AjaxHelpers.requests(this);
                        LibraryContainer.setPage(0);
                        AjaxHelpers.respondWithJson(requests, mockEmptyPage);
                        expect(LibraryContainer.pagingHeader.$('.next-page-link')).toHaveClass('is-disabled');
                    });
                });

                describe("Previous page button", function () {
                    beforeEach(function () {
                        LibraryContainer.render();
                    });

                    it('does not move back if a server error occurs', function () {
                        var requests = AjaxHelpers.requests(this);
                        LibraryContainer.setPage(1);
                        respondWithMockPage(requests);
                        LibraryContainer.pagingHeader.$('.previous-page-link').click();
                        requests[1].respond(500);
                        expect(LibraryContainer.collection.currentPage).toBe(1);
                    });

                    it('can go back a page', function () {
                        var requests = AjaxHelpers.requests(this);
                        LibraryContainer.setPage(1);
                        respondWithMockPage(requests);
                        LibraryContainer.pagingHeader.$('.previous-page-link').click();
                        respondWithMockPage(requests);
                        expect(LibraryContainer.collection.currentPage).toBe(0);
                    });

                    it('should be disabled on the first page', function () {
                        var requests = AjaxHelpers.requests(this);
                        LibraryContainer.setPage(0);
                        respondWithMockPage(requests);
                        expect(LibraryContainer.pagingHeader.$('.previous-page-link')).toHaveClass('is-disabled');
                    });

                    it('should be enabled on the second page', function () {
                        var requests = AjaxHelpers.requests(this);
                        LibraryContainer.setPage(1);
                        respondWithMockPage(requests);
                        expect(LibraryContainer.pagingHeader.$('.previous-page-link')).not.toHaveClass('is-disabled');
                    });

                    it('should be disabled for an empty page', function () {
                        var requests = AjaxHelpers.requests(this);
                        LibraryContainer.setPage(0);
                        AjaxHelpers.respondWithJson(requests, mockEmptyPage);
                        expect(LibraryContainer.pagingHeader.$('.previous-page-link')).toHaveClass('is-disabled');
                    });
                });

                describe("Page metadata section", function() {
                    it('shows the correct metadata for the current page', function () {
                        var requests = AjaxHelpers.requests(this),
                            message;
                        LibraryContainer.setPage(0);
                        respondWithMockPage(requests);
                        message = LibraryContainer.pagingHeader.$('.meta').html().trim();
                        expect(message).toBe('<p>Showing <span class="count-current-shown">1-3</span>' +
                            ' out of <span class="count-total">4 total</span>, ' +
                            'sorted by <span class="sort-order">Date added</span> descending</p>');
                    });
                });

                describe("Children count label", function () {
                    it('should show correct count on first page', function () {
                        var requests = AjaxHelpers.requests(this);
                        LibraryContainer.setPage(0);
                        respondWithMockPage(requests);
                        expect(LibraryContainer.pagingHeader.$('.count-current-shown')).toHaveHtml('1-3');
                    });

                    it('should show correct count on second page', function () {
                        var requests = AjaxHelpers.requests(this);
                        LibraryContainer.setPage(1);
                        respondWithMockPage(requests);
                        expect(LibraryContainer.pagingHeader.$('.count-current-shown')).toHaveHtml('4-4');
                    });

                    it('should show correct count for an empty collection', function () {
                        var requests = AjaxHelpers.requests(this);
                        LibraryContainer.setPage(0);
                        AjaxHelpers.respondWithJson(requests, mockEmptyPage);
                        expect(LibraryContainer.pagingHeader.$('.count-current-shown')).toHaveHtml('0-0');
                    });
                });

                describe("Children total label", function () {
                    it('should show correct total on the first page', function () {
                        var requests = AjaxHelpers.requests(this);
                        LibraryContainer.setPage(0);
                        respondWithMockPage(requests);
                        expect(LibraryContainer.pagingHeader.$('.count-total')).toHaveText('4 total');
                    });

                    it('should show correct total on the second page', function () {
                        var requests = AjaxHelpers.requests(this);
                        LibraryContainer.setPage(1);
                        respondWithMockPage(requests);
                        expect(LibraryContainer.pagingHeader.$('.count-total')).toHaveText('4 total');
                    });

                    it('should show zero total for an empty collection', function () {
                        var requests = AjaxHelpers.requests(this);
                        LibraryContainer.setPage(0);
                        AjaxHelpers.respondWithJson(requests, mockEmptyPage);
                        expect(LibraryContainer.pagingHeader.$('.count-total')).toHaveText('0 total');
                    });
                });
            });

            describe("PagingFooter", function () {
                beforeEach(function () {
                    var pagingFooterTpl = readFixtures('paging-footer.underscore');
                    appendSetFixtures($("<script>", { id: "paging-footer-tpl", type: "text/template" }).text(pagingFooterTpl));
                });

                describe("Next page button", function () {
                    beforeEach(function () {
                        // Render the page and header so that they can react to events
                        LibraryContainer.render();
                    });

                    it('does not move forward if a server error occurs', function () {
                        var requests = AjaxHelpers.requests(this);
                        LibraryContainer.setPage(0);
                        respondWithMockPage(requests);
                        LibraryContainer.pagingFooter.$('.next-page-link').click();
                        requests[1].respond(500);
                        expect(LibraryContainer.collection.currentPage).toBe(0);
                    });

                    it('can move to the next page', function () {
                        var requests = AjaxHelpers.requests(this);
                        LibraryContainer.setPage(0);
                        respondWithMockPage(requests);
                        LibraryContainer.pagingFooter.$('.next-page-link').click();
                        respondWithMockPage(requests);
                        expect(LibraryContainer.collection.currentPage).toBe(1);
                    });

                    it('should be enabled when there is at least one more page', function () {
                        var requests = AjaxHelpers.requests(this);
                        LibraryContainer.setPage(0);
                        respondWithMockPage(requests);
                        expect(LibraryContainer.pagingFooter.$('.next-page-link')).not.toHaveClass('is-disabled');
                    });

                    it('should be disabled on the final page', function () {
                        var requests = AjaxHelpers.requests(this);
                        LibraryContainer.setPage(1);
                        respondWithMockPage(requests);
                        expect(LibraryContainer.pagingFooter.$('.next-page-link')).toHaveClass('is-disabled');
                    });

                    it('should be disabled on an empty page', function () {
                        var requests = AjaxHelpers.requests(this);
                        LibraryContainer.setPage(0);
                        AjaxHelpers.respondWithJson(requests, mockEmptyPage);
                        expect(LibraryContainer.pagingFooter.$('.next-page-link')).toHaveClass('is-disabled');
                    });
                });

                describe("Previous page button", function () {
                    beforeEach(function () {
                        // Render the page and header so that they can react to events
                        LibraryContainer.render();
                    });

                    it('does not move back if a server error occurs', function () {
                        var requests = AjaxHelpers.requests(this);
                        LibraryContainer.setPage(1);
                        respondWithMockPage(requests);
                        LibraryContainer.pagingFooter.$('.previous-page-link').click();
                        requests[1].respond(500);
                        expect(LibraryContainer.collection.currentPage).toBe(1);
                    });

                    it('can go back a page', function () {
                        var requests = AjaxHelpers.requests(this);
                        LibraryContainer.setPage(1);
                        respondWithMockPage(requests);
                        LibraryContainer.pagingFooter.$('.previous-page-link').click();
                        respondWithMockPage(requests);
                        expect(LibraryContainer.collection.currentPage).toBe(0);
                    });

                    it('should be disabled on the first page', function () {
                        var requests = AjaxHelpers.requests(this);
                        LibraryContainer.setPage(0);
                        respondWithMockPage(requests);
                        expect(LibraryContainer.pagingFooter.$('.previous-page-link')).toHaveClass('is-disabled');
                    });

                    it('should be enabled on the second page', function () {
                        var requests = AjaxHelpers.requests(this);
                        LibraryContainer.setPage(1);
                        respondWithMockPage(requests);
                        expect(LibraryContainer.pagingFooter.$('.previous-page-link')).not.toHaveClass('is-disabled');
                    });

                    it('should be disabled for an empty page', function () {
                        var requests = AjaxHelpers.requests(this);
                        LibraryContainer.setPage(0);
                        AjaxHelpers.respondWithJson(requests, mockEmptyPage);
                        expect(LibraryContainer.pagingFooter.$('.previous-page-link')).toHaveClass('is-disabled');
                    });
                });

                describe("Current page label", function () {
                    it('should show 1 on the first page', function () {
                        var requests = AjaxHelpers.requests(this);
                        LibraryContainer.setPage(0);
                        respondWithMockPage(requests);
                        expect(LibraryContainer.pagingFooter.$('.current-page')).toHaveText('1');
                    });

                    it('should show 2 on the second page', function () {
                        var requests = AjaxHelpers.requests(this);
                        LibraryContainer.setPage(1);
                        respondWithMockPage(requests);
                        expect(LibraryContainer.pagingFooter.$('.current-page')).toHaveText('2');
                    });

                    it('should show 1 for an empty collection', function () {
                        var requests = AjaxHelpers.requests(this);
                        LibraryContainer.setPage(0);
                        AjaxHelpers.respondWithJson(requests, mockEmptyPage);
                        expect(LibraryContainer.pagingFooter.$('.current-page')).toHaveText('1');
                    });
                });

                describe("Page total label", function () {
                    it('should show the correct value with more than one page', function () {
                        var requests = AjaxHelpers.requests(this);
                        LibraryContainer.setPage(0);
                        respondWithMockPage(requests);
                        expect(LibraryContainer.pagingFooter.$('.total-pages')).toHaveText('2');
                    });

                    it('should show page 1 when there are no assets', function () {
                        var requests = AjaxHelpers.requests(this);
                        LibraryContainer.setPage(0);
                        AjaxHelpers.respondWithJson(requests, mockEmptyPage);
                        expect(LibraryContainer.pagingFooter.$('.total-pages')).toHaveText('1');
                    });
                });

                describe("Page input field", function () {
                    var input;

                    it('should initially have a blank page input', function () {
                        var requests = AjaxHelpers.requests(this);
                        LibraryContainer.setPage(0);
                        respondWithMockPage(requests);
                        expect(LibraryContainer.pagingFooter.$('.page-number-input')).toHaveValue('');
                    });

                    it('should handle invalid page requests', function () {
                        var requests = AjaxHelpers.requests(this);
                        LibraryContainer.setPage(0);
                        respondWithMockPage(requests);
                        LibraryContainer.pagingFooter.$('.page-number-input').val('abc');
                        LibraryContainer.pagingFooter.$('.page-number-input').trigger('change');
                        expect(LibraryContainer.collection.currentPage).toBe(0);
                        expect(LibraryContainer.pagingFooter.$('.page-number-input')).toHaveValue('');
                    });

                    it('should switch pages via the input field', function () {
                        var requests = AjaxHelpers.requests(this);
                        LibraryContainer.setPage(0);
                        respondWithMockPage(requests);
                        LibraryContainer.pagingFooter.$('.page-number-input').val('2');
                        LibraryContainer.pagingFooter.$('.page-number-input').trigger('change');
                        AjaxHelpers.respondWithJson(requests, mockSecondPage);
                        expect(LibraryContainer.collection.currentPage).toBe(1);
                        expect(LibraryContainer.pagingFooter.$('.page-number-input')).toHaveValue('');
                    });

                    it('should handle AJAX failures when switching pages via the input field', function () {
                        var requests = AjaxHelpers.requests(this);
                        LibraryContainer.setPage(0);
                        respondWithMockPage(requests);
                        LibraryContainer.pagingFooter.$('.page-number-input').val('2');
                        LibraryContainer.pagingFooter.$('.page-number-input').trigger('change');
                        requests[1].respond(500);
                        expect(LibraryContainer.collection.currentPage).toBe(0);
                        expect(LibraryContainer.pagingFooter.$('.page-number-input')).toHaveValue('');
                    });
                });
            });

            describe("Previews", function(){
                describe("toggle_previews", function(){
                    var oldXBlock,
                        testSendsAjax,
                        defaultUrl = "/some/weird/url/you/would/never/set/in/production",
                        handlerUrlMock = jasmine.createSpy('handlerUrl').andReturn(defaultUrl);

                    beforeEach(function() {
                        oldXBlock = LibraryContainer.xblock;
                        LibraryContainer.xblock = {
                            element: $('<div/>'),
                            runtime: {
                                handlerUrl: handlerUrlMock
                            }
                        }
                    });

                    afterEach(function() {
                        LibraryContainer.xblock = oldXBlock;
                    });

                    testSendsAjax = function (show_previews) {
                        it("should send " + (!show_previews) + " when show_children_previews was " + show_previews, function(){
                            var requests = AjaxHelpers.requests(this);
                            LibraryContainer.collection.show_children_previews = show_previews;
                            LibraryContainer.toggle_previews();

                            expect(handlerUrlMock).toHaveBeenCalledWith(
                                LibraryContainer.xblock.element, 'trigger_previews'
                            );
                            AjaxHelpers.expectJsonRequest(requests, 'POST', defaultUrl, { show_children_previews: !show_previews});
                            AjaxHelpers.respondWithJson(requests, { show_children_previews: !show_previews });

                            LibraryContainer.collection.show_children_previews = true;
                        });
                    };
                    testSendsAjax(true);
                    testSendsAjax(false);

                    it("should trigger render on success", function(){
                        spyOn(LibraryContainer, 'render');
                        var requests = AjaxHelpers.requests(this);

                        LibraryContainer.toggle_previews();
                        AjaxHelpers.respondWithJson(requests, { show_children_previews: true });

                        expect(LibraryContainer.render).toHaveBeenCalled();
                    });

                    it("should not trigger render on failure", function(){
                        spyOn(LibraryContainer, 'render');
                        var requests = AjaxHelpers.requests(this);

                        LibraryContainer.toggle_previews();
                        AjaxHelpers.respondWithError(requests);

                        expect(LibraryContainer.render).not.toHaveBeenCalled();
                    });
                });
            });
        });
    });
