define(["jquery", "underscore", "js/views/xblock", "js/utils/module", "gettext", "js/views/feedback_notification",
        "js/views/paging_header", "js/views/paging_footer"],
    function ($, _, XBlockView, ModuleUtils, gettext, NotificationView, PagingHeader, PagingFooter) {
        var LibraryContainerView = XBlockView.extend({
            // Store the request token of the first xblock on the page (which we know was rendered by Studio when
            // the page was generated). Use that request token to filter out user-defined HTML in any
            // child xblocks within the page.
            requestToken: "",

            initialize: function(options){
                var self = this;
                XBlockView.prototype.initialize.call(this);
                this.page_size = this.options.page_size || 10;
                this.page_reload_callback = this.options.page_reload_callback || function() {};
                // emulating Backbone.paginator interface
                this.collection = {
                    currentPage: 0,
                    totalPages: 0,
                    totalCount: 0,
                    sortDirection: "desc",
                    start: 0,
                    _size: 0,
                    show_children_previews: true,

                    bind: function() {},  // no-op
                    size: function() { return self.collection._size; }
                };
            },

            render: function(options) {
                var eff_options = options || {};
                if (eff_options.block_added) {
                    this.collection.currentPage = this.getPageCount(this.collection.totalCount+1) - 1;
                }
                eff_options.page_number = typeof eff_options.page_number !== "undefined"
                    ? eff_options.page_number
                    : this.collection.currentPage;
                return this.renderPage(eff_options);
            },

            renderPage: function(options){
                var self = this;
                return $.ajax({
                    url: decodeURIComponent(this.model.url()) + "/" + this.view,
                    type: 'GET',
                    cache: false,
                    data: this.getRenderParameters(options.page_number),
                    headers: { Accept: 'application/json' },
                    success: function(fragment) {
                        self.handleXBlockFragment(fragment, options);
                        self.processPaging({ requested_page: options.page_number });
                        if (options.paging) {
                            self.page_reload_callback(self.$el, self.collection.show_children_previews);
                        }
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
                if (total_count==0) return 1;
                return Math.ceil(total_count / this.page_size);
            },

            setPage: function(page_number) {
                this.render({ page_number: page_number, paging: true });
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

            processPaging: function(options){
                var $element = this.$el.find('.xblock-container-paging-parameters'),
                    total = $element.data('total');

                this.collection.currentPage = options.requested_page;
                this.collection.totalCount = total;
                this.collection.totalPages = this.getPageCount(total);
                this.collection.start = $element.data('start');
                this.collection._size = $element.data('displayed');
                this.collection.show_children_previews = $element.data('previews');

                this.processPagingHeaderAndFooter();
            },

            processPagingHeaderAndFooter: function(){
                if (this.pagingHeader)
                    this.pagingHeader.undelegateEvents();
                if (this.pagingFooter)
                    this.pagingFooter.undelegateEvents();

                this.pagingHeader = new PagingHeader({
                    view: this,
                    el: this.$el.find('.container-paging-header')
                });
                this.pagingFooter = new PagingFooter({
                    view: this,
                    el: this.$el.find('.container-paging-footer')
                });

                this.pagingHeader.render();
                this.pagingFooter.render();
            },

            xblockReady: function () {
                XBlockView.prototype.xblockReady.call(this);

                this.requestToken = this.$('div.xblock').first().data('request-token');
            },

            refresh: function() { },

            acknowledgeXBlockDeletion: function (locator){
                this.notifyRuntime('deleted-child', locator);
                this.collection._size -= 1;
                this.collection.totalCount -= 1;
                // pages are counted from 0 - thus currentPage == 1 if we're on second page
                if (this.collection._size == 0 && this.collection.currentPage >= 1) {
                    this.setPage(this.collection.currentPage - 1);
                    this.collection.totalPages -= 1;
                }
                else {
                    this.pagingHeader.render();
                    this.pagingFooter.render();
                }
            },

            makeRequestSpecificSelector: function(selector) {
                return 'div.xblock[data-request-token="' + this.requestToken + '"] > ' + selector;
            },

            sortDisplayName: function() {
                return "Date added";  // TODO add support for sorting
            },

            toggle_previews: function(){
                var self = this,
                    runtime = this.xblock && this.xblock.runtime;
                if (runtime) {
                    return $.ajax({
                        url: runtime.handlerUrl(this.xblock.element, 'trigger_previews'),
                        type: 'POST',
                        data: JSON.stringify({ show_children_previews: !this.collection.show_children_previews}),
                        dataType: 'json'
                    })
                    .then(self.render)
                    .promise();
                }
                else{
                    return $.Deferred().resolve(this.collection.show_children_previews).promise();
                }
            }
        });

        return LibraryContainerView;
    }); // end define();
