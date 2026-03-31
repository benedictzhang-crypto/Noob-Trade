<script setup>
defineProps({
  modelValue: {
    type: String,
    required: true
  },
  isLoading: {
    type: Boolean,
    default: false
  },
  errorMessage: {
    type: String,
    default: ''
  }
})

const emit = defineEmits(['update:modelValue', 'search', 'select-popular'])

function updateValue(event) {
  emit('update:modelValue', event.target.value)
}

function selectPopular(symbol) {
  emit('select-popular', symbol)
}
</script>

<template>
  <div>
    <div class="search-form">
      <input
        :value="modelValue"
        class="symbol-input"
        type="text"
        placeholder="Enter Ticker (e.g. AAPL)"
        @input="updateValue"
        @keyup.enter="$emit('search')"
      />
      <button class="search-button" :disabled="isLoading" @click="$emit('search')">
        {{ isLoading ? 'Loading...' : 'Search' }}
      </button>
    </div>

    <p v-if="errorMessage" class="status-message error-message">
      {{ errorMessage }}
    </p>
    <p v-else-if="isLoading" class="status-message loading-message">
      Loading stock data for {{ modelValue || 'selected symbol' }}...
    </p>

    <p class="popular-row">
      Popular:
      <button class="popular-link" @click="selectPopular('AAPL')">AAPL</button>
      <button class="popular-link" @click="selectPopular('TSLA')">TSLA</button>
      <button class="popular-link" @click="selectPopular('NVDA')">NVDA</button>
      <button class="popular-link" @click="selectPopular('SPY')">SPY</button>
    </p>
  </div>
</template>
