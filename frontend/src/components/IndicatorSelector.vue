<script setup>
defineProps({
  indicators: {
    type: Array,
    required: true
  },
  isLoading: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['toggle-indicator', 'run-analysis'])

function handleToggle(event, indicatorName) {
  emit('toggle-indicator', indicatorName)
  requestAnimationFrame(() => {
    event.currentTarget?.blur?.()
  })
}
</script>

<template>
  <div>
    <div class="inner-card">
      <div class="section-header">Select Indicators</div>
      <div class="indicator-list">
        <button
          v-for="indicator in indicators"
          :key="indicator.name"
          type="button"
          class="indicator-row"
          :class="{ active: indicator.active }"
          @mousedown.prevent
          @pointerdown.prevent
          @click="handleToggle($event, indicator.name)"
        >
          <span class="check-box">{{ indicator.active ? '✓' : '' }}</span>
          <span class="indicator-name">{{ indicator.name }}</span>
        </button>
      </div>
    </div>
    <button class="analysis-button" :disabled="isLoading" @click="emit('run-analysis')">
      {{ isLoading ? 'Generating...' : 'Generate' }}
    </button>
  </div>
</template>
