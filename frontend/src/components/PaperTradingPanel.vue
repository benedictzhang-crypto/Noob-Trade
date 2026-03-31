<script setup>
defineProps({
  paperTrade: {
    type: Object,
    required: true
  }
})
</script>

<template>
  <div class="inner-card paper-card">
    <div class="section-header">Paper Trading Panel</div>
    <div class="paper-grid">
      <div class="paper-item">
        <span>Entry</span>
        <strong>{{ paperTrade.entry }}</strong>
      </div>
      <div class="paper-item">
        <span>Stop</span>
        <strong>{{ paperTrade.stopLoss }}</strong>
      </div>
      <div class="paper-item">
        <span>Target</span>
        <strong>{{ paperTrade.takeProfit }}</strong>
      </div>
      <div class="paper-item">
        <span>Size</span>
        <strong>{{ paperTrade.positionSize }}</strong>
      </div>
    </div>
    <div class="confidence-row">
      Risk / Reward: <strong>{{ paperTrade.riskReward }}</strong>
    </div>
  </div>
</template>
