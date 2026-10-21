<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'

import ProductMedia from '@/components/ProductMedia.vue'
import { api } from '@/api/client'
import { applySeo, resetSeo } from '@/composables/seo'
import { useStorefrontStore } from '@/stores/storefront'

// Product detail (FR-CAT-002, FR-CAT-003, FR-CAT-004): the product
// information with its images and its variant combinations. Selecting a
// combination updates the price, the SKU and the availability; the cart API
// revalidates the selection when the item is added.
const route = useRoute()
const store = useStorefrontStore()

const product = ref(null)
const loading = ref(true)
const error = ref('')
const unavailable = ref(false)

const selectedSku = ref('')
const selectedOptions = ref({})
const combinationError = ref('')
const quantity = ref(1)
const activeImage = ref(0)
const adding = ref(false)
const added = ref(false)
const addError = ref('')

onMounted(async () => {
  try {
    const data = await api(`/storefront/products/${encodeURIComponent(route.params.slug)}`)
    product.value = data
    selectedSku.value = data.selected_variant || ''
    const selected = data.variants?.find((variant) => variant.sku === selectedSku.value)
    if (selected) {
      selectedOptions.value = { ...(selected.attributes ?? {}) }
    }
    applySeo({ title: data.meta_title, description: data.meta_description })
  } catch (err) {
    if (err.status === 404) {
      // An unpublished or unknown product is not exposed, matching the
      // server-rendered fallback.
      unavailable.value = true
    } else {
      error.value = err.message || 'Unable to load this product.'
    }
  } finally {
    loading.value = false
  }
})

onBeforeUnmount(() => resetSeo(store.branding.site_name))

const variants = computed(() => product.value?.variants ?? [])
const hasVariants = computed(() => variants.value.length > 0)
const options = computed(() => product.value?.options ?? [])
const images = computed(() => product.value?.images ?? [])

const currentVariant = computed(
  () => variants.value.find((variant) => variant.sku === selectedSku.value) ?? null,
)

const displayPrice = computed(() =>
  currentVariant.value ? currentVariant.value.price : product.value?.price ?? '',
)
const displayComparePrice = computed(() =>
  currentVariant.value ? currentVariant.value.compare_at_price : product.value?.compare_at_price ?? '',
)
const displaySku = computed(() =>
  currentVariant.value ? currentVariant.value.sku : product.value?.sku ?? '',
)
const inStock = computed(() =>
  currentVariant.value ? currentVariant.value.in_stock : product.value?.in_stock ?? false,
)
const availableQuantity = computed(() =>
  currentVariant.value
    ? currentVariant.value.available_quantity
    : product.value?.available_quantity ?? null,
)
const priceAvailable = computed(() => Boolean(displayPrice.value))
const canAddToCart = computed(
  () =>
    Boolean(product.value) &&
    priceAvailable.value &&
    inStock.value &&
    !combinationError.value &&
    !adding.value,
)

function valueClasses(option, value) {
  return {
    [value.swatch ? 'swatch' : 'option-pill']: true,
    'is-disabled': !value.available,
    'is-selected': selectedOptions.value[option.slug] === value.value,
  }
}

// The option values are the combinations the variants carry: a selection that
// matches no variant is not a purchasable combination and is refused here;
// the cart API validates the selection again when the item is added.
function selectOption(option, value) {
  const selection = { ...selectedOptions.value, [option.slug]: value }
  selectedOptions.value = selection
  const matches = variants.value.filter((variant) =>
    Object.entries(selection).every(([slug, chosen]) => variant.attributes?.[slug] === chosen),
  )
  if (!matches.length) {
    selectedSku.value = ''
    combinationError.value = 'This combination is not available.'
    return
  }
  combinationError.value = ''
  if (!matches.some((variant) => variant.sku === selectedSku.value)) {
    selectedSku.value = matches[0].sku
  }
}

function selectVariant(sku) {
  selectedSku.value = sku
  combinationError.value = ''
  const variant = variants.value.find((item) => item.sku === sku)
  if (variant) {
    selectedOptions.value = { ...(variant.attributes ?? {}) }
  }
}

function onVariantChange(event) {
  selectVariant(event.target.value)
}

async function addToCart() {
  addError.value = ''
  added.value = false
  adding.value = true
  try {
    await store.addToCart(product.value.slug, quantity.value, selectedSku.value)
    added.value = true
  } catch (err) {
    addError.value = err.message || 'This product could not be added to the cart.'
  } finally {
    adding.value = false
  }
}
</script>

