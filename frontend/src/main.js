import { createApp } from 'vue'
import App from './App.vue'
import './style.css'

createApp(App).mount('#app')

if (import.meta.env.DEV && 'serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.getRegistrations().then((registrations) => {
      registrations.forEach((registration) => {
        registration.unregister().catch(() => {})
      })
    })

    if ('caches' in window) {
      caches.keys().then((keys) => {
        keys
          .filter((key) => key.startsWith('noobtrade-'))
          .forEach((key) => caches.delete(key).catch(() => {}))
      })
    }
  })
} else if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/sw.js').catch((error) => {
      console.error('Service worker registration failed:', error)
    })
  })
}
