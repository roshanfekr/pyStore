import { defineStore } from 'pinia'

import { api, setStoreSlug, setToken } from '@/api/client'

// Global storefront state: theme/branding/menu bootstrap data, the cart and the
// current customer. Loaded once by App.vue on startup.
export const useStorefrontStore = defineStore('storefront', {
  state: () => ({
    bootstrap: null,
    cart: null,
    ready: false,
  }),

  getters: {
    store: (state) => state.bootstrap?.store ?? { slug: '', name: '' },
    branding: (state) => state.bootstrap?.branding ?? { site_name: 'pyStore' },
    menu: (state) => state.bootstrap?.menu ?? [],
    widgets: (state) => state.bootstrap?.widgets ?? [],
    theme: (state) => state.bootstrap?.theme ?? { name: 'default', config: {}, css: [] },
    languages: (state) => state.bootstrap?.languages ?? [],
    activeLanguage: (state) => state.bootstrap?.active_language ?? { code: 'en', direction: 'ltr' },
    currencies: (state) => state.bootstrap?.currencies ?? [],
    activeCurrency: (state) => state.bootstrap?.active_currency ?? { code: 'IRT', symbol: '' },
    user: (state) => state.bootstrap?.user ?? { is_authenticated: false },
    counts: (state) => state.bootstrap?.counts ?? { wishlist: 0, compare: 0 },
    cartLines: (state) => state.cart?.lines ?? [],
    cartCount: (state) => (state.cart?.lines ?? []).reduce((sum, line) => sum + line.quantity, 0),
  },

  actions: {
    async loadBootstrap() {
      this.bootstrap = await api('/storefront/bootstrap')
      setStoreSlug(this.store.slug)
    },
    async refreshCart() {
      try {
        this.cart = await api('/cart')
      } catch {
        this.cart = null
      }
    },
    async init() {
      await this.loadBootstrap()
      await this.refreshCart()
      this.ready = true
    },
    async addToCart(product, quantity = 1, variant = '') {
      this.cart = await api('/cart/items', {
        method: 'POST',
        body: { product, quantity, variant },
      })
    },
    async updateItem(itemId, quantity) {
      this.cart = await api(`/cart/items/${itemId}`, {
        method: 'PATCH',
        body: { quantity },
      })
    },
    async removeItem(itemId) {
      await api(`/cart/items/${itemId}`, { method: 'DELETE' })
      await this.refreshCart()
    },
    async applyCoupon(code) {
      this.cart = await api('/cart/coupon', { method: 'POST', body: { code } })
    },
    async login(email, password) {
      const data = await api('/auth/login', { method: 'POST', body: { email, password } })
      setToken(data.token)
      await this.init()
    },
    async register(email, password) {
      await api('/auth/register', { method: 'POST', body: { email, password } })
      await this.login(email, password)
    },
    async logout() {
      try {
        await api('/auth/logout', { method: 'POST' })
      } catch {
        /* token may already be revoked */
      }
      setToken(null)
      await this.init()
    },
  },
})
