<template>
  <div class="voice-input">
    <el-button
      :type="isRecording ? 'danger' : 'default'"
      :icon="isRecording ? Microphone : Microphone"
      circle
      :loading="processing"
      :disabled="disabled"
      @click="toggleRecording"
      :class="{ 'is-recording': isRecording }"
      size="large"
    />
    <span v-if="isRecording" class="recording-hint">录音中...点击停止</span>
    <span v-else class="idle-hint">语音输入</span>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Microphone } from '@element-plus/icons-vue'
import { speechToText } from '@/api/voice'

const props = defineProps({
  disabled: { type: Boolean, default: false },
})

const emit = defineEmits(['transcribed'])

const isRecording = ref(false)
const processing = ref(false)
let mediaRecorder = null
let audioChunks = []

// ── WAV encoding helpers ──

function writeString(view, offset, str) {
  for (let i = 0; i < str.length; i++) {
    view.setUint8(offset + i, str.charCodeAt(i))
  }
}

/** Simple linear resample (uses nearest-neighbour for speed). */
function resample(samples, fromRate, toRate) {
  const ratio = fromRate / toRate
  const newLen = Math.floor(samples.length / ratio)
  const result = new Float32Array(newLen)
  for (let i = 0; i < newLen; i++) {
    result[i] = samples[Math.floor(i * ratio)]
  }
  return result
}

/** Convert a Float32Array of samples to a 16-bit PCM WAV Blob. */
function audioBufferToWav(samples, sampleRate) {
  const dataLength = samples.length * 2          // 16-bit = 2 bytes/sample
  const buf = new ArrayBuffer(44 + dataLength)
  const view = new DataView(buf)

  // RIFF header
  writeString(view, 0, 'RIFF')
  view.setUint32(4, 36 + dataLength, true)
  writeString(view, 8, 'WAVE')

  // fmt sub-chunk
  writeString(view, 12, 'fmt ')
  view.setUint32(16, 16, true)                  // sub-chunk size = 16 (PCM)
  view.setUint16(20, 1, true)                   // format = 1 (PCM)
  view.setUint16(22, 1, true)                   // mono
  view.setUint32(24, sampleRate, true)
  view.setUint32(28, sampleRate * 2, true)      // byte rate
  view.setUint16(32, 2, true)                   // block align
  view.setUint16(34, 16, true)                  // bits per sample

  // data sub-chunk
  writeString(view, 36, 'data')
  view.setUint32(40, dataLength, true)

  // Write samples as signed 16-bit PCM
  let offset = 44
  for (let i = 0; i < samples.length; i++) {
    const s = Math.max(-1, Math.min(1, samples[i]))
    view.setInt16(offset, s < 0 ? s * 0x8000 : s * 0x7FFF, true)
    offset += 2
  }

  return new Blob([buf], { type: 'audio/wav' })
}

// ── Recording logic ──

async function toggleRecording() {
  if (isRecording.value) {
    stopRecording()
    return
  }
  await startRecording()
}

async function startRecording() {
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
    mediaRecorder = new MediaRecorder(stream, {
      mimeType: MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
        ? 'audio/webm;codecs=opus'
        : 'audio/webm',
    })
    audioChunks = []

    mediaRecorder.ondataavailable = (e) => { audioChunks.push(e.data) }
    mediaRecorder.onstop = async () => {
      stream.getTracks().forEach(t => t.stop())
      processing.value = true
      try {
        const webmBlob = new Blob(audioChunks, { type: 'audio/webm' })

        // Try to decode & convert to WAV in the browser (avoids ffmpeg).
        // If that fails, send the raw WebM — the backend has ffmpeg.
        let file
        try {
          let audioCtx
          try {
            audioCtx = new AudioContext({ sampleRate: 16000 })
          } catch {
            audioCtx = new AudioContext()
          }
          const arrayBuffer = await webmBlob.arrayBuffer()
          const audioBuffer = await audioCtx.decodeAudioData(arrayBuffer)

          let samples
          if (audioBuffer.sampleRate !== 16000) {
            samples = resample(audioBuffer.getChannelData(0), audioBuffer.sampleRate, 16000)
          } else {
            samples = audioBuffer.getChannelData(0)
          }
          await audioCtx.close()

          const wavBlob = audioBufferToWav(samples, 16000)
          file = new File([wavBlob], 'recording.wav', { type: 'audio/wav' })
        } catch (_decodeErr) {
          // Browser can't decode this WebM → send raw WebM (backend has ffmpeg)
          console.warn('[VoiceInput] decodeAudioData failed, sending raw WebM:', _decodeErr)
          file = new File([webmBlob], 'recording.webm', { type: 'audio/webm' })
        }

        const result = await speechToText(file)
        const text = result?.text || ''
        if (text) emit('transcribed', text)
        else ElMessage.warning('未识别到语音内容')
      } catch (e) {
        console.error('[VoiceInput] 语音识别失败:', e)
        ElMessage.warning('语音识别失败，请重试')
      } finally {
        processing.value = false
      }
    }

    mediaRecorder.start()
    isRecording.value = true
  } catch {
    ElMessage.warning('无法访问麦克风，请检查浏览器权限')
  }
}

function stopRecording() {
  if (mediaRecorder && mediaRecorder.state !== 'inactive') {
    mediaRecorder.stop()
  }
  isRecording.value = false
}
</script>

<style scoped>
.voice-input { display: flex; align-items: center; gap: 8px; }
.is-recording { animation: pulse 1.5s infinite; }
@keyframes pulse {
  0%, 100% { box-shadow: 0 0 0 0 rgba(245, 108, 108, 0.4); }
  50% { box-shadow: 0 0 0 8px rgba(245, 108, 108, 0); }
}
.recording-hint { color: #f56c6c; font-size: 13px; }
.idle-hint { color: #909399; font-size: 13px; }
</style>
