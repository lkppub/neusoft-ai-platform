<template>
  <div class="chat-input-area">
    <el-input
      v-model="localValue"
      type="textarea"
      :rows="rows"
      :maxlength="maxLength"
      :show-word-limit="showWordLimit"
      :placeholder="placeholder"
      :disabled="disabled"
      @keydown.enter.exact.prevent="handleSend"
      resize="none"
    />
    <div class="input-actions">
      <div class="input-left">
        <slot name="left-actions" />
        <span class="input-hint">{{ hint }}</span>
      </div>
      <el-button
        type="primary"
        :loading="loading"
        :disabled="!localValue.trim() || disabled"
        @click="handleSend"
      >
        {{ loading ? '回复中...' : buttonText }}
      </el-button>
    </div>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'

const props = defineProps({
  modelValue: { type: String, default: '' },
  placeholder: { type: String, default: '输入您的问题... (Enter 发送，Shift+Enter 换行)' },
  buttonText: { type: String, default: '发送' },
  hint: { type: String, default: 'Enter 发送 / Shift+Enter 换行' },
  rows: { type: Number, default: 3 },
  maxLength: { type: Number, default: 4000 },
  showWordLimit: { type: Boolean, default: true },
  loading: { type: Boolean, default: false },
  disabled: { type: Boolean, default: false },
})

const emit = defineEmits(['update:modelValue', 'send'])

const localValue = ref(props.modelValue)
watch(() => props.modelValue, (v) => { localValue.value = v })
watch(localValue, (v) => { emit('update:modelValue', v) })

function handleSend() {
  const trimmed = localValue.value.trim()
  if (!trimmed || props.disabled || props.loading) return
  emit('send', trimmed)
  localValue.value = ''
}
</script>

<style scoped>
.chat-input-area {
  padding: 16px 20px;
  border-top: 1px solid #e5e7eb;
  background: #fff;
}
.chat-input-area :deep(.el-textarea__inner) {
  border-radius: 8px;
  font-size: 14px;
  line-height: 1.6;
}
.input-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 8px;
}
.input-left { display: flex; align-items: center; gap: 12px; }
.input-hint { font-size: 12px; color: #c0c4cc; }
</style>
