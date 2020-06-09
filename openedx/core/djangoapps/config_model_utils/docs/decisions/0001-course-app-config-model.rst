Course App Config Model
=======================

Status
------

Proposal


Context
-------

During the development of discussions plugins, a need arose for a system of
configuration that would allow admins to configure connections to different
discussion tools, and have course authors select an established configuration
without needing to share any secrets.

For example, a discussion tool provider might require admins to specify OAuth2
credentials that will be needed to integrate their tool with the platform. This
needs to be configured by an admin, and used by a course, but ideally course
authors should not have access to this information.

It would also be useful to have multiple sets of configuration for different
discussion tools. A course admin can then select one of the available
configurations based on their requirements.

Additionally, we might want to prevent certain configurations to be available
to all courses on a site. So it would be useful to limit configuration options
to a specific site, org, course, or course run.

This ADR proposes a new abstract configuration model that can be used by course
apps to store their configuration in a way that can be easily configured by
admins/staff with different levels of access.

The `StackedConfiguration` model might seem like a close match for this but it
works in a different way than what is ideal here.

First of all, we do not need stacking in this case, since we are dealing with
configurations for different discussion tools that may not cleanly stack on top
of each other.

Second of all, `StackedConfiguration` can only provide one configuration set
whereas we need support for multiple configuration profiles.

Decision
--------

We can create a new `CourseAppConfigOptionsModel` Django model that derives
from `ConfigurationModel`. This model shares some logic with the
`StackedConfiguration` model but works in a completely different way.

In the `StackedConfiguration` model, values set at different levels, site, org,
org_course, and course all coalesce into a single configuration. Configuration
specified at the site level can be overridden by configuration at the org level
etc. For our use case though, we need to be able to support multiple
configuration profiles that might be entirely different in shape, and will
often not be derived from each other.

The new model instead treats each configuration as a separate option available
to course authors. So an org level configuration will not override a site level
configuration, but will co-exist with it. Course authors will have both options
at their disposal when configuring a course.

Since this model is based on `ConfigurationModel`it saves a new object with
each change instead of updating an existing object. This means we can't really
rely on a stable PK/ID value to identify a configuration, so instead we are
using a separate `config_key` ID that is unique for a single configuration set.
Each time you modify a configuration, it is saved with the same config key so
you can use this as a stable identifier.

This also means that a course admin can change settings at any level without
needing to update ids all over the place.

To use a configuration, it can be associated with a course via a separate
mechanism. For the case of discussions a new model will associate each learning
context with `config_key` that configures discussions for that learning
context.

Alternative Approaches
----------------------

An alternative to basing this model on the ConfigurationModel, and having each
edit save with a separate id, is to instead use Django simple history to save
historical edits. This will remove some complexity and allow us to use the
configuration id directly instead of creating a new `config_key` field.
