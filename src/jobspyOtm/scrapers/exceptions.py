"""
jobspy.scrapers.exceptions
~~~~~~~~~~~~~~~~~~~

This module contains the set of Scrapers' exceptions.
"""


class LinkedInException(Exception):
    def __init__(self, message=None):
        super().__init__(message or "An error occurred with LinkedIn")

class WTJInException(Exception):
    def __init__(self, message=None):
        super().__init__(message or "An error occurred with Welcome to jungle")

class IndeedException(Exception):
    def __init__(self, message=None):
        super().__init__(message or "An error occurred with Indeed")


class ZipRecruiterException(Exception):
    def __init__(self, message=None):
        super().__init__(message or "An error occurred with ZipRecruiter")


class GlassdoorException(Exception):
    def __init__(self, message=None):
        super().__init__(message or "An error occurred with Glassdoor")
