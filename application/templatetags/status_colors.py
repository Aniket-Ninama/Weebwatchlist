from django import template

register = template.Library()

@register.filter
def status_color(status):
    return {
        'completed': 'bg-green-600',
        'ongoing': 'bg-blue-600',
        'upcoming': 'bg-yellow-600',
        'cancelled': 'bg-red-600'
    }.get(status.lower(), 'bg-gray-600')  # default color if unknown
