"""
Supports rendering an XBlock to HTML using mako templates.
"""

from xblock.reference.plugins import Service

from common.djangoapps.edxmako.shortcuts import render_to_string


class MakoService(Service):
    """
    A service for rendering XBlocks to HTML using mako templates.

    Args:
        render_template(function): function that renders the given context to the given template.
    """
    def __init__(
        self,
        namespace_prefix='',
        **kwargs
    ):
        super().__init__(**kwargs)
        self.namespace_prefix = namespace_prefix

    def render_template(self, template_file, context, namespace='main'):
        """
        Takes (template_file, context) and returns rendered HTML.
        """
        return render_to_string(template_file, context, namespace=self.namespace_prefix + namespace)
