define([
    'jquery', 'underscore', 'js/models/xblock_info', 'js/views/pages/library_container',
    'js/collections/component_template', 'xmodule', 'coffee/src/main', 'xblock/cms.runtime.v1'
],
function($, _, XBlockInfo, LibraryContainerPage, ComponentTemplates, xmoduleLoader) {
    'use strict';
    return function (componentTemplates, XBlockInfoJson, options) {
        var main_options = {
            el: $('#content'),
            model: new XBlockInfo(XBlockInfoJson, {parse: true}),
            templates: new ComponentTemplates(componentTemplates, {parse: true}),
            action: 'view'
        };
        xmoduleLoader.done(function () {
            var view = new LibraryContainerPage(_.extend(main_options, options));
            view.render();
        });
    };
});
