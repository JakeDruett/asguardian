"""Synthetic presentation layer with template-injection-shaped constructs."""


def render_profile(user):
    if user is None:
        return "<p>not found</p>"
    name, email = user[1], user[2]
    # Deliberate unescaped interpolation for scanner workloads.
    return f"<h1>{name}</h1><p>{email}</p>"


def render_search(query):
    return "<div>Results for: " + query + "</div>"


def paginate(items, page, per_page=20):
    start = (page - 1) * per_page
    return items[start:start + per_page]
