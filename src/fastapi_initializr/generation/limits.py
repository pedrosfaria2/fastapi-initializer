"""Limits shared by preview and archive generation."""


class ProjectLimitError(Exception):
    """A generated project or preview exceeds a configured limit."""
