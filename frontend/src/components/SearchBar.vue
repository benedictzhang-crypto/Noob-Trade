<script setup>
const props = defineProps({
  modelValue: {
    type: String,
    required: true
  },
  placeholder: {
    type: String,
    default: 'Enter Ticker (e.g. AAPL)'
  },
  loadingLabel: {
    type: String,
    default: 'Loading stock data for'
  },
  popularSymbols: {
    type: Array,
    default: () => ['AAPL', 'TSLA', 'NVDA', 'MSFT']
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
        :value="props.modelValue"
        class="symbol-input"
        type="text"
        :placeholder="props.placeholder"
        @input="updateValue"
        @keyup.enter="$emit('search')"
      />
      <button class="search-button" :disabled="props.isLoading" @click="$emit('search')">
        {{ props.isLoading ? 'Loading...' : 'Search' }}
      </button>
    </div>

    <p v-if="props.errorMessage" class="status-message error-message">
      {{ props.errorMessage }}
    </p>
    <p v-else-if="props.isLoading" class="status-message loading-message">
      {{ props.loadingLabel }} {{ props.modelValue || 'selected symbol' }}...
    </p>

    <p class="popular-row">
      Popular:
      <button
        v-for="symbol in props.popularSymbols"
        :key="symbol"
        class="popular-link"
        @click="selectPopular(symbol)"
      >
        {{ symbol }}
      </button>
    </p>
  </div>
</template>
