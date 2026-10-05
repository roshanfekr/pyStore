from django.db import models

from core.models import BaseModel


class SEOMixin(models.Model):
    meta_title = models.CharField(max_length=200, blank=True)
    meta_description = models.CharField(max_length=300, blank=True)
    canonical_url = models.CharField(max_length=500, blank=True)
    robots_meta = models.CharField(max_length=100, default="index, follow")
    og_title = models.CharField(max_length=200, blank=True)
    og_description = models.CharField(max_length=300, blank=True)
    structured_data = models.JSONField(default=dict, blank=True)

    class Meta:
        abstract = True


class Page(SEOMixin, BaseModel):
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True)
    content = models.TextField(blank=True)
    is_published = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Page"
        verbose_name_plural = "Pages"
        ordering = ["title"]

    def __str__(self):
        return self.title


class BlogCategory(BaseModel):
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True)
    description = models.TextField(blank=True)

    class Meta:
        verbose_name = "Blog category"
        verbose_name_plural = "Blog categories"

    def __str__(self):
        return self.name


class BlogPost(SEOMixin, BaseModel):
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True)
    content = models.TextField(blank=True)
    author = models.ForeignKey(
        "identity.User", null=True, blank=True, related_name="blog_posts", on_delete=models.SET_NULL
    )
    category = models.ForeignKey(
        BlogCategory, null=True, blank=True, related_name="posts", on_delete=models.SET_NULL
    )
    tags = models.JSONField(default=list, blank=True)
    is_published = models.BooleanField(default=False)
    published_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Blog post"
        verbose_name_plural = "Blog posts"
        ordering = ["-published_at"]

    def __str__(self):
        return self.title


class Menu(BaseModel):
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True)

    class Meta:
        verbose_name = "Menu"
        verbose_name_plural = "Menus"

    def __str__(self):
        return self.name


class MenuItem(models.Model):
    menu = models.ForeignKey(Menu, related_name="items", on_delete=models.CASCADE)
    parent = models.ForeignKey(
        "self", null=True, blank=True, related_name="children", on_delete=models.CASCADE
    )
    title = models.CharField(max_length=200)
    url = models.CharField(max_length=500, blank=True)
    page = models.ForeignKey(
        Page, null=True, blank=True, related_name="menu_items", on_delete=models.CASCADE
    )
    ordering = models.PositiveIntegerField(default=0)
    open_in_new_tab = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Menu item"
        verbose_name_plural = "Menu items"
        ordering = ["ordering"]

    def __str__(self):
        return self.title


class Widget(BaseModel):
    TYPE_HTML = "html"
    TYPE_TEXT = "text"
    TYPE_CHOICES = [(TYPE_HTML, "HTML"), (TYPE_TEXT, "Text")]

    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True)
    widget_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default=TYPE_HTML)
    content = models.TextField(blank=True)
    config = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Widget"
        verbose_name_plural = "Widgets"

    def __str__(self):
        return self.name


class ContentBlock(BaseModel):
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True)
    content = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Content block"
        verbose_name_plural = "Content blocks"

    def __str__(self):
        return self.name
