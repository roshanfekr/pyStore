<script setup>
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

import { api } from '@/api/client'
import { useStorefrontStore } from '@/stores/storefront'

const store = useStorefrontStore()
const router = useRouter()
const items = ref([])

onMounted(async () => {
  if (!store.user.is_authenticated) {
    router.push('/login/')
    return
  }
  items.value = await api('/storefront/wishlist')
})

async function remove(item) {
  items.value = await api(`/storefront/wishlist/${item.product.id}`, { method: 'DELETE' })
}

async function move(item) {
  items.value = await api('/storefront/wishlist/move', {
    method: 'POST',
    body: { product: item.product.slug },
  })
  await store.refreshCart()
}
</script>

<template>
  <div class="page-title">
    <h2>Wishlist</h2>
  </div>
  <div v-if="!items.length" class="empty-state">Your wishlist is empty.</div>
  <div v-else class="product-grid">
    <article v-for="item in items" :key="item.id" class="product-card">
      <div class="product-card-body">
        <div class="product-card-title">
          <a :href="`/product/${item.product.slug}/`">{{ item.product.name }}</a>
        </div>
        <div class="price">{{ item.product.price }}</div>
        <button type="button" @click="move(item)">Move to cart</button>
        <button class="btn-secondary" type="button" @click="remove(item)">Remove</button>
      </div>
    </article>
  </div>
</template>
