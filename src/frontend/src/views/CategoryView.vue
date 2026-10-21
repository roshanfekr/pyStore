<script setup>
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'

import { api } from '@/api/client'
import { applySeo, resetSeo } from '@/composables/seo'
import { useStorefrontStore } from '@/stores/storefront'

// Category listing: the category itself plus its published products, using the
// existing category and product APIs.
const route = useRoute()
const store = useStorefrontStore()

const category = ref(null)
const products = ref([])
const loading = ref(true)
const error = ref('')
const unavailable = ref(false)

onMounted(async () => {
  try {
    const data = await api(`/categories/${encodeURIComponent(route.params.slug)}`)
    if (!data?.is_active) {
      // Inactive categories are not exposed on the storefront, matching the
      // server-rendered fallback.
      unavailable.value = true
      return
    }
    category.value = data
    applySeo({ title: data.name, description: data.description || '' })
    const query = new URLSearchParams({ category: data.slug })
    const listing = await api(`/products?${query.toString()}`)
    products.value = listing?.results ?? []
  } catch (err) {
    if (err.status === 404) {
      unavailable.value = true
    } else {
      error.value = err.message || 'Unable to load this category.'
    }
  } finally {
    loading.value = false
  }
})

onBeforeUnmount(() => resetSeo(store.branding.site_name))
</script>

<template>
  <p v-if="loading" class="empty-state">Loading category…</p>

  <div v-else-if="unavailable" class="empty-state">This category is not available.</div>

  <p v-else-if="error" class="error">{{ error }}</p>

  <template v-else-if="category">
    <div class="page-title">
      <h2>{{ category.name }}</h2>
      <span class="count">{{ products.length }} items</span>
    </div>

    <p v-if="category.description" class="brand-description">{{ category.description }}</p>

    <div v-if="!products.length" class="empty-state">No products in this category yet.</div>
    <div v-else class="product-grid">
      <article v-for="product in products" :key="product.id" class="product-card">
        <div class="product-card-media">{{ product.name.slice(0, 1).toUpperCase() }}</div>
        <div class="product-card-body">
          <div class="product-card-title">
            <!-- The product page is still server-rendered by Django. -->
            <a :href="`/product/${product.slug}/`">{{ product.name }}</a>
          </div>
          <div class="price">{{ product.price }}</div>
        </div>
      </article>
    </div>
  </template>
</template>
