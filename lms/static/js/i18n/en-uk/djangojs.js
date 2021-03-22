

(function(globals) {

  var django = globals.django || (globals.django = {});

  
  django.pluralidx = function(n) {
    var v=(n != 1);
    if (typeof(v) == 'boolean') {
      return v ? 1 : 0;
    } else {
      return v;
    }
  };
  

  /* gettext library */

  django.catalog = django.catalog || {};
  
  var newcatalog = {
    " learner is not enrolled in course and not added to the exception list": " learner is not enrolled in programme and not added to the exception list",
    " learners are not enrolled in course and not added to the exception list": " learners are not enrolled in programme and not added to the exception list",
    "%(sel)s of %(cnt)s selected": [
      "%(sel)s of %(cnt)s selected",
      "%(sel)s of %(cnt)s selected"
    ],
    "6 a.m.": "6 a.m.",
    "A list of courses you have just enrolled in as a verified student": "A list of programmes you have just enrolled in as a verified student",
    "Adding the selected course to your cart": "Adding the selected programme to your cart",
    "After the course\\'s end date has passed, learners can no longer access subsection content. The subsection remains included in grade calculations.": "After the programme\\'s end date has passed, learners can no longer access subsection content. The subsection remains included in grade calculations.",
    "All learners who are enrolled in this course": "All learners who are enrolled in this programme",
    "All professional education courses are fee-based, and require payment to complete the enrollment process.": "All professional education programmes are fee-based, and require payment to complete the enrollment process.",
    "Allow students to generate certificates for this course?": "Allow students to generate certificates for this programme?",
    "Already a course team member": "Already a programme team member",
    "Any course progress or grades from your current session will be lost.": "Any programme progress or grades from your current session will be lost.",
    "Are you sure you want to delete {email} from the course team for \u201c{container}\u201d?": "Are you sure you want to delete {email} from the programme team for \u201c{container}\u201d?",
    "Are you sure you want to unenroll from the purchased course {courseName} ({courseNumber})?": "Are you sure you want to unenroll from the purchased programme {courseName} ({courseNumber})?",
    "As you complete courses, you will see them listed here.": "As you complete programmes, you will see them listed here.",
    "Available %s": "Available %s",
    "Browse recently launched courses and see what\\'s new in your favorite subjects": "Browse recently launched programmes and see what\\'s new in your favorite subjects",
    "COMPLETED COURSES": "COMPLETED PROGRAMMES",
    "COURSES IN PROGRESS": "PROGRAMMES IN PROGRESS",
    "Cancel": "Cancel",
    "Choose": "Choose",
    "Choose a time": "Choose a time",
    "Choose all": "Choose all",
    "Chosen %s": "Chosen %s",
    "Click to choose all %s at once.": "Click to choose all %s at once.",
    "Click to remove all chosen %s at once.": "Click to remove all chosen %s at once.",
    "Complete courses on your schedule to ensure you stand out in your field!": "Complete programmes on your schedule to ensure you stand out in your field!",
    "Course": [
      "Programme",
      "Programmes"
    ],
    "Course Content": "Programme Content",
    "Course Credit Requirements": "Programme Credit Requirements",
    "Course Discussion Forum": "Programme Discussion Forum",
    "Course End": "Programme End",
    "Course Handouts": "Programme Handouts",
    "Course ID": "Programme ID",
    "Course Index": "Programme Index",
    "Course Key": "Programme Key",
    "Course Name": "Programme Name",
    "Course Number": "Programme Number",
    "Course Number Override": "Programme Number Override",
    "Course Number:": "Programme Number:",
    "Course Outline": "Programme Outline",
    "Course Run:": "Programme Run:",
    "Course Start": "Programme Start",
    "Course Title": "Programme Title",
    "Course Title Override": "Programme Title Override",
    "Course Video Settings": "Programme Video Settings",
    "Course is not yet visible to students.": "Programme is not yet visible to students.",
    "Course pacing cannot be changed once a course has started.": "Programme pacing cannot be changed once a programme has started.",
    "Course title": "Programme title",
    "Course-Wide Discussion Topics": "Programme-Wide Discussion Topics",
    "Discussion topics in the course are not divided.": "Discussion topics in the programme are not divided.",
    "Emails successfully sent. The following users are no longer enrolled in the course:": "Emails successfully sent. The following users are no longer enrolled in the programme:",
    "Enrolling you in the selected course": "Enrolling you in the selected programme",
    "Error importing course": "Error importing programme",
    "Everyone who has staff privileges in this course": "Everyone who has staff privileges in this programme",
    "Explore your course!": "Explore your programme!",
    "Filter": "Filter",
    "Find a course": "Find a programme",
    "For inquiries regarding assignments, grades, or structure of a specific course, please post in the discussion forums for that course directly.": "For inquiries regarding assignments, grades, or structure of a specific programme, please post in the discussion forums for that programme directly.",
    "Hide": "Hide",
    "Hide content after course end date": "Hide content after programme end date",
    "ID-Verification is not required for this Professional Education course.": "ID-Verification is not required for this Professional Education programme.",
    "If the course does not have an end date, learners always see their scores when they submit answers to assessments.": "If the programme does not have an end date, learners always see their scores when they submit answers to assessments.",
    "If you don't verify your identity now, you can still explore your course from your dashboard. You will receive periodic reminders from %(platformName)s to verify your identity.": "If you don't verify your identity now, you can still explore your programme from your dashboard. You will receive periodic reminders from %(platformName)s to verify your identity.",
    "If you don't verify your identity now, you can still explore your course from your dashboard. You will receive periodic reminders from {platformName} to verify your identity.": "If you don't verify your identity now, you can still explore your programme from your dashboard. You will receive periodic reminders from {platformName} to verify your identity.",
    "If you proceed, you will be unable to use this account to take courses on the {platformName} app, {siteName}, or any other site hosted by {platformName}.": "If you proceed, you will be unable to use this account to take programmes on the {platformName} app, {siteName}, or any other site hosted by {platformName}.",
    "In the {linkStart}Course Outline{linkEnd}, use this group to control access to a component.": "In the {linkStart}Programme Outline{linkEnd}, use this group to control access to a component.",
    "Learners do not see the subsection in the course outline. The subsection is not included in grade calculations.": "Learners do not see the subsection in the programme outline. The subsection is not included in grade calculations.",
    "Learners do not see whether their answers to assessments were correct or incorrect, nor the score received, until after the course end date has passed.": "Learners do not see whether their answers to assessments were correct or incorrect, nor the score received, until after the programme end date has passed.",
    "List of uploaded files and assets in this course": "List of uploaded files and assets in this programme",
    "Loading your courses": "Loading your programmes",
    "Location in Course": "Location in Programme",
    "Midnight": "Midnight",
    "Noon": "Noon",
    "Not specific to a course": "Not specific to a programme",
    "Now": "Now",
    "Once your account is deleted, you cannot use it to take courses on the {platformName} app, {siteName}, or any other site hosted by {platformName}.": "Once your account is deleted, you cannot use it to take programmes on the {platformName} app, {siteName}, or any other site hosted by {platformName}.",
    "Only the parent course staff of a CCX can create content groups.": "Only the parent programme staff of a CCX can create content groups.",
    "Please check the following validation feedbacks and reflect them in your course settings:": "Please check the following validation feedbacks and reflect them in your programme settings:",
    "Press close to hide course video settings": "Press close to hide programme video settings",
    "Press update settings to update course video settings": "Press update settings to update programme video settings",
    "Prevent students from generating certificates in this course?": "Prevent students from generating certificates in this programme?",
    "REMAINING COURSES": "REMAINING PROGRAMMES",
    "Re-run Course": "Re-run Programme",
    "Remove": "Remove",
    "Remove all": "Remove all",
    "Removing a video from this list does not affect course content. Any content that uses a previously uploaded video ID continues to display in the course.": "Removing a video from this list does not affect programme content. Any content that uses a previously uploaded video ID continues to display in the programme.",
    "See all teams you belong to and all public teams in your course, organized by topic.": "See all teams you belong to and all public teams in your programme, organized by topic.",
    "See all teams you belong to and all public teams in your course, organized by topic. Join an open public team to collaborate with other learners who are interested in the same topic as you are.": "See all teams you belong to and all public teams in your programme, organized by topic. Join an open public team to collaborate with other learners who are interested in the same topic as you are.",
    "Select a course or select \"Not specific to a course\" for your support request.": "Select a programme or select \"Not specific to a programme\" for your support request.",
    "Select the course-wide discussion topics that you want to divide.": "Select the programme-wide discussion topics that you want to divide.",
    "Select the time zone for displaying course dates. If you do not specify a time zone, course dates, including assignment deadlines, will be displayed in your browser's local time zone.": "Select the time zone for displaying programme dates. If you do not specify a time zone, programme dates, including assignment deadlines, will be displayed in your browser's local time zone.",
    "Sequence error! Cannot navigate to %(tab_name)s in the current SequenceModule. Please contact the course staff.": "Sequence error! Cannot navigate to %(tab_name)s in the current SequenceModule. Please contact the programme staff.",
    "Show": "Show",
    "Specify an alternative to the official course title to display on certificates. Leave blank to use the official course title.": "Specify an alternative to the official programme title to display on certificates. Leave blank to use the official programme title.",
    "Start generating certificates for all students in this course?": "Start generating certificates for all students in this programme?",
    "Start regenerating certificates for students in this course?": "Start regenerating certificates for students in this programme?",
    "Subsection is hidden after course end date": "Subsection is hidden after programme end date",
    "Take me to the main course page": "Take me to the main programme page",
    "Tell other learners a little about yourself: where you live, what your interests are, why you're taking courses, or what you hope to learn.": "Tell other learners a little about yourself: where you live, what your interests are, why you're taking programmes, or what you hope to learn.",
    "Thank you for setting your course goal to {goal}!": "Thank you for setting your programme goal to {goal}!",
    "Thank you for submitting your photos. We will review them shortly. You can now sign up for any %(platformName)s course that offers verified certificates. Verification is good for one year. After one year, you must submit photos for verification again.": "Thank you for submitting your photos. We will review them shortly. You can now sign up for any %(platformName)s programme that offers verified certificates. Verification is good for one year. After one year, you must submit photos for verification again.",
    "The certificate available date must be later than the course end date.": "The certificate available date must be later than the programme end date.",
    "The combined length of the organization, course number, and course run fields cannot be more than <%- limit %> characters.": "The combined length of the organization, programme number, and programme run fields cannot be more than <%- limit %> characters.",
    "The course end date must be later than the course start date.": "The programme end date must be later than the programme start date.",
    "The course must have an assigned start date.": "The programme must have an assigned start date.",
    "The course start date must be later than the enrollment start date.": "The programme start date must be later than the enrollment start date.",
    "The enrollment end date cannot be after the course end date.": "The enrollment end date cannot be after the programme end date.",
    "The following message will be displayed at the bottom of the courseware pages within your course:": "The following message will be displayed at the bottom of the courseware pages within your programme:",
    "The following users are no longer enrolled in the course:": "The following users are no longer enrolled in the programme:",
    "The minimum grade for course credit is not set.": "The minimum grade for programme credit is not set.",
    "The number of subsections in the course that contain problems of this assignment type.": "The number of subsections in the programme that contain problems of this assignment type.",
    "The refund deadline for this course has passed,so you will not receive a refund.": "The refund deadline for this programme has passed,so you will not receive a refund.",
    "There is no email history for this course.": "There is no email history for this programme.",
    "There was an error obtaining email content history for this course.": "There was an error obtaining email content history for this programme.",
    "There was an error obtaining email task history for this course.": "There was an error obtaining email task history for this programme.",
    "There was an error while importing the new course to our database.": "There was an error while importing the new programme to our database.",
    "There were errors reindexing course.": "There were errors reindexing programme.",
    "These users were not affiliated with the course so could not be unenrolled:": "These users were not affiliated with the programme so could not be unenrolled:",
    "This Group Configuration is not in use. Start by adding a content experiment to any Unit via the {linkStart}Course Outline{linkEnd}.": "This Group Configuration is not in use. Start by adding a content experiment to any Unit via the {linkStart}Programme Outline{linkEnd}.",
    "This catalog's courses:": "This catalog's programmes:",
    "This course has automatic cohorting enabled for verified track learners, but cohorts are disabled. You must enable cohorts for the feature to work.": "This programme has automatic cohorting enabled for verified track learners, but cohorts are disabled. You must enable cohorts for the feature to work.",
    "This course has automatic cohorting enabled for verified track learners, but the required cohort does not exist. You must create a manually-assigned cohort named '{verifiedCohortName}' for the feature to work.": "This programme has automatic cohorting enabled for verified track learners, but the required cohort does not exist. You must create a manually-assigned cohort named '{verifiedCohortName}' for the feature to work.",
    "This course uses automatic cohorting for verified track learners. You cannot disable cohorts, and you cannot rename the manual cohort named '{verifiedCohortName}'. To change the configuration for verified track cohorts, contact your edX partner manager.": "This programme uses automatic cohorting for verified track learners. You cannot disable cohorts, and you cannot rename the manual cohort named '{verifiedCohortName}'. To change the configuration for verified track cohorts, contact your edX partner manager.",
    "This feature is currently in testing. Course teams can enter highlights, but learners will not receive email messages.": "This feature is currently in testing. Programme teams can enter highlights, but learners will not receive email messages.",
    "This is the list of available %s. You may choose some by selecting them in the box below and then clicking the \"Choose\" arrow between the two boxes.": "This is the list of available %s. You may choose some by selecting them in the box below and then clicking the \"Choose\" arrow between the two boxes.",
    "This is the list of chosen %s. You may remove some by selecting them in the box below and then clicking the \"Remove\" arrow between the two boxes.": "This is the list of chosen %s. You may remove some by selecting them in the box below and then clicking the \"Remove\" arrow between the two boxes.",
    "To access the course, select a session.": "To access the programme, select a session.",
    "To complete the program, you must earn a verified certificate for each course.": "To complete the program, you must earn a verified certificate for each programme.",
    "To finalize course credit, {display_name} requires {platform_name} learners to submit a credit request.": "To finalize programme credit, {display_name} requires {platform_name} learners to submit a credit request.",
    "To review learner cohort assignments or see the results of uploading a CSV file, download course profile information or cohort results on the {link_start}Data Download{link_end} page.": "To review learner cohort assignments or see the results of uploading a CSV file, download programme profile information or cohort results on the {link_start}Data Download{link_end} page.",
    "Today": "Today",
    "Tomorrow": "Tomorrow",
    "Type into this box to filter down the list of available %s.": "Type into this box to filter down the list of available %s.",
    "Upgrade All Remaining Courses (": "Upgrade All Remaining Programmes (",
    "Upload your course image.": "Upload your programme image.",
    "View Archived Course": "View Archived Programme",
    "View Course": "View Programme",
    "Viewing %s course": [
      "Viewing %s programme",
      "Viewing %s programmes"
    ],
    "We have received your information and are verifying your identity. You will see a message on your dashboard when the verification process is complete (usually within 5-7 days). In the meantime, you can still access all available course content.": "We have received your information and are verifying your identity. You will see a message on your dashboard when the verification process is complete (usually within 5-7 days). In the meantime, you can still access all available programme content.",
    "While our support team is happy to assist with the edX platform, the course staff has the expertise for specific assignment questions, grading or the proper procedures in each course. Please post all course related questions within the Discussion Forum where the Course Staff can directly respond.": "While our support team is happy to assist with the edX platform, the programme staff has the expertise for specific assignment questions, grading or the proper procedures in each programme. Please post all programme related questions within the Discussion Forum where the Programme Staff can directly respond.",
    "Yesterday": "Yesterday",
    "You cannot view the course as a student or beta tester before the course release date.": "You cannot view the programme as a student or beta tester before the programme release date.",
    "You have done a dry run of force publishing the course. Nothing has changed. Had you run it, the following course versions would have been change.": "You have done a dry run of force publishing the programme. Nothing has changed. Had you run it, the following programme versions would have been change.",
    "You have selected an action, and you haven't made any changes on individual fields. You're probably looking for the Go button rather than the Save button.": "You have selected an action, and you haven't made any changes on individual fields. You're probably looking for the Go button rather than the Save button.",
    "You have selected an action, but you haven't saved your changes to individual fields yet. Please click OK to save. You'll need to re-run the action.": "You have selected an action, but you haven't saved your changes to individual fields yet. Please click OK to save. You'll need to re-run the action.",
    "You have unsaved changes on individual editable fields. If you run an action, your unsaved changes will be lost.": "You have unsaved changes on individual editable fields. If you run an action, your unsaved changes will be lost.",
    "You haven't added any assets to this course yet.": "You haven't added any assets to this programme yet.",
    "You haven't added any content to this course yet.": "You haven't added any content to this programme yet.",
    "You haven't added any textbooks to this course yet.": "You haven't added any textbooks to this programme yet.",
    "You must select a session by {expiration_date} to access the course.": "You must select a session by {expiration_date} to access the programme.",
    "You must select a session to access the course.": "You must select a session to access the programme.",
    "You need to activate your account before you can enroll in courses. Check your inbox for an activation email.": "You need to activate your account before you can enroll in programmes. Check your inbox for an activation email.",
    "You need to activate your account before you can enroll in courses. Check your inbox for an activation email. After you complete activation you can return and refresh this page.": "You need to activate your account before you can enroll in programmes. Check your inbox for an activation email. After you complete activation you can return and refresh this page.",
    "You receive messages from {platform_name} and course teams at this address.": "You receive messages from {platform_name} and programme teams at this address.",
    "Your course could not be exported to XML. There is not enough information to identify the failed component. Inspect your course to identify any problematic components and try again.": "Your programme could not be exported to XML. There is not enough information to identify the failed component. Inspect your programme to identify any problematic components and try again.",
    "Your email message was successfully queued for sending. In courses with a large number of learners, email messages to learners might take up to an hour to be sent.": "Your email message was successfully queued for sending. In programmes with a large number of learners, email messages to learners might take up to an hour to be sent.",
    "course id": "programme id",
    "{numPreassigned} learner was pre-assigned for this cohort. This learner will automatically be added to the cohort when they enroll in the course.": [
      "{numPreassigned} learner was pre-assigned for this cohort. This learner will automatically be added to the cohort when they enroll in the programme.",
      "{numPreassigned} learners were pre-assigned for this cohort. These learners will automatically be added to the cohort when they enroll in the programme."
    ]
  };
  for (var key in newcatalog) {
    django.catalog[key] = newcatalog[key];
  }
  

  if (!django.jsi18n_initialized) {
    django.gettext = function(msgid) {
      var value = django.catalog[msgid];
      if (typeof(value) == 'undefined') {
        return msgid;
      } else {
        return (typeof(value) == 'string') ? value : value[0];
      }
    };

    django.ngettext = function(singular, plural, count) {
      var value = django.catalog[singular];
      if (typeof(value) == 'undefined') {
        return (count == 1) ? singular : plural;
      } else {
        return value.constructor === Array ? value[django.pluralidx(count)] : value;
      }
    };

    django.gettext_noop = function(msgid) { return msgid; };

    django.pgettext = function(context, msgid) {
      var value = django.gettext(context + '\x04' + msgid);
      if (value.indexOf('\x04') != -1) {
        value = msgid;
      }
      return value;
    };

    django.npgettext = function(context, singular, plural, count) {
      var value = django.ngettext(context + '\x04' + singular, context + '\x04' + plural, count);
      if (value.indexOf('\x04') != -1) {
        value = django.ngettext(singular, plural, count);
      }
      return value;
    };

    django.interpolate = function(fmt, obj, named) {
      if (named) {
        return fmt.replace(/%\(\w+\)s/g, function(match){return String(obj[match.slice(2,-2)])});
      } else {
        return fmt.replace(/%s/g, function(match){return String(obj.shift())});
      }
    };


    /* formatting library */

    django.formats = {
    "DATETIME_FORMAT": "N j, Y, P",
    "DATETIME_INPUT_FORMATS": [
      "%Y-%m-%d %H:%M:%S",
      "%Y-%m-%d %H:%M:%S.%f",
      "%Y-%m-%d %H:%M",
      "%Y-%m-%d",
      "%m/%d/%Y %H:%M:%S",
      "%m/%d/%Y %H:%M:%S.%f",
      "%m/%d/%Y %H:%M",
      "%m/%d/%Y",
      "%m/%d/%y %H:%M:%S",
      "%m/%d/%y %H:%M:%S.%f",
      "%m/%d/%y %H:%M",
      "%m/%d/%y"
    ],
    "DATE_FORMAT": "N j, Y",
    "DATE_INPUT_FORMATS": [
      "%Y-%m-%d",
      "%m/%d/%Y",
      "%m/%d/%y"
    ],
    "DECIMAL_SEPARATOR": ".",
    "FIRST_DAY_OF_WEEK": 0,
    "MONTH_DAY_FORMAT": "F j",
    "NUMBER_GROUPING": 3,
    "SHORT_DATETIME_FORMAT": "m/d/Y P",
    "SHORT_DATE_FORMAT": "m/d/Y",
    "THOUSAND_SEPARATOR": ",",
    "TIME_FORMAT": "P",
    "TIME_INPUT_FORMATS": [
      "%H:%M:%S",
      "%H:%M:%S.%f",
      "%H:%M"
    ],
    "YEAR_MONTH_FORMAT": "F Y"
  };

    django.get_format = function(format_type) {
      var value = django.formats[format_type];
      if (typeof(value) == 'undefined') {
        return format_type;
      } else {
        return value;
      }
    };

    /* add to global namespace */
    globals.pluralidx = django.pluralidx;
    globals.gettext = django.gettext;
    globals.ngettext = django.ngettext;
    globals.gettext_noop = django.gettext_noop;
    globals.pgettext = django.pgettext;
    globals.npgettext = django.npgettext;
    globals.interpolate = django.interpolate;
    globals.get_format = django.get_format;

    django.jsi18n_initialized = true;
  }

}(this));

