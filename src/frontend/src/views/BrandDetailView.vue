<script setup>
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'

import BrandLogo from '@/components/BrandLogo.vue'
import ProductMedia from '@/components/ProductMedia.vue'
import { api } from '@/api/client'
import { applySeo, resetSeo } from '@/composables/seo'
import { useStorefrontStore } from '@/stores/storefront'

// Brand detail (FR-CAT-006, FR-CAT-007): the brand's own published products,
// listed with the existing product API and the ?brand=<slug> filter.
const route = useRoute()
const store = useStorefrontStore()

const brand = ref(null)
const products = ref([])
const loading = ref(true)
const error = ref('')
const notFound = ref(false)

onMounted(async () => {
  try {
    const data = await api(`/brands/${encodeURIComponent(route.params.slug)}`)
    brand.value = data
    applySeo({
      title: data.effective_meta_title || data.name,
      description: data.effective_meta_description || data.description || '',
    })
    const query = new URLSearchParams({ brand: data.slug })
    const listing = await api(`/products?${query.toString()}`)
    products.value = listing?.results ?? []
  } catch (err) {
    if (err.status === 404) {
      // An inactive or unknown brand is not exposed publicly.
      notFound.value = true
    } else {
      error.value = err.message || 'Unable to load this brand.'
    }
  } finally {
    loading.value = false
  }
})

onBeforeUnmount(() => resetSeo(store.branding.site_name))
</script>

<template>
  <p v-if="loading" class="empty-state">Loading brand…</p>

  <div v-else-if="notFound" class="empty-state">This brand is not available.</div>

  <p v-else-if="error" class="error">{{ error }}</p>

  <template v-else-if="brand">
    <div class="brand-header">
      <div class="brand-header-logo">
        <BrandLogo :brand="brand" />
      </div>
      <div>
        <h2 class="brand-header-name">{{ brand.name }}</h2>
        <p v-if="brand.description" class="brand-description">{{ brand.description }}</p>
      </div>
    </div>

    <div class="page-title">
      <h3>Products</h3>
      <span class="count">{{ products.length }} items</span>
    </div>

    <div v-if="!products.length" class="empty-state">No products in this brand yet.</div>
    <div v-else class="product-grid">
      <article v-for="product in products" :key="product.id" class="product-card">
        <div class="product-card-media">
          <ProductMedia :name="product.name" />
        </div>
        <div class="product-card-body">
          <div class="product-card-title">
            <RouterLink :to="`/product/${product.slug}/`">{{ product.name }}</RouterLink>
          </div>
          <div class="price">{{ product.price }}</div>
        </div>
      </article>
    </div>
  </template>
</template>
