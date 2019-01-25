/* global CodeMirror, _ */
// no-useless-escape disabled because of warnings in regexp expressions within the
// "toXML" code. When the "useless escapes" were removed, some of the unit tests
// failed, but only in Jenkins, indicating browser-specific behavior.
/* eslint no-useless-escape: 0 */

(function() {
    'use strict';
    this.CapaMarkdownEditor = (function() {

        var MarkdownEditingDescriptor = function(element) {
            var that = this;
            this.toggleCheatsheetVisibility = function() {
                return MarkdownEditingDescriptor.prototype.toggleCheatsheetVisibility.apply(that, arguments);
            };
            this.toggleCheatsheet = function() {
                return MarkdownEditingDescriptor.prototype.toggleCheatsheet.apply(that, arguments);
            };
            this.onToolbarButton = function() {
                return MarkdownEditingDescriptor.prototype.onToolbarButton.apply(that, arguments);
            };
            this.onShowXMLButton = function() {
                return MarkdownEditingDescriptor.prototype.onShowXMLButton.apply(that, arguments);
            };
            this.save = function() {
                return MarkdownEditingDescriptor.prototype.save.apply(that, arguments);
            };

            this.element = element;
            this.xml_data_input = $(this.element.find('.xml-box'));
            this.markdown_input = $(this.element.find('.markdown-box'));
            this.save_button = this.element.closest('.xblock-editor').find('.save-button')
            if (this.markdown_input.length !== 0) {
                this.markdown_editor = CodeMirror.fromTextArea(this.markdown_input[0], {
                    lineWrapping: true,
                    mode: null
                });
                this.setCurrentEditor(this.markdown_editor);
                // Add listeners for toolbar buttons (only present for markdown editor)
                this.element.on('click', '.xml-tab', this.onShowXMLButton);
                this.element.on('click', '.format-buttons button', this.onToolbarButton);
                this.element.on('click', '.cheatsheet-toggle', this.toggleCheatsheet);

                // Hide the XML text area
                this.xml_data_input.hide();
            } else {
                this.createXMLEditor();
            }

            // Add Save handler to synchronise markdown and XML data
            this.save_button.click(this.save);
        };

        MarkdownEditingDescriptor.multipleChoiceTemplate = '( ) ' +
            (gettext('incorrect')) + '\n( ) ' + (gettext('incorrect')) +
            '\n(x) ' + (gettext('correct')) + '\n';

        MarkdownEditingDescriptor.checkboxChoiceTemplate = '[x] ' +
            (gettext('correct')) + '\n[ ] incorrect\n[x] correct\n';

        MarkdownEditingDescriptor.stringInputTemplate = '= ' +
            (gettext('answer')) + '\n';

        MarkdownEditingDescriptor.numberInputTemplate = '= ' +
            (gettext('answer')) + ' +- 0.001%\n';

        MarkdownEditingDescriptor.selectTemplate = '[[' +
            (gettext('incorrect')) + ', (' + (gettext('correct')) + '), ' + (gettext('incorrect')) + ']]\n';

        MarkdownEditingDescriptor.headerTemplate = '' +
            (gettext('Header')) + '\n=====\n';

        MarkdownEditingDescriptor.explanationTemplate = '[explanation]\n' +
            (gettext('Short explanation')) + '\n[explanation]\n';

        /*
         Creates the XML Editor and sets it as the current editor. If text is passed in,
         it will replace the text present in the HTML template.

         text: optional argument to override the text passed in via the HTML template
         */
        MarkdownEditingDescriptor.prototype.createXMLEditor = function(text) {
            this.xml_editor = CodeMirror.fromTextArea(this.xml_data_input[0], {
                mode: 'xml',
                lineNumbers: true,
                lineWrapping: true
            });
            if (text) {
                this.xml_editor.setValue(text);
            }
            this.setCurrentEditor(this.xml_editor);
            $(this.xml_editor.getWrapperElement()).toggleClass('CodeMirror-advanced');
            // Need to refresh to get line numbers to display properly.
            this.xml_editor.refresh();
        };

        /*
         User has clicked to show the XML editor. Before XML editor is swapped in,
         the user will need to confirm the one-way conversion.
         */
        MarkdownEditingDescriptor.prototype.onShowXMLButton = function(e) {
            e.preventDefault();
            if (this.cheatsheet && this.cheatsheet.hasClass('shown')) {
                this.cheatsheet.toggleClass('shown');
                this.toggleCheatsheetVisibility();
            }
            if (this.confirmConversionToXml()) {
                this.createXMLEditor(MarkdownEditingDescriptor.markdownToXml(this.markdown_editor.getValue()));
                this.xml_editor.setCursor(0);
                // Hide markdown-specific toolbar buttons
                $(this.element.find('.editor-bar')).hide();
            }
        };

        /*
         Have the user confirm the one-way conversion to XML.
         Returns true if the user clicked OK, else false.
         */
        MarkdownEditingDescriptor.prototype.confirmConversionToXml = function() {
            return confirm(gettext('If you use the Advanced Editor, this problem will be converted to XML and you will not be able to return to the Simple Editor Interface.\n\nProceed to the Advanced Editor and convert this problem to XML?')); // eslint-disable-line max-len, no-alert
        };

        /*
         Event listener for toolbar buttons (only possible when markdown editor is visible).
         */
        MarkdownEditingDescriptor.prototype.onToolbarButton = function(e) {
            var revisedSelection, selection;
            e.preventDefault();
            selection = this.markdown_editor.getSelection();
            revisedSelection = null;
            switch ($(e.currentTarget).attr('class')) {
            case 'multiple-choice-button':
                revisedSelection = MarkdownEditingDescriptor.insertMultipleChoice(selection);
                break;
            case 'string-button':
                revisedSelection = MarkdownEditingDescriptor.insertStringInput(selection);
                break;
            case 'number-button':
                revisedSelection = MarkdownEditingDescriptor.insertNumberInput(selection);
                break;
            case 'checks-button':
                revisedSelection = MarkdownEditingDescriptor.insertCheckboxChoice(selection);
                break;
            case 'dropdown-button':
                revisedSelection = MarkdownEditingDescriptor.insertSelect(selection);
                break;
            case 'header-button':
                revisedSelection = MarkdownEditingDescriptor.insertHeader(selection);
                break;
            case 'explanation-button':
                revisedSelection = MarkdownEditingDescriptor.insertExplanation(selection);
                break;
            default:
                break;
            }
            if (revisedSelection !== null) {
                this.markdown_editor.replaceSelection(revisedSelection);
                this.markdown_editor.focus();
            }
        };

        /*
         Event listener for toggling cheatsheet (only possible when markdown editor is visible).
         */
        MarkdownEditingDescriptor.prototype.toggleCheatsheet = function(e) {
            var that = this;
            e.preventDefault();
            if (!$(this.markdown_editor.getWrapperElement()).find('.simple-editor-cheatsheet')[0]) {
                this.cheatsheet = $($('#simple-editor-cheatsheet').html());
                $(this.markdown_editor.getWrapperElement()).append(this.cheatsheet);
            }
            this.toggleCheatsheetVisibility();
            return setTimeout((function() {
                return that.cheatsheet.toggleClass('shown');
            }), 10);
        };

        /*
         Function to toggle cheatsheet visibility.
         */
        MarkdownEditingDescriptor.prototype.toggleCheatsheetVisibility = function() {
            return $('.modal-content').toggleClass('cheatsheet-is-shown');
        };

        /*
         Stores the current editor and hides the one that is not displayed.
         */
        MarkdownEditingDescriptor.prototype.setCurrentEditor = function(editor) {
            if (this.current_editor) {
                $(this.current_editor.getWrapperElement()).hide();
            }
            this.current_editor = editor;
            $(this.current_editor.getWrapperElement()).show();
            return $(this.current_editor).focus();
        };

        /*
         Called when save button is clicked.

         Ensures that any updated data from the active editor is saved to both
         the markdown and data fields.
         */
        MarkdownEditingDescriptor.prototype.save = function() {
            if (this.current_editor === this.markdown_editor) {
                var markdown = this.markdown_editor.getValue(),
                    data = MarkdownEditingDescriptor.markdownToXml(markdown);
                if (markdown !== this.markdown_input.val()) {
                    this.markdown_input.val(markdown);
                    this.xml_data_input.val(data);

                    this.markdown_input.closest('li').addClass('is-set');
                    this.xml_data_input.closest('li').addClass('is-set');
                }
            } else {
                // Using xml data editor, so clear out any markdown.
                var markdown = "",
                    data = this.current_editor.getValue();
                if (data !== this.xml_data_input.val()) {
                    this.markdown_input.val("");
                    this.xml_data_input.val(data);

                    this.markdown_input.closest('li').addClass('is-set');
                    this.xml_data_input.closest('li').addClass('is-set');
                }
            }
        };

        MarkdownEditingDescriptor.insertMultipleChoice = function(selectedText) {
            return MarkdownEditingDescriptor.insertGenericChoice(selectedText, '(', ')',
                MarkdownEditingDescriptor.multipleChoiceTemplate
            );
        };

        MarkdownEditingDescriptor.insertCheckboxChoice = function(selectedText) {
            return MarkdownEditingDescriptor.insertGenericChoice(selectedText, '[', ']',
                MarkdownEditingDescriptor.checkboxChoiceTemplate
            );
        };

        MarkdownEditingDescriptor.insertGenericChoice = function(selectedText, choiceStart, choiceEnd, template) {
            var cleanSelectedText, line, lines, revisedLines, i, len;
            if (selectedText.length > 0) {
                // Replace adjacent newlines with a single newline, strip any trailing newline
                cleanSelectedText = selectedText.replace(/\n+/g, '\n').replace(/\n$/, '');
                lines = cleanSelectedText.split('\n');
                revisedLines = '';
                for (i = 0, len = lines.length; i < len; i++) {
                    line = lines[i];
                    revisedLines += choiceStart;
                    // a stand alone x before other text implies that this option is "correct"
                    if (/^\s*x\s+(\S)/i.test(line)) {
                        // Remove the x and any initial whitespace as long as there's more text on the line
                        line = line.replace(/^\s*x\s+(\S)/i, '$1');
                        revisedLines += 'x';
                    } else {
                        revisedLines += ' ';
                    }
                    revisedLines += choiceEnd + ' ' + line + '\n';
                }
                return revisedLines;
            } else {
                return template;
            }
        };

        MarkdownEditingDescriptor.insertStringInput = function(selectedText) {
            return MarkdownEditingDescriptor.insertGenericInput(selectedText, '= ', '',
                MarkdownEditingDescriptor.stringInputTemplate
            );
        };

        MarkdownEditingDescriptor.insertNumberInput = function(selectedText) {
            return MarkdownEditingDescriptor.insertGenericInput(selectedText, '= ', '',
                MarkdownEditingDescriptor.numberInputTemplate
            );
        };

        MarkdownEditingDescriptor.insertSelect = function(selectedText) {
            return MarkdownEditingDescriptor.insertGenericInput(selectedText, '[[', ']]',
                MarkdownEditingDescriptor.selectTemplate
            );
        };

        MarkdownEditingDescriptor.insertHeader = function(selectedText) {
            return MarkdownEditingDescriptor.insertGenericInput(selectedText, '', '\n====\n',
                MarkdownEditingDescriptor.headerTemplate
            );
        };

        MarkdownEditingDescriptor.insertExplanation = function(selectedText) {
            return MarkdownEditingDescriptor.insertGenericInput(selectedText, '[explanation]\n', '\n[explanation]',
                MarkdownEditingDescriptor.explanationTemplate
            );
        };

        MarkdownEditingDescriptor.insertGenericInput = function(selectedText, lineStart, lineEnd, template) {
            if (selectedText.length > 0) {
                return lineStart + selectedText + lineEnd;
            } else {
                return template;
            }
        };

        MarkdownEditingDescriptor.markdownToXml = function(markdown) {
            var demandHintTags = [],
                finalDemandHints, finalXml, responseTypesMarkdown, responseTypesXML, toXml;
            toXml = function(partialMarkdown) {
                var xml = partialMarkdown,
                    i, splits, makeParagraph, serializer, responseType, $xml, responseTypesSelector,
                    inputtype, beforeInputtype, extractHint, demandhints;
                var responseTypes = [
                    'optionresponse', 'multiplechoiceresponse', 'stringresponse', 'numericalresponse', 'choiceresponse'
                ];

                // fix DOS \r\n line endings to look like \n
                xml = xml.replace(/\r\n/g, '\n');

                // replace headers
                xml = xml.replace(/(^.*?$)(?=\n\=\=+$)/gm, '<h3 class="hd hd-2 problem-header">$1</h3>');
                xml = xml.replace(/\n^\=\=+$/gm, '');

                // extract question and description(optional)
                // >>question||description<< converts to
                // <label>question</label> <description>description</description>
                xml = xml.replace(/>>([^]+?)<</gm, function(match, questionText) {
                    var result = questionText.split('||'),
                        label = '<label>' + result[0] + '</label>\n';

                    // don't add empty <description> tag
                    if (result.length === 1 || !result[1]) {
                        return label;
                    }
                    return label + '<description>' + result[1] + '</description>\n';
                });

                // Pull out demand hints,  || a hint ||
                demandhints = '';
                xml = xml.replace(/(^\s*\|\|.*?\|\|\s*$\n?)+/gm, function(match) {  // $\n
                    var inner,
                        options = match.split('\n');
                    for (i = 0; i < options.length; i += 1) {
                        inner = /\s*\|\|(.*?)\|\|/.exec(options[i]);
                        if (inner) {
                            // xss-lint: disable=javascript-concat-html
                            demandhints += '  <hint>' + inner[1].trim() + '</hint>\n';
                        }
                    }
                    return '';
                });

                // replace \n+whitespace within extended hint {{ .. }}, by a space, so the whole
                // hint sits on one line.
                // This is the one instance of {{ ... }} matching that permits \n
                xml = xml.replace(/{{(.|\n)*?}}/gm, function(match) {
                    return match.replace(/\r?\n( |\t)*/g, ' ');
                });

                // Function used in many places to extract {{ label:: a hint }}.
                // Returns a little hash with various parts of the hint:
                // hint: the hint or empty, nothint: the rest
                // labelassign: javascript assignment of label attribute, or empty
                extractHint = function(inputText, detectParens) {
                    var text = inputText,
                        curly = /\s*{{(.*?)}}/.exec(text),
                        hint = '',
                        label = '',
                        parens = false,
                        labelassign = '',
                        labelmatch;
                    if (curly) {
                        text = text.replace(curly[0], '');
                        hint = curly[1].trim();
                        labelmatch = /^(.*?)::/.exec(hint);
                        if (labelmatch) {
                            hint = hint.replace(labelmatch[0], '').trim();
                            label = labelmatch[1].trim();
                            labelassign = ' label="' + label + '"';
                        }
                    }
                    if (detectParens) {
                        if (text.length >= 2 && text[0] === '(' && text[text.length - 1] === ')') {
                            text = text.substring(1, text.length - 1);
                            parens = true;
                        }
                    }
                    return {
                        nothint: text,
                        hint: hint,
                        label: label,
                        parens: parens,
                        labelassign: labelassign
                    };
                };


                // replace selects
                // [[ a, b, (c) ]]
                // [[
                //     a
                //     b
                //     (c)
                //  ]]
                // <optionresponse>
                //  <optioninput>
                //     <option  correct="True">AAA<optionhint  label="Good Job">
                //          Yes, multiple choice is the right answer.
                //  </optionhint>
                // Note: part of the option-response syntax looks like multiple-choice, so it must be processed first.
                xml = xml.replace(/\[\[((.|\n)+?)\]\]/g, function(match, group1) {
                    var textHint, options, optiontag, correct, lines, optionlines, line, correctstr, hintstr, label;
                    // decide if this is old style or new style
                    if (match.indexOf('\n') === -1) {  // OLD style, [[ .... ]]  on one line
                        options = group1.split(/\,\s*/g);
                        optiontag = '  <optioninput options="(';
                        for (i = 0; i < options.length; i += 1) {
                            optiontag += "'" + options[i].replace(/(?:^|,)\s*\((.*?)\)\s*(?:$|,)/g, '$1') + "'" +
                                (i < options.length - 1 ? ',' : '');
                        }
                        optiontag += ')" correct="';
                        correct = /(?:^|,)\s*\((.*?)\)\s*(?:$|,)/g.exec(group1);
                        if (correct) {
                            optiontag += correct[1];
                        }
                        optiontag += '">';
                        return '\n<optionresponse>\n' + optiontag + '</optioninput>\n</optionresponse>\n\n';
                    }

                    // new style  [[ many-lines ]]
                    lines = group1.split('\n');
                    optionlines = '';
                    for (i = 0; i < lines.length; i++) {
                        line = lines[i].trim();
                        if (line.length > 0) {
                            textHint = extractHint(line, true);
                            correctstr = ' correct="' + (textHint.parens ? 'True' : 'False') + '"';
                            hintstr = '';
                            if (textHint.hint) {
                                label = textHint.label;
                                if (label) {
                                    label = ' label="' + label + '"';
                                }
                                hintstr = ' <optionhint' + label + '>' + textHint.hint + '</optionhint>';
                            }
                            optionlines += '    <option' + correctstr + '>' + textHint.nothint + hintstr +
                                '</option>\n';
                        }
                    }
                    return '\n<optionresponse>\n  <optioninput>\n' + optionlines +
                        '  </optioninput>\n</optionresponse>\n\n';
                });

                // multiple choice questions
                //
                xml = xml.replace(/(^\s*\(.{0,3}\).*?$\n*)+/gm, function(match) {
                    var choices = '',
                        shuffle = false,
                        options = match.split('\n'),
                        value, inparens, correct,
                        fixed, hint, result;
                    for (i = 0; i < options.length; i++) {
                        options[i] = options[i].trim();                   // trim off leading/trailing whitespace
                        if (options[i].length > 0) {
                            value = options[i].split(/^\s*\(.{0,3}\)\s*/)[1];
                            inparens = /^\s*\((.{0,3})\)\s*/.exec(options[i])[1];
                            correct = /x/i.test(inparens);
                            fixed = '';
                            if (/@/.test(inparens)) {
                                fixed = ' fixed="true"';
                            }
                            if (/!/.test(inparens)) {
                                shuffle = true;
                            }

                            hint = extractHint(value);
                            if (hint.hint) {
                                value = hint.nothint;
                                value = value + ' <choicehint' + hint.labelassign + '>' + hint.hint + '</choicehint>';
                            }
                            choices += '    <choice correct="' + correct + '"' + fixed + '>' + value + '</choice>\n';
                        }
                    }
                    result = '<multiplechoiceresponse>\n';
                    if (shuffle) {
                        result += '  <choicegroup type="MultipleChoice" shuffle="true">\n';
                    } else {
                        result += '  <choicegroup type="MultipleChoice">\n';
                    }
                    result += choices;
                    result += '  </choicegroup>\n';
                    result += '</multiplechoiceresponse>\n\n';
                    return result;
                });

                // group check answers
                // [.] with {{...}} lines mixed in
                xml = xml.replace(/(^\s*((\[.?\])|({{.*?}})).*?$\n*)+/gm, function(match) {
                    var groupString = '<choiceresponse>\n',
                        options = match.split('\n'),
                        value, correct, abhint, endHints, hintbody,
                        hint, inner, select, hints;

                    groupString += '  <checkboxgroup>\n';
                    endHints = '';  // save these up to emit at the end

                    for (i = 0; i < options.length; i += 1) {
                        if (options[i].trim().length > 0) {
                            // detect the {{ ((A*B)) ...}} case first
                            // emits: <compoundhint value="A*B">AB hint</compoundhint>

                            abhint = /^\s*{{\s*\(\((.*?)\)\)(.*?)}}/.exec(options[i]);
                            if (abhint) {
                                // lone case of hint text processing outside of extractHint, since syntax here is unique
                                hintbody = abhint[2];
                                hintbody = hintbody.replace('&lf;', '\n').trim();
                                endHints += '    <compoundhint value="' + abhint[1].trim() + '">' + hintbody +
                                    '</compoundhint>\n';
                                continue;  // bail
                            }

                            value = options[i].split(/^\s*\[.?\]\s*/)[1];
                            correct = /^\s*\[x\]/i.test(options[i]);
                            hints = '';
                            //  {{ selected: You’re right that apple is a fruit. },
                            //   {unselected: Remember that apple is also a fruit.}}
                            hint = extractHint(value);
                            if (hint.hint) {
                                inner = '{' + hint.hint + '}';  // parsing is easier if we put outer { } back

                                // include \n since we are downstream of extractHint()
                                select = /{\s*(s|selected):((.|\n)*?)}/i.exec(inner);
                                // checkbox choicehints get their own line, since there can be two of them
                                // <choicehint selected="true">You’re right that apple is a fruit.</choicehint>
                                if (select) {
                                    hints += '\n      <choicehint selected="true">' + select[2].trim() +
                                        '</choicehint>';
                                }
                                select = /{\s*(u|unselected):((.|\n)*?)}/i.exec(inner);
                                if (select) {
                                    hints += '\n      <choicehint selected="false">' + select[2].trim() +
                                        '</choicehint>';
                                }

                                // Blank out the original text only if the specific "selected" syntax is found
                                // That way, if the user types it wrong, at least they can see it's not processed.
                                if (hints) {
                                    value = hint.nothint;
                                }
                            }
                            groupString += '    <choice correct="' + correct + '">' + value + hints + '</choice>\n';
                        }
                    }

                    groupString += endHints;
                    groupString += '  </checkboxgroup>\n';
                    groupString += '</choiceresponse>\n\n';

                    return groupString;
                });


                // replace string and numerical, numericalresponse, stringresponse
                // A fine example of the function-composition programming style.
                xml = xml.replace(/(^s?\=\s*(.*?$)(\n*(or|not)\=\s*(.*?$))*)+/gm, function(match, p) {
                    // Line split here, trim off leading xxx= in each function
                    var answersList = p.split('\n'),

                        isRangeToleranceCase = function(answer) {
                            return _.contains(
                                ['[', '('], answer[0]) && _.contains([']', ')'], answer[answer.length - 1]
                            );
                        },

                        getAnswerData = function(answerValue) {
                            var answerData = {},
                                answerParams = /(.*?)\+\-\s*(.*?$)/.exec(answerValue);
                            if (answerParams) {
                                answerData.answer = answerParams[1].replace(/\s+/g, ''); // inputs like 5*2 +- 10
                                answerData.default = answerParams[2];
                            } else {
                                answerData.answer = answerValue.replace(/\s+/g, ''); // inputs like 5*2
                            }
                            return answerData;
                        },

                        processNumericalResponse = function(answerValues) {
                            var firstAnswer, answerData, numericalResponseString, additionalAnswerString,
                                textHint, hintLine, additionalTextHint, additionalHintLine, orMatch, hasTolerance;

                            // First string case is s?= [e.g. = 100]
                            firstAnswer = answerValues[0].replace(/^\=\s*/, '');

                            // If answer is not numerical
                            if (isNaN(parseFloat(firstAnswer)) && !isRangeToleranceCase(firstAnswer)) {
                                return false;
                            }

                            textHint = extractHint(firstAnswer);
                            hintLine = '';
                            if (textHint.hint) {
                                firstAnswer = textHint.nothint;
                                // xss-lint: disable=javascript-concat-html
                                hintLine = '  <correcthint' + textHint.labelassign + '>' +
                                // xss-lint: disable=javascript-concat-html
                                    textHint.hint + '</correcthint>\n';
                            }

                            // Range case
                            if (isRangeToleranceCase(firstAnswer)) {
                                // [5, 7) or (5, 7), or (1.2345 * (2+3), 7*4 ]  - range tolerance case
                                // = (5*2)*3 should not be used as range tolerance
                                // xss-lint: disable=javascript-concat-html
                                numericalResponseString = '<numericalresponse answer="' + firstAnswer + '">\n';
                            } else {
                                answerData = getAnswerData(firstAnswer);
                                // xss-lint: disable=javascript-concat-html
                                numericalResponseString = '<numericalresponse answer="' + answerData.answer + '">\n';
                                if (answerData.default) {
                                    // xss-lint: disable=javascript-concat-html
                                    numericalResponseString += '  <responseparam type="tolerance" default="' +
                                    // xss-lint: disable=javascript-concat-html
                                        answerData.default + '" />\n';
                                }
                            }

                            // Additional answer case or= [e.g. or= 10]
                            // Since answerValues[0] is firstAnswer, so we will not include this in additional answers.
                            additionalAnswerString = '';
                            for (i = 1; i < answerValues.length; i++) {
                                additionalHintLine = '';
                                additionalTextHint = extractHint(answerValues[i]);
                                orMatch = /^or\=\s*(.*)/.exec(additionalTextHint.nothint);
                                if (orMatch) {
                                    hasTolerance = /(.*?)\+\-\s*(.*?$)/.exec(orMatch[1]);
                                    // Do not add additional_answer if additional answer is not numerical (eg. or= ABC)
                                    // or contains range tolerance case (eg. or= (5,7)
                                    // or has tolerance (eg. or= 10 +- 0.02)
                                    if (isNaN(parseFloat(orMatch[1])) ||
                                        isRangeToleranceCase(orMatch[1]) ||
                                        hasTolerance) {
                                        continue;
                                    }

                                    if (additionalTextHint.hint) {
                                        // xss-lint: disable=javascript-concat-html
                                        additionalHintLine = '<correcthint' +
                                            // xss-lint: disable=javascript-concat-html
                                            additionalTextHint.labelassign + '>' +
                                            // xss-lint: disable=javascript-concat-html
                                            additionalTextHint.hint + '</correcthint>';
                                    }

                                    // xss-lint: disable=javascript-concat-html
                                    additionalAnswerString += '  <additional_answer answer="' + orMatch[1] + '">';
                                    additionalAnswerString += additionalHintLine;
                                    additionalAnswerString += '</additional_answer>\n';
                                }
                            }

                            // Add additional answers string to numerical problem string.
                            if (additionalAnswerString) {
                                numericalResponseString += additionalAnswerString;
                            }

                            numericalResponseString += '  <formulaequationinput />\n';
                            numericalResponseString += hintLine;
                            numericalResponseString += '</numericalresponse>\n\n';

                            return numericalResponseString;
                        },

                        processStringResponse = function(values) {
                            var firstAnswer, textHint, typ, string, orMatch, notMatch;
                            // First string case is s?=
                            firstAnswer = values.shift();
                            firstAnswer = firstAnswer.replace(/^s?\=\s*/, '');
                            textHint = extractHint(firstAnswer);
                            firstAnswer = textHint.nothint;
                            typ = ' type="ci"';
                            if (firstAnswer[0] === '|') { // this is regexp case
                                typ = ' type="ci regexp"';
                                firstAnswer = firstAnswer.slice(1).trim();
                            }
                            string = '<stringresponse answer="' + firstAnswer + '"' + typ + ' >\n';
                            if (textHint.hint) {
                                string += '  <correcthint' + textHint.labelassign + '>' +
                                    textHint.hint + '</correcthint>\n';
                            }

                            // Subsequent cases are not= or or=
                            for (i = 0; i < values.length; i += 1) {
                                textHint = extractHint(values[i]);
                                notMatch = /^not\=\s*(.*)/.exec(textHint.nothint);
                                if (notMatch) {
                                    string += '  <stringequalhint answer="' + notMatch[1] + '"' +
                                        textHint.labelassign + '>' + textHint.hint + '</stringequalhint>\n';
                                    continue;
                                }
                                orMatch = /^or\=\s*(.*)/.exec(textHint.nothint);
                                if (orMatch) {
                                    // additional_answer with answer= attribute
                                    string += '  <additional_answer answer="' + orMatch[1] + '">';
                                    if (textHint.hint) {
                                        string += '<correcthint' + textHint.labelassign + '>' +
                                            textHint.hint + '</correcthint>';
                                    }
                                    string += '</additional_answer>\n';
                                }
                            }

                            string += '  <textline size="20"/>\n</stringresponse>\n\n';

                            return string;
                        };

                    return processNumericalResponse(answersList) || processStringResponse(answersList);
                });


                // replace explanations
                xml = xml.replace(/\[explanation\]\n?([^\]]*)\[\/?explanation\]/gmi, function(match, p1) {
                    return '<solution>\n<div class="detailed-solution">\n' +
                        gettext('Explanation') + '\n\n' + p1 + '\n</div>\n</solution>';
                });

                // replace code blocks
                xml = xml.replace(/\[code\]\n?([^\]]*)\[\/?code\]/gmi, function(match, p1) {
                    return '<pre><code>' + p1 + '</code></pre>';
                });

                // split scripts and preformatted sections, and wrap paragraphs
                splits = xml.split(/(\<\/?(?:script|pre|label|description).*?\>)/g);

                // Wrap a string by <p> tag when line is not already wrapped by another tag
                // true when line is not already wrapped by another tag false otherwise
                makeParagraph = true;

                for (i = 0; i < splits.length; i += 1) {
                    if (/\<(script|pre|label|description)/.test(splits[i])) {
                        makeParagraph = false;
                    }

                    if (makeParagraph) {
                        splits[i] = splits[i].replace(/(^(?!\s*\<|$).*$)/gm, '<p>$1</p>');
                    }

                    if (/\<\/(script|pre|label|description)/.test(splits[i])) {
                        makeParagraph = true;
                    }
                }

                xml = splits.join('');

                // rid white space
                xml = xml.replace(/\n\n\n/g, '\n');

                // if we've come across demand hints, wrap in <demandhint> at the end
                if (demandhints) {
                    demandHintTags.push(demandhints);
                }

                // make selector to search responsetypes in xml
                responseTypesSelector = responseTypes.join(', ');

                // make temporary xml
                // xss-lint: disable=javascript-concat-html
                $xml = $($.parseXML('<prob>' + xml + '</prob>'));
                responseType = $xml.find(responseTypesSelector);

                // convert if there is only one responsetype
                if (responseType.length === 1) {
                    inputtype = responseType[0].firstElementChild;
                    // used to decide whether an element should be placed before or after an inputtype
                    beforeInputtype = true;

                    _.each($xml.find('prob').children(), function(child) {
                        // we don't want to add the responsetype again into new xml
                        if (responseType[0].nodeName === child.nodeName) {
                            beforeInputtype = false;
                            return;
                        }

                        if (beforeInputtype) {
                            // xss-lint: disable=javascript-jquery-insert-into-target
                            responseType[0].insertBefore(child, inputtype);
                        } else {
                            responseType[0].appendChild(child);
                        }
                    });
                    serializer = new XMLSerializer();

                    xml = serializer.serializeToString(responseType[0]);

                    // remove xmlns attribute added by the serializer
                    xml = xml.replace(/\sxmlns=['"].*?['"]/gi, '');

                    // XMLSerializer messes the indentation of XML so add newline
                    // at the end of each ending tag to make the xml looks better
                    xml = xml.replace(/(\<\/.*?\>)(\<.*?\>)/gi, '$1\n$2');
                }

                // remove class attribute added on <p> tag for question title
                xml = xml.replace(/\sclass=\'qtitle\'/gi, '');
                return xml;
            };
            responseTypesXML = [];
            responseTypesMarkdown = markdown.split(/\n\s*---\s*\n/g);
            _.each(responseTypesMarkdown, function(responseTypeMarkdown) {
                if (responseTypeMarkdown.trim().length > 0) {
                    responseTypesXML.push(toXml(responseTypeMarkdown));
                }
            });
            finalDemandHints = '';
            if (demandHintTags.length) {
                // xss-lint: disable=javascript-concat-html
                finalDemandHints = '\n<demandhint>\n' + demandHintTags.join('') + '</demandhint>';
            }
            // make all responsetypes descendants of a single problem element
            // xss-lint: disable=javascript-concat-html
            finalXml = '<problem>\n' + responseTypesXML.join('\n\n') + finalDemandHints + '\n</problem>';
            return finalXml;
        };

        return MarkdownEditingDescriptor;
    }(this));
}).call(this);

function CapaXBlockMarkdownEditor(element) {
    'use strict';
    new CapaMarkdownEditor(element);
}
