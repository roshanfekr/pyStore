import { createRouter, createWebHistory } from 'vue-router'

// Hybrid storefront: content pages (home, category, product, search, blog, CMS)
// are server-rendered by Django and are reached via normal full-page links. The
// SPA only owns the interactive routes below.
const routes = [
  { path: '/cart/', name: 'cart', component: () => import('@/views/CartView.vue') },
  { path: '/checkout/', name: 'checkout', component: () => import('@/views/CheckoutView.vue') },
  { path: '/login/', name: 'login', component: () => import('@/views/LoginView.vue') },
  { path: '/register/', name: 'register', component: () => import('@/views/RegisterView.vue') },
  { path: '/account/', name: 'account', component: () => import('@/views/AccountView.vue') },
  { path: '/wishlist/', name: 'wishlist', component: () => import('@/views/WishlistView.vue') },
  { path: '/compare/', name: 'compare', component: () => import('@/views/CompareView.vue') },
  { path: '/orders/:number/', name: 'order', component: () => import('@/views/OrderView.vue') },
  { path: '/:pathMatch(.*)*', name: 'not-found', component: () => import('@/views/NotFoundView.vue') },
]

export default createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior: () => ({ top: 0 }),
})
