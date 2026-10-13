<script setup>
import { computed, onMounted, watch } from 'vue'

import SiteFooter from '@/components/SiteFooter.vue'
import SiteHeader from '@/components/SiteHeader.vue'
import { useStorefrontStore } from '@/stores/storefront'

const store = useStorefrontStore()

onMounted(() => store.init())

const theme = computed(() => store.theme)

// Apply theme branding: document metadata, CSS variables and the theme
// stylesheet(s) discovered by the backend. This is how themes keep working
// after the move to Vue.
watch(
  theme,
  (value) => {
    const root = document.documentElement
    root.lang = store.activeLanguage.code || 'en'
    root.dir = store.activeLanguage.direction || 'ltr'
    document.title = store.branding.site_name || 'pyStore'

    const config = value?.config ?? {}
    if (config.primary_color) root.style.setProperty('--primary-color', config.primary_color)
    if (config.accent_color) root.style.setProperty('--accent-color', config.accent_color)

    document.querySelectorAll('link[data-theme-css]').forEach((el) => el.remove())
    for (const href of value?.css ?? []) {
      const link = document.createElement('link')
      link.rel = 'stylesheet'
      link.href = href
      link.dataset.themeCss = 'true'
      document.head.appendChild(link)
    }
  },
  { immediate: true },
)
</script>

<template>
  <div class="app-shell" :class="`theme-${theme.name}`">
    <SiteHeader />
    <main class="app-main">
      <RouterView />
    </main>
    <SiteFooter />
  </div>
</template>
