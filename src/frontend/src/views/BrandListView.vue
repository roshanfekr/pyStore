<script setup>
import { onBeforeUnmount, onMounted, ref } from 'vue'

import BrandLogo from '@/components/BrandLogo.vue'
import { api } from '@/api/client'
import { applySeo, resetSeo } from '@/composables/seo'
import { useStorefrontStore } from '@/stores/storefront'

// Brand listing (FR-CAT-006): the public API returns the active brands only.
const store = useStorefrontStore()
const brands = ref([])
const loading = ref(true)
const error = ref('')

onMounted(async () => {
  applySeo({
    title: 'Brands',
    description: 'Browse the brands available in this store.',
  })
  try {
    const data = await api('/brands')
    brands.value = data?.results ?? []
  } catch (err) {
    error.value = err.message || 'Unable to load brands.'
  } finally {
    loading.value = false
  }
})

onBeforeUnmount(() => resetSeo(store.branding.site_name))
</script>

<template>
  <div class="page-title">
    <h2>Brands</h2>
    <span class="count">{{ brands.length }} {{ brands.length === 1 ? 'brand' : 'brands' }}</span>
  </div>

  <p v-if="loading" class="empty-state">Loading brands…</p>
  <p v-else-if="error" class="error">{{ error }}</p>
  <div v-else-if="!brands.length" class="empty-state">No brands are available.</div>

  <div v-else class="brand-grid">
    <article v-for="brand in brands" :key="brand.id" class="brand-card">
      <RouterLink class="brand-card-logo" :to="`/brands/${brand.slug}/`">
        <BrandLogo :brand="brand" />
      </RouterLink>
      <div class="brand-card-body">
        <div class="brand-card-title">
          <RouterLink :to="`/brands/${brand.slug}/`">{{ brand.name }}</RouterLink>
        </div>
        <p v-if="brand.description" class="brand-card-description">{{ brand.description }}</p>
      </div>
    </article>
  </div>
</template>
