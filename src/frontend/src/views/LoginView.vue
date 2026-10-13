<script setup>
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { useStorefrontStore } from '@/stores/storefront'

const store = useStorefrontStore()
const router = useRouter()
const route = useRoute()

const email = ref('')
const password = ref('')
const error = ref('')

async function submit() {
  error.value = ''
  try {
    await store.login(email.value, password.value)
    router.push(route.query.next || '/account/')
  } catch (err) {
    error.value = err.message
  }
}
</script>

<template>
  <div class="page-title">
    <h2>Login</h2>
  </div>
  <form class="card" @submit.prevent="submit">
    <div class="form-field">
      <label for="email">Email</label>
      <input id="email" v-model="email" type="email" required />
    </div>
    <div class="form-field">
      <label for="password">Password</label>
      <input id="password" v-model="password" type="password" required />
    </div>
    <p v-if="error" class="error">{{ error }}</p>
    <button type="submit">Login</button>
  </form>
  <p>No account? <RouterLink to="/register/">Register</RouterLink></p>
</template>
