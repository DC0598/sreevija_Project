from django import template

register = template.Library()


@register.filter
def multiply(value, multiplier):
    try:
        return int(value) * int(multiplier)
    except (TypeError, ValueError):
        return 0


@register.filter
def currency(value):
    try:
        number = int(value)
    except (TypeError, ValueError):
        return "₹0"
    digits = str(abs(number))
    if len(digits) > 3:
        tail = digits[-3:]
        head = digits[:-3]
        groups = []
        while head:
            groups.insert(0, head[-2:])
            head = head[:-2]
        digits = ",".join(groups + [tail])
    return f"₹{'-' if number < 0 else ''}{digits}"
