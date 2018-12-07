/* eslint-env node */

// Karma config for common-webpack suite.
// Docs and troubleshooting tips in common/static/common/js/karma.common.conf.js

'use strict';
var path = require('path');
var configModule = require(path.join(__dirname, 'common/js/karma.common.conf.js'));

var options = {

    includeCommonFiles: true,

    normalizePathsForCoverageFunc: function(appRoot, pattern) {
        return pattern;
    },

    // Avoid adding files to this list. Use RequireJS.
    libraryFilesToInclude: [
        {pattern: 'common/js/vendor/jquery.js', included: true},
        {pattern: 'common/js/vendor/jquery-migrate.js', included: true},
        {pattern: 'js/vendor/jquery.event.drag-2.2.js', included: true},
        {pattern: 'js/vendor/slick.core.js', included: true},
        {pattern: 'js/vendor/slick.grid.js', included: true}
    ],

    libraryFiles: [
        {pattern: 'js/RequireJS-namespace-undefine.js'}
    ],

    // Make sure the patterns in sourceFiles and specFiles do not match the same file.
    // Otherwise Istanbul which is used for coverage tracking will cause tests to not run.
    sourceFiles: [
        {pattern: 'js/video/**/!(*spec).js'}
    ],

    specFiles: [
        // Define the Webpack-built spec files first
        {pattern: 'js/spec/video/*_spec.js', webpack: true}
    ],

    fixtureFiles: [
        // TODO: move these fixtures if not shared
        {pattern: '../lib/xmodule/xmodule/js/fixtures/*.*'},
        {pattern: '../lib/xmodule/xmodule/js/fixtures/hls/**/*.*'},
    ],

    runFiles: [
        {pattern: 'karma_runner_webpack.js', webpack: true}
    ],

    preprocessors: {}
};

options.runFiles
    .filter(function(file) { return file.webpack; })
    .forEach(function(file) {
        options.preprocessors[file.pattern] = ['webpack', 'sourcemap'];
    });


module.exports = function(config) {
    configModule.configure(config, options);
};
