<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'

import { useStorefrontStore } from '@/stores/storefront'

const store = useStorefrontStore()
const router = useRouter()

const email = ref('')
const password = ref('')
const error = ref('')

async function submit() {
  error.value = ''
  try {
    await store.register(email.value, password.value)
    router.push('/account/')
  } catch (err) {
    error.value = err.message
  }
}
</script>

<template>
  <div class="page-title">
    <h2>Register</h2>
  </div>
  <form class="card" @submit.prevent="submit">
    <div class="form-field">
      <label for="email">Email</label>
      <input id="email" v-model="email" type="email" required />
    </div>
    <div class="form-field">
      <label for="password">Password</label>
      <input id="password" v-model="password" type="password" minlength="8" required />
    </div>
    <p v-if="error" class="error">{{ error }}</p>
    <button type="submit">Create account</button>
  </form>
  <p>Already registered? <RouterLink to="/login/">Login</RouterLink></p>
</template>
