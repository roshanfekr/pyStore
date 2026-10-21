// Document metadata for storefront pages.
//
// App.vue keeps the document title in sync with the active theme; a page
// overrides it while it is mounted and restores the store title on unmount.

export function applySeo({ title, description } = {}) {
  if (title) {
    document.title = title
  }
  if (description !== undefined && description !== null) {
    let tag = document.querySelector('meta[name="description"]')
    if (!tag) {
      tag = document.createElement('meta')
      tag.setAttribute('name', 'description')
      document.head.appendChild(tag)
    }
    tag.setAttribute('content', description)
  }
}

export function resetSeo(siteName) {
  document.title = siteName || 'pyStore'
  const tag = document.querySelector('meta[name="description"]')
  if (tag) {
    tag.setAttribute('content', '')
  }
}
