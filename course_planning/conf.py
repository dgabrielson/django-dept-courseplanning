"""
The DEFAULT configuration is loaded when the named _CONFIG dictionary
is not present in your settings.
"""
#########################################################################
from __future__ import print_function, unicode_literals

from django.conf import settings

#########################################################################

CONFIG_NAME = "COURSE_PLANNING_CONFIG"  # must be uppercase!

#########################################################################

DEFAULT = {
    # a list of section types for consideration in various places.
    "valid_section_types": ["cl", "on"],
    "spreadsheet_formats": (
        ("csv", "Comma Seperated Values"),
        # ('xls', 'Microsoft Excel (old)'),
        ("xlsx", "Microsoft Excel"),
        ("ods", "OpenOffice Spreadsheet"),
    ),
    # Define the default spreadsheet format in the form.
    # (optional)
    "default_spreadsheet_format": "xlsx",
    "program:description:help_text": """About the program. This will be processed as
<a href="http://docutils.sourceforge.net/docs/user/rst/quickref.html" target="_blank">
ReStructuredText</a>.""",
}

#########################################################################


def get(setting):
    """
    get(setting) -> value

    setting should be a string representing the application settings to
    retrieve.
    """
    assert setting in DEFAULT, "the setting %r has no default value" % setting
    app_settings = getattr(settings, CONFIG_NAME, DEFAULT)
    return app_settings.get(setting, DEFAULT[setting])


#########################################################################


def get_all():
    """
    Return all current settings as a dictionary.
    """
    app_settings = getattr(settings, CONFIG_NAME, DEFAULT)
    return dict(
        [(setting, app_settings.get(setting, DEFAULT[setting])) for setting in DEFAULT]
    )


#########################################################################