<template>
  <p v-if="loading" class="empty-state">Loading product…</p>

  <div v-else-if="unavailable" class="empty-state">This product is not available.</div>

  <p v-else-if="error" class="error">{{ error }}</p>

  <article v-else-if="product" class="product-detail">
    <div class="product-detail-media">
      <ProductMedia
        v-if="images.length"
        class="product-detail-image"
        :image="images[activeImage]"
        :name="product.name"
        :lazy="false"
      />
      <ProductMedia v-else class="product-detail-image" :name="product.name" />

      <div v-if="images.length > 1" class="product-detail-thumbs">
        <button
          v-for="(image, index) in images"
          :key="image.id"
          type="button"
          class="product-detail-thumb"
          :class="{ 'is-active': index === activeImage }"
          @click="activeImage = index"
        >
          <ProductMedia :image="image" :name="product.name" />
        </button>
      </div>
    </div>

    <div class="product-detail-info">
      <h1>{{ product.name }}</h1>

      <p v-if="product.brand" class="product-detail-meta">
        Brand:
        <RouterLink :to="`/brands/${product.brand.slug}/`">{{ product.brand.name }}</RouterLink>
      </p>
      <p v-if="product.category" class="product-detail-meta">
        <RouterLink :to="`/category/${product.category.slug}/`">{{ product.category.name }}</RouterLink>
      </p>

      <div class="product-detail-price">
        <span class="price price-lg">{{ displayPrice }}</span>
        <span v-if="displayComparePrice" class="price-was">{{ displayComparePrice }}</span>
      </div>
      <p v-if="!priceAvailable" class="error">
        The price is not available in the selected currency.
      </p>

      <p v-if="displaySku" class="product-detail-meta">SKU: <strong>{{ displaySku }}</strong></p>

      <p class="product-detail-meta product-detail-availability">
        Availability:
        <span v-if="inStock" class="stock-dot stock-in"></span>
        <span v-else class="stock-dot stock-out"></span>
        <strong v-if="inStock">In stock</strong>
        <strong v-else>Out of stock</strong>
        <span v-if="inStock && availableQuantity"> — only {{ availableQuantity }} left</span>
      </p>

      <div v-for="option in options" :key="option.slug" class="product-detail-option">
        <span class="product-option-label">{{ option.name }}</span>
        <div class="product-option-values">
          <template v-for="value in option.values" :key="value.value">
            <button
              v-if="hasVariants"
              type="button"
              :class="valueClasses(option, value)"
              :style="value.swatch ? { background: value.swatch } : undefined"
              :disabled="!value.available"
              :title="value.label"
              :aria-label="value.label"
              @click="selectOption(option, value.value)"
            >
              <span v-if="!value.swatch">{{ value.label }}</span>
            </button>
            <span
              v-else
              :class="valueClasses(option, value)"
              :style="value.swatch ? { background: value.swatch } : undefined"
              :title="value.label"
            >
              <span v-if="!value.swatch">{{ value.label }}</span>
            </span>
          </template>
        </div>
      </div>

      <div v-if="hasVariants" class="form-field">
        <label for="variant-select">Variants</label>
        <select
          id="variant-select"
          :value="selectedSku"
          @change="onVariantChange"
        >
          <option v-for="variant in variants" :key="variant.sku" :value="variant.sku">
            {{ variant.sku }} — {{ variant.price }}
          </option>
        </select>
      </div>

      <p v-if="combinationError" class="error">{{ combinationError }}</p>

      <div class="form-field">
        <label for="product-qty">Quantity</label>
        <input id="product-qty" v-model.number="quantity" type="number" min="1" />
      </div>

      <button type="button" class="btn" :disabled="!canAddToCart" @click="addToCart">
        {{ adding ? 'Adding…' : 'Add to cart' }}
      </button>

      <p v-if="addError" class="error">{{ addError }}</p>
      <p v-if="added" class="product-detail-added">Added to cart.</p>
      <RouterLink v-if="added" to="/cart/">View cart</RouterLink>
    </div>

    <section v-if="product.description" class="product-detail-description">
      <h2>Description</h2>
      <div class="prose">{{ product.description }}</div>
    </section>
  </article>
</template>
