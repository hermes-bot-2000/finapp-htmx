"""Template filters for budget math (e.g. percentage of budget spent)."""
from django import template

register = template.Library()


@register.filter
def div(value, arg):
    """Divide ``value`` by ``arg`` (returns 0.0 on invalid/zero arg)."""
    try:
        arg = float(arg)
        if arg == 0:
            return 0.0
        return float(value) / arg
    except (ValueError, TypeError):
        return 0.0


@register.filter
def mul(value, arg):
    """Multiply ``value`` by ``arg``."""
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0.0
