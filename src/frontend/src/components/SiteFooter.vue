<script setup>
import { computed } from 'vue'

import { useStorefrontStore } from '@/stores/storefront'

const store = useStorefrontStore()
const branding = computed(() => store.branding)
</script>

<template>
  <footer class="site-footer">
    <div class="footer-inner">
      <div>
        <div class="footer-brand">{{ branding.site_name }}</div>
        <div>Modern e-commerce platform</div>
      </div>
      <div class="footer-links">
        <RouterLink to="/">Home</RouterLink>
        <RouterLink to="/cart/">Cart</RouterLink>
        <RouterLink to="/account/">Account</RouterLink>
      </div>
    </div>
  </footer>
</template>
