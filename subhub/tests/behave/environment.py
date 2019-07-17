def before_scenario(context, scenario):
    """Seed empty HTTP headers to steps do not need to check and create."""
    context.headers = {}
    context.data = u""
    context.query = {}
