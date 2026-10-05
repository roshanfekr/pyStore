
from django.utils.text import slugify

from apps.cms.models import (
    BlogCategory,
    BlogPost,
    ContentBlock,
    Menu,
    MenuItem,
    Page,
    Widget,
)
from apps.identity.services.roles import ensure_permission
from core.exceptions import ConflictError, ValidationError

CMS_PERMISSIONS = [
    ("cms.pages.manage", "Manage CMS pages"),
    ("cms.blog.manage", "Manage blog"),
    ("cms.media.manage", "Manage media library"),
]


def ensure_cms_permissions() -> None:
    for codename, display_name in CMS_PERMISSIONS:
        ensure_permission(codename, display_name=display_name, source="core")


def _unique_slug(model, name: str, slug: str | None = None) -> str:
    base = slugify(slug or name) or "item"
    candidate = base
    counter = 2
    while model.objects.filter(slug=candidate).exists():
        candidate = f"{base}-{counter}"
        counter += 1
    return candidate


def create_page(title: str, *, slug: str | None = None, content: str = "", **seo_fields) -> Page:
    if not title or not title.strip():
        raise ValidationError("Page title is required", code="cms.title_required")
    page = Page.objects.create(
        title=title.strip(), slug=_unique_slug(Page, title, slug), content=content, **seo_fields
    )
    return page


def publish_page(page: Page) -> Page:
    page.is_published = True
    page.save(update_fields=["is_published"])
    return page


def create_blog_category(name: str, *, slug: str | None = None) -> BlogCategory:
    return BlogCategory.objects.create(name=name, slug=_unique_slug(BlogCategory, name, slug))


def create_blog_post(
    title: str, *, slug: str | None = None, content: str = "", author=None,
    category=None, tags=None, **seo_fields,
) -> BlogPost:
    from django.utils import timezone

    if not title or not title.strip():
        raise ValidationError("Post title is required", code="cms.title_required")
    post = BlogPost.objects.create(
        title=title.strip(),
        slug=_unique_slug(BlogPost, title, slug),
        content=content,
        author=author,
        category=category,
        tags=tags or [],
        is_published=True,
        published_at=timezone.now(),
        **seo_fields,
    )
    return post


def add_menu_item(menu: Menu, title: str, *, url: str = "", page=None, parent=None, ordering: int = 0) -> MenuItem:
    if not url and page is None:
        raise ValidationError("Menu item requires a URL or a page", code="cms.menu_item_target")
    if parent is not None and parent.menu_id != menu.id:
        raise ValidationError("Parent item belongs to another menu", code="cms.menu_item_parent")

    exists = MenuItem.objects.filter(
        menu=menu, parent=parent, title=title
    ).exists()
    if exists:
        raise ConflictError("Duplicate menu item", code="cms.menu_item_duplicate")

    return MenuItem.objects.create(
        menu=menu, title=title, url=url, page=page, parent=parent, ordering=ordering
    )


def get_widget(slug: str) -> Widget:
    widget = Widget.objects.filter(slug=slug, is_active=True).first()
    if widget is None:
        raise ValidationError(f"Widget {slug!r} not found", code="cms.widget_not_found")
    return widget


def get_block(slug: str) -> ContentBlock:
    block = ContentBlock.objects.filter(slug=slug, is_active=True).first()
    if block is None:
        raise ValidationError(f"Block {slug!r} not found", code="cms.block_not_found")
    return block
