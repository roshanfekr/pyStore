<script setup>
import { onMounted, ref } from 'vue'

import { api } from '@/api/client'
import { useStorefrontStore } from '@/stores/storefront'

const store = useStorefrontStore()
const items = ref([])

onMounted(async () => {
  items.value = await api('/storefront/compare')
})

async function remove(item) {
  items.value = await api(`/storefront/compare/${item.product.id}`, { method: 'DELETE' })
}

async function addToCart(item) {
  await store.addToCart(item.product.slug, 1)
}
</script>

<template>
  <div class="page-title">
    <h2>Compare</h2>
  </div>
  <div v-if="!items.length" class="empty-state">Nothing to compare yet.</div>
  <div v-else class="product-grid">
    <article v-for="item in items" :key="item.id" class="product-card">
      <div class="product-card-body">
        <div class="product-card-title">
          <a :href="`/product/${item.product.slug}/`">{{ item.product.name }}</a>
        </div>
        <div class="price">{{ item.product.price }}</div>
        <button type="button" @click="addToCart(item)">Add to cart</button>
        <button class="btn-secondary" type="button" @click="remove(item)">Remove</button>
      </div>
    </article>
  </div>
</template>
