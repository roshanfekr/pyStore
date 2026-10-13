<script setup>
import { onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'

import { api } from '@/api/client'

const route = useRoute()
const order = ref(null)
const error = ref('')

async function load() {
  error.value = ''
  try {
    order.value = await api(`/orders/${route.params.number}`)
  } catch (err) {
    error.value = err.message
  }
}

onMounted(load)
watch(() => route.params.number, load)
</script>

<template>
  <p v-if="error" class="error">{{ error }}</p>
  <div v-if="order" class="card">
    <div class="page-title">
      <h2>Order {{ order.number }}</h2>
      <span class="count">{{ order.status }}</span>
    </div>
    <table>
      <thead>
        <tr><th>Product</th><th>Quantity</th><th>Total</th></tr>
      </thead>
      <tbody>
        <tr v-for="(item, index) in order.items" :key="index">
          <td>{{ item.product_name }}</td>
          <td>{{ item.quantity }}</td>
          <td>{{ item.line_total }}</td>
        </tr>
      </tbody>
    </table>
    <div style="margin-top: 1rem"><strong>Total: {{ order.total }} {{ order.currency }}</strong></div>
  </div>
</template>
