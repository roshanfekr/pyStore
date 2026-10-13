<script setup>
import { computed, ref } from 'vue'

import { getCsrfToken } from '@/api/client'
import { useStorefrontStore } from '@/stores/storefront'

const store = useStorefrontStore()

const languageForm = ref(null)
const csrfInput = ref(null)
const currencyForm = ref(null)
const currencyCsrfInput = ref(null)

const branding = computed(() => store.branding)
const menu = computed(() => store.menu)
const user = computed(() => store.user)
const counts = computed(() => store.counts)
const languages = computed(() => store.languages)
const currencies = computed(() => store.currencies)

async function logout() {
  await store.logout()
  // Full navigation back to the server-rendered home page.
  window.location.href = '/'
}

function switchLanguage() {
  // Refresh the CSRF token from the cookie at submit time, then post to the
  // Django set-language view (sets the locale cookie) and reload.
  if (csrfInput.value) {
    csrfInput.value.value = getCsrfToken()
  }
  languageForm.value?.submit()
}

function switchCurrency() {
  if (currencyCsrfInput.value) {
    currencyCsrfInput.value.value = getCsrfToken()
  }
  currencyForm.value?.submit()
}
</script>

<template>
  <header class="site-header">
    <div class="header-inner">
      <a class="logo" href="/"><span class="logo-mark">py</span>{{ branding.site_name }}</a>

      <nav class="main-nav">
        <a v-for="item in menu" :key="item.id" :href="item.url || '/'">{{ item.title }}</a>
      </nav>

      <!-- Server-rendered search results page. -->
      <form class="search-form" method="get" action="/search/">
        <input type="text" name="q" placeholder="Search products…" aria-label="Search" />
        <button type="submit">Search</button>
      </form>

      <div class="header-actions">
        <RouterLink to="/wishlist/">Wishlist ({{ counts.wishlist }})</RouterLink>
        <RouterLink to="/compare/">Compare ({{ counts.compare }})</RouterLink>
        <RouterLink to="/cart/">Cart ({{ store.cartCount }})</RouterLink>
        <a v-if="user.is_staff" href="/admin/">Admin</a>
        <template v-if="user.is_authenticated">
          <RouterLink to="/account/">Account</RouterLink>
          <a href="#" @click.prevent="logout">Logout</a>
        </template>
        <template v-else>
          <RouterLink to="/login/">Login</RouterLink>
          <RouterLink to="/register/">Register</RouterLink>
        </template>
      </div>

      <form
        v-if="languages.length > 1"
        ref="languageForm"
        class="lang-form"
        method="post"
        action="/i18n/setlang/"
      >
        <input ref="csrfInput" type="hidden" name="csrfmiddlewaretoken" value="" />
        <input type="hidden" name="next" :value="$route.fullPath" />
        <select :value="store.activeLanguage.code" name="language" @change="switchLanguage">
          <option v-for="lang in languages" :key="lang.code" :value="lang.code">
            {{ lang.flag }} {{ lang.name }}
          </option>
        </select>
      </form>

      <form
        v-if="currencies.length > 1"
        ref="currencyForm"
        class="lang-form"
        method="post"
        action="/i18n/setcurrency/"
      >
        <input ref="currencyCsrfInput" type="hidden" name="csrfmiddlewaretoken" value="" />
        <input type="hidden" name="next" :value="$route.fullPath" />
        <select :value="store.activeCurrency.code" name="currency" @change="switchCurrency">
          <option v-for="cur in currencies" :key="cur.code" :value="cur.code">
            {{ cur.symbol }} {{ cur.name }}
          </option>
        </select>
      </form>
    </div>
  </header>
</template>
