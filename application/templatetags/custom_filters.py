from django import template
from django.utils.timesince import timesince
from django.utils.timezone import now

register = template.Library()

@register.filter
def custom_time_display(value):
    """
    Format post timestamp like:
    - '2 minutes ago'
    - '1 hour ago'
    - '3 hours ago'
    - 'Jun 17' (for older than 1 day)
    """
    if not value:
        return ''

    delta = now() - value

    if delta.days >= 1:
        return value.strftime('%b %d')  # Example: Jun 17
    elif delta.seconds >= 3600:
        hours = delta.seconds // 3600
        return f"{hours} hour{'s' if hours > 1 else ''} ago"
    elif delta.seconds >= 60:
        minutes = delta.seconds // 60
        return f"{minutes} minute{'s' if minutes > 1 else ''} ago"
    else:
        return "Just now"