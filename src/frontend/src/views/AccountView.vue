<script setup>
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

import { api } from '@/api/client'
import { useStorefrontStore } from '@/stores/storefront'

const store = useStorefrontStore()
const router = useRouter()

const profile = ref(null)
const orders = ref([])

onMounted(async () => {
  if (!store.user.is_authenticated) {
    router.push('/login/')
    return
  }
  profile.value = await api('/customers/me')
  const data = await api('/orders')
  orders.value = data.results ?? data
})
</script>

<template>
  <div class="page-title">
    <h2>Account</h2>
  </div>
  <div v-if="profile" class="card">
    <div>{{ profile.email }}</div>
    <div>{{ profile.first_name }} {{ profile.last_name }}</div>
  </div>

  <h3>Recent orders</h3>
  <div v-if="!orders.length" class="empty-state">No orders yet.</div>
  <table v-else>
    <thead>
      <tr><th>Number</th><th>Status</th><th>Total</th><th></th></tr>
    </thead>
    <tbody>
      <tr v-for="order in orders" :key="order.id">
        <td>{{ order.number }}</td>
        <td>{{ order.status }}</td>
        <td>{{ order.total }}</td>
        <td><RouterLink :to="`/orders/${order.number}/`">View</RouterLink></td>
      </tr>
    </tbody>
  </table>
</template>
