/* globals requirejs, requireSerial, MathJax */
/* eslint-disable quote-props */

(function(requirejs) {
    'use strict';

    var i, specHelpers, testFiles;

    // TODO: how can we share the vast majority of this config that is in common
    // with LMS/CMS?
    requirejs.config({
        baseUrl: '/base',

        paths: {
            'js/src/ajax_prefix': 'js/src/ajax_prefix',
            'underscore': 'common/js/vendor/underscore',
            'underscore.string': 'common/js/vendor/underscore.string',
            'backbone': 'common/js/vendor/backbone',
            'codemirror': 'js/vendor/CodeMirror/codemirror',
            'draggabilly': 'js/vendor/draggabilly',
            'jquery': 'common/js/vendor/jquery',
            'jquery-migrate': 'common/js/vendor/jquery-migrate',
            'jquery.cookie': 'js/vendor/jquery.cookie',
            'jquery.leanModal': 'js/vendor/jquery.leanModal',
            'jquery.timeago': 'js/vendor/jquery.timeago',
            'jquery.ui': 'js/vendor/jquery-ui.min',
            'jquery.ui.draggable': 'js/vendor/jquery.ui.draggable',
            'json2': 'js/vendor/json2',
            'jquery.tinymce': 'js/vendor/tinymce/js/tinymce/jquery.tinymce',
            'tinymce': 'js/vendor/tinymce/js/tinymce/tinymce.full.min',
            'accessibility': 'js/src/accessibility_tools',
            'logger': 'js/src/logger',
            'utility': 'js/src/utility',
            'js/test/add_ajax_prefix': 'js/test/add_ajax_prefix',
            'gettext': 'js/test/i18n',
            'hls': 'common/js/vendor/hls',
            'VerticalStudentView': '../lib/xmodule/xmodule/assets/vertical/public/js/vertical_student_view',
            'jasmine-imagediff': 'js/vendor/jasmine-imagediff',
            'sinon': 'common/js/vendor/sinon',
            'js/time': 'js/time',
        },
        shim: {
            'gettext': {
                exports: 'gettext'
            },
            'string_utils': {
                deps: ['underscore'],
                exports: 'interpolate_text'
            },
            'date': {
                exports: 'Date'
            },
            'jquery-migrate': ['jquery'],
            'jquery.ui': {
                deps: ['jquery'],
                exports: 'jQuery.ui'
            },
            'jquery.flot': {
                deps: ['jquery'],
                exports: 'jQuery.flot'
            },
            'jquery.form': {
                deps: ['jquery'],
                exports: 'jQuery.fn.ajaxForm'
            },
            'jquery.markitup': {
                deps: ['jquery'],
                exports: 'jQuery.fn.markitup'
            },
            'jquery.leanModal': {
                deps: ['jquery'],
                exports: 'jQuery.fn.leanModal'
            },
            'jquery.smoothScroll': {
                deps: ['jquery'],
                exports: 'jQuery.fn.smoothScroll'
            },
            'jquery.ajaxQueue': {
                deps: ['jquery'],
                exports: 'jQuery.fn.ajaxQueue'
            },
            'jquery.scrollTo': {
                deps: ['jquery'],
                exports: 'jQuery.fn.scrollTo'
            },
            'jquery.cookie': {
                deps: ['jquery'],
                exports: 'jQuery.fn.cookie'
            },
            'jquery.qtip': {
                deps: ['jquery'],
                exports: 'jQuery.fn.qtip'
            },
            'jquery.fileupload': {
                deps: ['jquery.iframe-transport'],
                exports: 'jQuery.fn.fileupload'
            },
            'jquery.inputnumber': {
                deps: ['jquery'],
                exports: 'jQuery.fn.inputNumber'
            },
            'jquery.simulate': {
                deps: ['jquery'],
                exports: 'jQuery.fn.simulate'
            },
            'jquery.timeago': {
                deps: ['jquery'],
                exports: 'jQuery.timeago'
            },
            'jquery.tinymce': {
                deps: ['jquery', 'tinymce'],
                exports: 'jQuery.fn.tinymce'
            },
            'jquery.url': {
                deps: ['jquery'],
                exports: 'jQuery.fn.url'
            },
            'datepair': {
                deps: ['jquery.ui', 'jquery.timepicker']
            },
            'underscore': {
                deps: ['underscore.string'],
                exports: '_'
            },
            'backbone': {
                deps: ['underscore', 'jquery'],
                exports: 'Backbone'
            },
            'bootstrap': {
                deps: ['jquery']
            },
            'backbone.associations': {
                deps: ['backbone'],
                exports: 'Backbone.Associations'
            },
            'backbone.paginator': {
                deps: ['backbone'],
                exports: 'Backbone.PageableCollection'
            },
            'backbone-super': {
                deps: ['backbone']
            },
            'paging-collection': {
                deps: ['jquery', 'underscore', 'backbone.paginator']
            },
            'youtube': {
                exports: 'YT'
            },
            'Markdown.Converter': {
                deps: ['mathjax'],
                exports: 'Markdown.Converter'
            },
            'Markdown.Editor': {
                deps: ['Markdown.Converter', 'gettext', 'underscore'],
                exports: 'Markdown.Editor'
            },
            'Markdown.Sanitizer': {
                deps: ['Markdown.Converter'],
                exports: 'Markdown.Sanitizer'
            },
            '_split': {
                exports: '_split'
            },
            'codemirror': {
                exports: 'CodeMirror'
            },
            'tinymce': {
                exports: 'tinymce'
            },
            'mathjax': {
                exports: 'MathJax',
                init: function() {
                    MathJax.Hub.Config({
                        tex2jax: {
                            inlineMath: [['\\(', '\\)'], ['[mathjaxinline]', '[/mathjaxinline]']],
                            displayMath: [['\\[', '\\]'], ['[mathjax]', '[/mathjax]']]
                        }
                    });
                    return MathJax.Hub.Configured();
                }
            },
            'URI': {
                exports: 'URI'
            },
            'xmodule': {
                exports: 'XModule'
            },
            'logger': {
                exports: 'Logger'
            },
            'sinon': {
                exports: 'sinon'
            },
            'jasmine-imagediff': {},
            'common/js/spec_helpers/jasmine-extensions': {
                deps: ['jquery']
            },
            'common/js/spec_helpers/jasmine-stealth': {
                deps: ['underscore', 'underscore.string']
            },
            'common/js/spec_helpers/jasmine-waituntil': {
                deps: ['jquery']
            },
            'xblock/core': {
                exports: 'XBlock',
                deps: ['jquery', 'jquery.immediateDescendents']
            },
            'xblock/runtime.v1': {
                exports: 'XBlock.Runtime.v1',
                deps: ['xblock/core']
            },
            'xblock/lms.runtime.v1': {
                exports: 'LmsRuntime.v1',
                deps: ['xblock/runtime.v1']
            },
            // VideoXBlock
            'js/video/10_main': {
                deps: [
                    'require',
                    'jquery',
                ],
                exports: 'VideoXBlock'
            },
            'xmodule_js/spec/helper': {},
            'js/time': {},
            'js/spec/video_helper': {},
            'js/video/00_async_process': {},
        }
    });

    testFiles = [
        'js/spec/video/async_process_spec.js',
        'js/spec/video/completion_spec.js',
        'js/spec/video/events_spec.js',
        'js/spec/video/general_spec.js',
        'js/spec/video/html5_video_spec.js',
        'js/spec/video/initialize_spec.js',
        'js/spec/video/iterator_spec.js',
        'js/spec/video/resizer_spec.js',
        'js/spec/video/sjson_spec.js',
        'js/spec/video/video_autoadvance_spec.js',
        'js/spec/video/video_bumper_spec.js',
        'js/spec/video/video_caption_spec.js',
        'js/spec/video/video_context_menu_spec.js',
        'js/spec/video/video_control_spec.js',
        'js/spec/video/video_events_bumper_plugin_spec.js',
        'js/spec/video/video_events_plugin_spec.js',
        'js/spec/video/video_focus_grabber_spec.js',
        'js/spec/video/video_full_screen_spec.js',
        'js/spec/video/video_player_spec.js',
        'js/spec/video/video_play_pause_control_spec.js',
        'js/spec/video/video_play_placeholder_spec.js',
        'js/spec/video/video_play_skip_control_spec.js',
        'js/spec/video/video_poster_spec.js',
        'js/spec/video/video_progress_slider_spec.js',
        'js/spec/video/video_quality_control_spec.js',
        'js/spec/video/video_save_state_plugin_spec.js',
        'js/spec/video/video_skip_control_spec.js',
        'js/spec/video/video_speed_control_spec.js',
        'js/spec/video/video_storage_spec.js',
        'js/spec/video/video_volume_control_spec.js',
        'js/spec/time_spec.js'
    ];

    for (i = 0; i < testFiles.length; i++) {
        testFiles[i] = '/base/' + testFiles[i];
    }

    specHelpers = [
        'common/js/spec_helpers/jasmine-extensions',
        'common/js/spec_helpers/jasmine-stealth',
        'common/js/spec_helpers/jasmine-waituntil',
    ];

    // Jasmine has a global stack for creating a tree of specs. We need to load
    // spec files one by one, otherwise some end up getting nested under others.
    window.requireSerial(specHelpers.concat(testFiles), function() {
        // start test run, once Require.js is done
        window.__karma__.start();  // eslint-disable-line no-underscore-dangle
    });
}).call(this, requirejs);


