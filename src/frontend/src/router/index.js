import { createRouter, createWebHistory } from 'vue-router'

// Hybrid storefront: the SPA owns the interactive routes below and, as content
// routes are migrated, the storefront content pages it has taken over. Routes
// that have not been migrated yet stay server-rendered by Django and are
// reached via normal full-page links.
const routes = [
  { path: '/cart/', name: 'cart', component: () => import('@/views/CartView.vue') },
  { path: '/checkout/', name: 'checkout', component: () => import('@/views/CheckoutView.vue') },
  { path: '/login/', name: 'login', component: () => import('@/views/LoginView.vue') },
  { path: '/register/', name: 'register', component: () => import('@/views/RegisterView.vue') },
  { path: '/account/', name: 'account', component: () => import('@/views/AccountView.vue') },
  { path: '/wishlist/', name: 'wishlist', component: () => import('@/views/WishlistView.vue') },
  { path: '/compare/', name: 'compare', component: () => import('@/views/CompareView.vue') },
  { path: '/orders/:number/', name: 'order', component: () => import('@/views/OrderView.vue') },
  { path: '/brands/', name: 'brands', component: () => import('@/views/BrandListView.vue') },
  { path: '/brands/:slug/', name: 'brand', component: () => import('@/views/BrandDetailView.vue') },
  { path: '/category/:slug/', name: 'category', component: () => import('@/views/CategoryView.vue') },
  { path: '/:pathMatch(.*)*', name: 'not-found', component: () => import('@/views/NotFoundView.vue') },
]

export default createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior: () => ({ top: 0 }),
})
