define(["jquery", "underscore", "js/views/xblock", "js/utils/module", "gettext", "js/views/feedback_notification",
    "jquery.ui"], // The container view uses sortable, which is provided by jquery.ui.
    function ($, _, XBlockView, ModuleUtils, gettext, NotificationView) {
        var studioXBlockWrapperClass = '.studio-xblock-wrapper';

        var PagedContainerView = XBlockView.extend({
            // Store the request token of the first xblock on the page (which we know was rendered by Studio when
            // the page was generated). Use that request token to filter out user-defined HTML in any
            // child xblocks within the page.
            requestToken: "",

            initialize: function(options){
                XBlockView.prototype.initialize.call(this);
                this.paging = this.options.paging || {};
                if (this.paging.page_size === 'undefined') {
                    this.paging.page_size = 10;
                }
                this.current_page = 0;
                this.children_count = 0;
            },

            render: function(options) {
                if (options.block_added) {
                    this.current_page = this.getLastPage(this.children_count+1) - 1;
                }
                options.page_number = options.page_number || this.current_page;
                return this.renderPage(options);
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
                        self.processPagingParameters();
                    }
                });
            },

            getRenderParameters: function(page_number) {
                return {
                    enable_paging: true,
                    page_size: this.paging.page_size,
                    page_number: page_number
                };
            },

            getLastPage: function(children_count){
                return Math.ceil(children_count / this.paging.page_size);
            },

            processPagingParameters: function(){
                var selector = this.makeRequestSpecificSelector('.xblock-header-paging > .header-details'),
                    $element = $(selector),
                    textTemplate = _.template(gettext("Showing <%= displayed_children %> / <%= children_count %> items")),
                    displayed_children = $element.data('displayedChildren');

                this.children_count = $element.data('totalChildren');

                $element.html(textTemplate({displayed_children: displayed_children, children_count: this.children_count}));

                if (displayed_children >= this.children_count) {
                    $element.parent().hide();
                }
            },

            xblockReady: function () {
                XBlockView.prototype.xblockReady.call(this);

                this.requestToken = this.$('div.xblock').first().data('request-token');
            },

            refresh: function() {
                var sortableInitializedClass = this.makeRequestSpecificSelector('.reorderable-container.ui-sortable');
                this.$(sortableInitializedClass).sortable('refresh');
            },

            makeRequestSpecificSelector: function(selector) {
                return 'div.xblock[data-request-token="' + this.requestToken + '"] > ' + selector;
            }
        });

        return PagedContainerView;
    }); // end define();
