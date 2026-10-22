<script setup>
import { computed, ref } from 'vue'

import { useStorefrontStore } from '@/stores/storefront'

const store = useStorefrontStore()
const coupon = ref('')

const cart = computed(() => store.cart)
const lines = computed(() => store.cartLines)

async function setQuantity(line, quantity) {
  if (quantity < 1) {
    await store.removeItem(line.item_id)
    return
  }
  await store.updateItem(line.item_id, quantity)
}

async function applyCoupon() {
  if (coupon.value.trim()) {
    await store.applyCoupon(coupon.value.trim())
  }
}
</script>

<template>
  <div class="page-title">
    <h2>Cart</h2>
  </div>

  <div v-if="!lines.length" class="empty-state">Your cart is empty.</div>

  <template v-else>
    <table>
      <thead>
        <tr>
          <th>Product</th>
          <th>Unit price</th>
          <th>Quantity</th>
          <th>Total</th>
          <th></th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="line in lines" :key="line.item_id">
          <td>{{ line.product_name }}</td>
          <td>{{ line.unit_price }}</td>
          <td>
            <input
              type="number"
              min="1"
              :value="line.quantity"
              style="width: 4rem"
              @change="setQuantity(line, Number($event.target.value))"
            />
          </td>
          <td>{{ line.line_total }}</td>
          <td><button class="btn-secondary" @click="store.removeItem(line.item_id)">Remove</button></td>
        </tr>
      </tbody>
    </table>

    <div class="card">
      <div v-if="cart.currency">Currency: {{ cart.currency }}</div>
      <div>Subtotal: {{ cart.subtotal }}</div>
      <div v-if="cart.coupon_code">Coupon {{ cart.coupon_code }}: -{{ cart.discount_amount }}</div>
      <div><strong>Total: {{ cart.total }}</strong></div>
    </div>

    <div class="card">
      <form class="search-form" @submit.prevent="applyCoupon">
        <input v-model="coupon" type="text" placeholder="Coupon code" />
        <button type="submit">Apply</button>
      </form>
    </div>

    <RouterLink class="btn" to="/checkout/">Checkout</RouterLink>
  </template>
</template>
