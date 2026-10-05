import io

import pytest
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.cms.models import ContentBlock, Menu, Widget
from apps.cms.seo import build_robots_txt, build_sitemap_items, get_seo_metadata
from apps.cms.services import (
    add_menu_item,
    create_blog_category,
    create_blog_post,
    create_page,
    ensure_cms_permissions,
    get_block,
    get_widget,
)
from core.exceptions import ConflictError, ValidationError

pytestmark = [pytest.mark.django_db]

User = get_user_model()


def _png_file():
    from PIL import Image

    buffer = io.BytesIO()
    image = Image.new("RGB", (800, 600), color=(200, 30, 30))
    image.save(buffer, format="PNG")
    buffer.seek(0)
    return SimpleUploadedFile("banner.png", buffer.read(), content_type="image/png")


def test_create_page_with_slug_and_seo():
    page = create_page("About Us", content="About content", meta_title="About",
                       meta_description="About us page")
    assert page.slug == "about-us"
    assert page.meta_title == "About"
    assert page.is_published is False


def test_page_slug_unique():
    create_page("Contact")
    second = create_page("Contact")
    assert second.slug == "contact-2"


def test_page_title_required():
    with pytest.raises(ValidationError):
        create_page("  ")


def test_publish_page():
    page = create_page("Published Page")
    assert page.is_published is False
    page.is_published = True
    page.save()
    page.refresh_from_db()
    assert page.is_published is True


def test_blog_category_and_post():
    category = create_blog_category("News")
    post = create_blog_post("Hello World", content="First post!", category=category, tags=["news", "hello"])

    assert post.slug == "hello-world"
    assert post.is_published is True
    assert post.published_at is not None
    assert post.tags == ["news", "hello"]
    assert category.posts.count() == 1


def test_menu_with_nested_items():
    menu = Menu.objects.create(name="Main Menu", slug="main")
    home = add_menu_item(menu, "Home", url="/")
    child = add_menu_item(menu, "About", url="/about", parent=home)

    assert home.children.count() == 1
    assert child.parent_id == home.id

    page = create_page("Support", content="support")
    support_item = add_menu_item(menu, "Support", page=page)
    assert support_item.page_id == page.id

    with pytest.raises(ValidationError):
        add_menu_item(menu, "No Target")

    with pytest.raises(ConflictError):
        add_menu_item(menu, "Home", url="/again")

    other_menu = Menu.objects.create(name="Footer", slug="footer")
    foreign_parent = add_menu_item(other_menu, "X", url="/x")
    with pytest.raises(ValidationError, match="another menu"):
        add_menu_item(menu, "Orphan", url="/y", parent=foreign_parent)


def test_widgets():
    widget = Widget.objects.create(
        name="Announcement", slug="announcement", content="<p>Sale!</p>",
        config={"show_on": ["home"]},
    )
    found = get_widget("announcement")
    assert found.id == widget.id
    assert found.config["show_on"] == ["home"]

    with pytest.raises(ValidationError):
        get_widget("missing-widget")


def test_blocks():
    ContentBlock.objects.create(name="Footer Text", slug="footer-text", content="(c) pyStore")
    assert get_block("footer-text").content == "(c) pyStore"
    with pytest.raises(ValidationError):
        get_block("nope")


def test_seo_metadata_defaults():
    page = create_page("SEO Page", content="Some content here")
    page.is_published = True
    page.save()

    meta = get_seo_metadata(page, base_url="https://shop.example.com")

    assert meta["title"] == "SEO Page"
    assert meta["description"].startswith("Some content here")
    assert meta["canonical"] == "https://shop.example.com/seo-page"
    assert meta["robots"] == "index, follow"
    assert meta["opengraph"]["og:type"] == "website"
    assert meta["opengraph"]["og:title"] == "SEO Page"
    assert meta["structured_data"]["@type"] == "WebPage"
    assert meta["structured_data"]["url"] == "https://shop.example.com/seo-page"


def test_seo_metadata_blog_post():
    post = create_blog_post("Post SEO", content="Post content", og_title="Custom OG")
    meta = get_seo_metadata(post, base_url="https://shop.example.com")

    assert meta["opengraph"]["og:type"] == "article"
    assert meta["opengraph"]["og:title"] == "Custom OG"
    assert meta["structured_data"]["@type"] == "BlogPosting"


def test_seo_metadata_truncates_long_description():
    long_content = "x" * 500
    page = create_page("Long Page", content=long_content)
    meta = get_seo_metadata(page)
    assert len(meta["description"]) == 300
    assert meta["description"].endswith("...")


def test_seo_custom_structured_data_merged():
    page = create_page("Custom SD", content="c", structured_data={"@type": "AboutPage"})
    meta = get_seo_metadata(page)
    assert meta["structured_data"]["@type"] == "AboutPage"
    assert meta["structured_data"]["name"] == "Custom SD"


def test_sitemap_includes_only_published():
    create_page("Visible Page")
    publish = create_page("Publish Me")
    publish.is_published = True
    publish.save()
    create_blog_post("Visible Post", content="c")

    items = build_sitemap_items(base_url="https://shop.example.com")
    locs = [item["loc"] for item in items]

    assert "https://shop.example.com/publish-me" in locs
    assert "https://shop.example.com/blog/visible-post" in locs
    assert "https://shop.example.com/visible-page" not in locs


def test_robots_txt():
    robots = build_robots_txt(base_url="https://shop.example.com")
    assert "Disallow: /admin/" in robots
    assert "Sitemap: https://shop.example.com/sitemap.xml" in robots


def test_media_upload_image_with_thumbnail():
    from apps.media.services import delete_media, upload_media

    media = upload_media(_png_file(), alt_text="Banner")

    assert media.media_type == "image"
    assert media.size > 0
    assert media.metadata["width"] == 800
    assert media.metadata["height"] == 600
    assert media.thumbnail.name

    delete_media(media)


def test_media_upload_video_and_file():
    from apps.media.services import upload_media

    video = SimpleUploadedFile("clip.mp4", b"VIDEOBYTES", content_type="video/mp4")
    media_video = upload_media(video)
    assert media_video.media_type == "video"
    assert not media_video.thumbnail

    document = SimpleUploadedFile("doc.pdf", b"PDF", content_type="application/pdf")
    media_file = upload_media(document)
    assert media_file.media_type == "file"


def test_media_delete_removes_files():
    from django.core.files.storage import default_storage

    from apps.media.services import delete_media, upload_media

    media = upload_media(_png_file())
    file_name = media.file.name
    thumb_name = media.thumbnail.name

    assert default_storage.exists(file_name)
    delete_media(media)
    assert default_storage.exists(file_name) is False
    assert default_storage.exists(thumb_name) is False


def test_media_requires_name():
    from apps.media.services import upload_media

    with pytest.raises(ValidationError):
        upload_media(SimpleUploadedFile("   ", b"data"))


def test_media_upload_tracks_user():
    from apps.media.services import upload_media

    user = User.objects.create_user(email="uploader@example.com", password="Str0ng!Passw0rd")
    media = upload_media(_png_file(), uploaded_by=user)
    assert media.uploaded_by_id == user.id


def test_cms_permissions_declared(db):
    from apps.identity.models import Permission

    ensure_cms_permissions()
    assert Permission.objects.filter(codename="cms.pages.manage").exists()
    assert Permission.objects.filter(codename="cms.media.manage").exists()
