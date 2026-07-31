import { createPinia } from 'pinia'
import { createApp } from 'vue'

import App from './App.vue'
import router from './router'
import './assets/main.css'
import { useCartStore } from './features/cart/store'
import { useAuthStore } from './stores/auth'

const app = createApp(App)
const pinia = createPinia()

app.use(pinia)
const authStore = useAuthStore(pinia)
const cartStore = useCartStore(pinia)
authStore.bindHttpClient()
await authStore.restoreSession()
window.addEventListener('auth:authenticated', () => void cartStore.mergeGuestCart())
if (authStore.isAuthenticated) void cartStore.mergeGuestCart()

app.use(router)
app.mount('#app')
