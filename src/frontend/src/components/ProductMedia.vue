<script setup>
// Product media shared by the product pages and the product cards: the
// product image when there is one, the product initial otherwise.
defineProps({
  image: { type: Object, default: null },
  name: { type: String, required: true },
  lazy: { type: Boolean, default: true },
})
</script>

<template>
  <img
    v-if="image && image.url"
    class="product-media-image"
    :src="image.url"
    :alt="image.alt || name"
    :loading="lazy ? 'lazy' : undefined"
  />
  <span v-else class="product-media-fallback">{{ name.slice(0, 1).toUpperCase() }}</span>
</template>
