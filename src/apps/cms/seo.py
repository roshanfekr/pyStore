from apps.cms.models import BlogPost, Page


def _absolute(path: str, base_url: str = "") -> str:
    if base_url:
        return f"{base_url.rstrip('/')}/{path.lstrip('/')}"
    return path


def build_sitemap_items(base_url: str = "") -> list[dict]:
    items = []
    pages = Page.objects.filter(is_published=True)
    for page in pages:
        items.append(
            {
                "loc": _absolute(f"/{page.slug}", base_url),
                "lastmod": page.updated_at,
                "priority": "0.8",
            }
        )
    posts = BlogPost.objects.filter(is_published=True)
    for post in posts:
        items.append(
            {
                "loc": _absolute(f"/blog/{post.slug}", base_url),
                "lastmod": post.updated_at,
                "priority": "0.6",
            }
        )
    return items


def build_robots_txt(base_url: str = "") -> str:
    sitemap_url = _absolute("/sitemap.xml", base_url) if base_url else "/sitemap.xml"
    lines = [
        "User-agent: *",
        "Disallow: /admin/",
        "Disallow: /health/",
        f"Sitemap: {sitemap_url}",
    ]
    return "\n".join(lines)


def get_seo_metadata(obj, base_url: str = "") -> dict:
    title = getattr(obj, "meta_title", "") or getattr(obj, "title", "")
    description = getattr(obj, "meta_description", "") or getattr(obj, "description", "") or getattr(obj, "content", "")
    if description and len(description) > 300:
        description = description[:297] + "..."

    is_post = isinstance(obj, BlogPost)
    path = f"/blog/{obj.slug}" if is_post else f"/{obj.slug}"
    canonical = getattr(obj, "canonical_url", "") or _absolute(path, base_url)

    og_title = getattr(obj, "og_title", "") or title
    og_description = getattr(obj, "og_description", "") or description

    default_structured = {
        "@context": "https://schema.org",
        "@type": "BlogPosting" if is_post else "WebPage",
        "name": title,
        "description": description,
    }
    structured = {**default_structured, **(getattr(obj, "structured_data", {}) or {})}
    if base_url:
        structured.setdefault("url", _absolute(path, base_url))

    return {
        "title": title,
        "description": description,
        "canonical": canonical,
        "robots": getattr(obj, "robots_meta", "index, follow"),
        "opengraph": {
            "og:title": og_title,
            "og:description": og_description,
            "og:type": "article" if is_post else "website",
            "og:url": _absolute(path, base_url),
        },
        "structured_data": structured,
    }