/*
import 'js/src/ajax_prefix.js';
import 'common/js/vendor/underscore.js';
import 'common/js/vendor/backbone.js';
import 'js/vendor/CodeMirror/codemirror.js';
import 'js/vendor/draggabilly.js';
import 'common/js/vendor/jquery.js';
import 'common/js/vendor/jquery-migrate.js';
import 'js/vendor/jquery.cookie.js';
import 'js/vendor/jquery.leanModal.js';
import 'js/vendor/jquery.timeago.js';
import 'js/vendor/jquery-ui.min.js';
import 'js/vendor/jquery.ui.draggable.js';
import 'js/vendor/json2.js';
// import 'common/js/vendor/moment-with-locales.js';
import 'js/vendor/tinymce/js/tinymce/jquery.tinymce.min.js';
import 'js/vendor/tinymce/js/tinymce/tinymce.full.min.js';
import 'js/src/accessibility_tools.js';
import 'js/src/logger.js';
import 'js/src/utility.js';
import 'js/test/add_ajax_prefix.js';
import 'js/test/i18n.js';
import 'common/js/vendor/hls.js';
import '../lib/xmodule/xmodule/assets/vertical/public/js/vertical_student_view.js';


import 'js/vendor/jasmine-imagediff.js';
import 'common/js/spec_helpers/jasmine-waituntil.js';
import 'common/js/spec_helpers/jasmine-extensions.js';
import 'common/js/vendor/sinon.js';

// These libraries are used by the tests (and the code under test)
// but not explicitly imported
import 'jquery.ui';

// These
import 'js/video/10_main.js'
import 'js/spec/helper.js'
import 'js/spec/video_helper.js'

// These are the tests that will be run
import 'js/spec/video/async_process_spec.js';
import 'js/spec/video/completion_spec.js';
import 'js/spec/video/events_spec.js';
import 'js/spec/video/general_spec.js';
import 'js/spec/video/html5_video_spec.js';
import 'js/spec/video/initialize_spec.js';
import 'js/spec/video/iterator_spec.js';
import 'js/spec/video/resizer_spec.js';
import 'js/spec/video/sjson_spec.js';
import 'js/spec/video/video_autoadvance_spec.js';
import 'js/spec/video/video_bumper_spec.js';
import 'js/spec/video/video_caption_spec.js';
import 'js/spec/video/video_context_menu_spec.js';
import 'js/spec/video/video_control_spec.js';
import 'js/spec/video/video_events_bumper_plugin_spec.js';
import 'js/spec/video/video_events_plugin_spec.js';
import 'js/spec/video/video_focus_grabber_spec.js';
import 'js/spec/video/video_full_screen_spec.js';
import 'js/spec/video/video_player_spec.js';
import 'js/spec/video/video_play_pause_control_spec.js';
import 'js/spec/video/video_play_placeholder_spec.js';
import 'js/spec/video/video_play_skip_control_spec.js';
import 'js/spec/video/video_poster_spec.js';
import 'js/spec/video/video_progress_slider_spec.js';
import 'js/spec/video/video_quality_control_spec.js';
import 'js/spec/video/video_save_state_plugin_spec.js';
import 'js/spec/video/video_skip_control_spec.js';
import 'js/spec/video/video_speed_control_spec.js';
import 'js/spec/video/video_storage_spec.js';
import 'js/spec/video/video_volume_control_spec.js';
import 'js/spec/time_spec.js';

// overwrite the loaded method and manually start the karma after a delay
// Somehow the code initialized in jQuery's onready doesn't get called before karma auto starts

'use strict';
window.__karma__.loaded = function () {
    setTimeout(function () {
        window.__karma__.start();
    }, 1000);
};
*/
