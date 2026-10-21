<script setup>
import { computed } from 'vue'

// Brand logo with a graceful fallback: a brand may have no logo (FR-CAT-007),
// in which case its initial is shown instead of a broken image.
const props = defineProps({
  brand: { type: Object, required: true },
})

const hasLogo = computed(() => Boolean(props.brand?.logo))
const initial = computed(() => (props.brand?.name || '?').trim().charAt(0).toUpperCase())
</script>

<template>
  <span class="brand-logo">
    <img
      v-if="hasLogo"
      class="brand-logo-image"
      :src="brand.logo"
      :alt="`${brand.name} logo`"
      loading="lazy"
    />
    <span v-else class="brand-logo-fallback" aria-hidden="true" :title="brand.name">
      {{ initial }}
    </span>
  </span>
</template>
