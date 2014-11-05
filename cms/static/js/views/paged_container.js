define(["jquery", "underscore", "js/views/xblock", "js/utils/module", "gettext", "js/views/feedback_notification",
        "js/views/paging_header", "js/views/paging_footer"],
    function ($, _, XBlockView, ModuleUtils, gettext, NotificationView, PagingHeader, PagingFooter) {
        var studioXBlockWrapperClass = '.studio-xblock-wrapper';

        var PagedContainerView = XBlockView.extend({
            // Store the request token of the first xblock on the page (which we know was rendered by Studio when
            // the page was generated). Use that request token to filter out user-defined HTML in any
            // child xblocks within the page.
            requestToken: "",

            initialize: function(options){
                var self = this;
                XBlockView.prototype.initialize.call(this);
                this.page_size = this.options.page_size || 10;
                this.renderAddXBlockComponents = options.renderAddXBlockComponents;

                // emulating Backbone.paginator interface
                this.collection = {
                    currentPage: 0,
                    totalPages: 0,
                    totalCount: 0,
                    sortDirection: "desc",
                    start: 0,
                    _size: 0,

                    bind: function() {},  // no-op
                    size: function() { return self.collection._size; }
                };


            },

            render: function(options) {
                var eff_options = options || {};
                if (eff_options.block_added) {
                    this.collection.currentPage = this.getPageCount(this.collection.totalCount+1) - 1;
                }
                eff_options.page_number = eff_options.page_number || this.collection.currentPage;
                return this.renderPage(eff_options);
            },

            renderPage: function(options){
                var self = this,
                    view = this.view,
                    xblockInfo = this.model,
                    xblockUrl = xblockInfo.url();
                return $.ajax({
                    url: decodeURIComponent(xblockUrl) + "/" + view,
                    type: 'GET',
                    cache: false,
                    data: this.getRenderParameters(options.page_number),
                    headers: { Accept: 'application/json' },
                    success: function(fragment) {
                        self.handleXBlockFragment(fragment, options);
                        self.processPaging();
                        self.renderAddXBlockComponents();
                    }
                });
            },

            getRenderParameters: function(page_number) {
                return {
                    enable_paging: true,
                    page_size: this.page_size,
                    page_number: page_number
                };
            },

            getPageCount: function(total_count){
                return Math.ceil(total_count / this.page_size);
            },

            setPage: function(page_number) {
                this.collection.currentPage = page_number;
                this.render();
            },

            nextPage: function() {
                var collection = this.collection,
                    currentPage = collection.currentPage,
                    lastPage = collection.totalPages - 1;
                if (currentPage < lastPage) {
                    this.setPage(currentPage + 1);
                }
            },

            previousPage: function() {
                var collection = this.collection,
                    currentPage = collection.currentPage;
                if (currentPage > 0) {
                    this.setPage(currentPage - 1);
                }
            },

            processPaging: function(){
                var selector = this.makeRequestSpecificSelector('.xblock-container-paging-parameters'),
                    $element = $(selector),
                    total = $element.data('total'),
                    displayed = $element.data('displayed'),
                    start = $element.data('start');

                this.collection.totalCount = total;
                this.collection.totalPages = this.getPageCount(total);
                this.collection.start = start;
                this.collection._size = displayed;

                this.pagingHeader = new PagingHeader({
                    view: this,
                    el: $(this.makeRequestSpecificSelector('.container-paging-header'))
                });
                this.pagingFooter = new PagingFooter({
                    view: this,
                    el: $(this.makeRequestSpecificSelector('.container-paging-footer'))
                });

                this.pagingHeader.render();
                this.pagingFooter.render();
            },

            xblockReady: function () {
                XBlockView.prototype.xblockReady.call(this);

                this.requestToken = this.$('div.xblock').first().data('request-token');
            },

            refresh: function() { },

            makeRequestSpecificSelector: function(selector) {
                return 'div.xblock[data-request-token="' + this.requestToken + '"] > ' + selector;
            },

            sortDisplayName: function() {
                return "Date added";  // TODO add support for sorting
            }
        });

        return PagedContainerView;
    }); // end define();
