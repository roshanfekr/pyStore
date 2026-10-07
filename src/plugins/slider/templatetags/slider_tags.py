from django import template

register = template.Library()


@register.filter
def parse_slides(raw) -> list[dict]:
    """Turn "url | caption" lines into a list of slide dicts."""
    slides: list[dict] = []
    for line in str(raw or "").splitlines():
        line = line.strip()
        if not line:
            continue
        if "|" in line:
            url, caption = line.split("|", 1)
            slides.append({"url": url.strip(), "caption": caption.strip()})
        else:
            slides.append({"url": line, "caption": ""})
    return slides
