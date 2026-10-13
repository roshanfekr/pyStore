<script setup>
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

import { api } from '@/api/client'
import { useStorefrontStore } from '@/stores/storefront'

const store = useStorefrontStore()
const router = useRouter()

const methods = ref({ shipping_methods: [], payment_methods: [] })
const error = ref('')
const submitting = ref(false)
const form = ref({
  email: '',
  first_name: '',
  last_name: '',
  country: '',
  state: '',
  city: '',
  postal_code: '',
  address_line: '',
  phone: '',
  shipping_method_code: '',
  payment_method_code: '',
})

onMounted(async () => {
  methods.value = await api('/checkout/methods')
  form.value.shipping_method_code = methods.value.shipping_methods[0]?.code ?? ''
  form.value.payment_method_code = methods.value.payment_methods[0]?.code ?? ''
})

async function submit() {
  error.value = ''
  submitting.value = true
  const {
    email,
    shipping_method_code,
    payment_method_code,
    ...address
  } = form.value
  try {
    const data = await api('/checkout', {
      method: 'POST',
      body: {
        email,
        shipping_address: address,
        shipping_method_code,
        payment_method_code,
      },
    })
    await store.refreshCart()
    router.push({ name: 'order', params: { number: data.order_number } })
  } catch (err) {
    error.value = err.message
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <div class="page-title">
    <h2>Checkout</h2>
  </div>

  <form class="card" @submit.prevent="submit">
    <div class="form-field">
      <label for="email">Email</label>
      <input id="email" v-model="form.email" type="email" required />
    </div>
    <div class="form-field">
      <label for="first_name">First name</label>
      <input id="first_name" v-model="form.first_name" type="text" />
    </div>
    <div class="form-field">
      <label for="last_name">Last name</label>
      <input id="last_name" v-model="form.last_name" type="text" />
    </div>
    <div class="form-field">
      <label for="country">Country</label>
      <input id="country" v-model="form.country" type="text" required />
    </div>
    <div class="form-field">
      <label for="city">City</label>
      <input id="city" v-model="form.city" type="text" required />
    </div>
    <div class="form-field">
      <label for="address_line">Address</label>
      <input id="address_line" v-model="form.address_line" type="text" required />
    </div>
    <div class="form-field">
      <label for="postal_code">Postal code</label>
      <input id="postal_code" v-model="form.postal_code" type="text" />
    </div>
    <div class="form-field">
      <label for="shipping">Shipping method</label>
      <select id="shipping" v-model="form.shipping_method_code">
        <option v-for="m in methods.shipping_methods" :key="m.code" :value="m.code">
          {{ m.name }} ({{ m.flat_price }})
        </option>
      </select>
    </div>
    <div class="form-field">
      <label for="payment">Payment method</label>
      <select id="payment" v-model="form.payment_method_code">
        <option v-for="m in methods.payment_methods" :key="m.code" :value="m.code">
          {{ m.name }}
        </option>
      </select>
    </div>

    <p v-if="error" class="error">{{ error }}</p>
    <button type="submit" :disabled="submitting">Place order</button>
  </form>
</template>
