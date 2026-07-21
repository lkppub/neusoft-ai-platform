import { ref } from 'vue'
import { textToSpeech } from '@/api/voice'
import { ElMessage } from 'element-plus'

/**
 * Strip common Markdown/HTML syntax so TTS reads clean text.
 * Covers: headings, bold/italic, code, links, images, lists, blockquotes, HR, strikethrough.
 */
function stripMarkdown(text) {
  let clean = text
  // HTML tags (e.g. <br>, <p>)
  clean = clean.replace(/<[^>]+>/g, '')
  // Images ![alt](url)
  clean = clean.replace(/!\[.*?\]\(.*?\)/g, '')
  // Links [text](url)
  clean = clean.replace(/\[([^\]]*)\]\(.*?\)/g, '$1')
  // Bold **text** or __text__
  clean = clean.replace(/\*\*([^*]+)\*\*/g, '$1')
  clean = clean.replace(/__([^_]+)__/g, '$1')
  // Italic *text* or _text_
  clean = clean.replace(/\*([^*]+)\*/g, '$1')
  clean = clean.replace(/_([^_]+)_/g, '$1')
  // Strikethrough ~~text~~
  clean = clean.replace(/~~([^~]+)~~/g, '$1')
  // Inline code `text`
  clean = clean.replace(/`([^`]+)`/g, '$1')
  // Code blocks ```...```
  clean = clean.replace(/```[\s\S]*?```/g, '')
  // Headings # ## ### etc
  clean = clean.replace(/^#{1,6}\s+/gm, '')
  // Horizontal rules
  clean = clean.replace(/^[-*_]{3,}\s*$/gm, '')
  // Blockquotes
  clean = clean.replace(/^>\s+/gm, '')
  // Unordered list markers
  clean = clean.replace(/^[-*+]\s+/gm, '')
  // Ordered list markers
  clean = clean.replace(/^\d+\.\s+/gm, '')
  // Collapse multiple newlines
  clean = clean.replace(/\n{3,}/g, '\n\n')
  // Collapse multiple spaces
  clean = clean.replace(/ {2,}/g, ' ')
  return clean.trim()
}

/**
 * Composable for TTS audio playback with pause/resume support.
 *
 * Usage:
 *   const { play, pause, resume, stop, isPlaying, isPaused } = useTTS()
 *   await play('你好，这是语音合成测试。')
 */
export function useTTS() {
  const isPlaying = ref(false)   // audio is actively playing
  const isPaused = ref(false)    // audio is paused mid-stream
  const error = ref(null)
  let audio = null
  let _currentUrl = null

  /** Play TTS audio for the given text. Markdown is auto-stripped. */
  async function play(text, options = {}) {
    stop()

    isPlaying.value = true
    isPaused.value = false
    error.value = null

    // Strip markdown before sending to TTS
    const cleanText = stripMarkdown(text)

    try {
      const blob = await textToSpeech(cleanText, options)
      _currentUrl = URL.createObjectURL(blob)
      audio = new Audio(_currentUrl)

      audio.onended = () => {
        isPlaying.value = false
        isPaused.value = false
        URL.revokeObjectURL(_currentUrl)
        _currentUrl = null
        audio = null
      }

      audio.onerror = () => {
        isPlaying.value = false
        isPaused.value = false
        URL.revokeObjectURL(_currentUrl)
        _currentUrl = null
        audio = null
        ElMessage.warning('音频播放失败')
      }

      await audio.play()
    } catch (e) {
      isPlaying.value = false
      isPaused.value = false
      error.value = e.message || '语音合成失败'
      ElMessage.warning(error.value)
    }
  }

  /** Pause current playback (resumable). */
  function pause() {
    if (audio && !audio.paused) {
      audio.pause()
      isPaused.value = true
    }
  }

  /** Resume paused playback. */
  function resume() {
    if (audio && audio.paused) {
      audio.play()
      isPaused.value = false
    }
  }

  /** Stop current playback and reset. */
  function stop() {
    if (audio) {
      audio.pause()
      if (_currentUrl) {
        URL.revokeObjectURL(_currentUrl)
        _currentUrl = null
      }
      audio = null
    }
    isPlaying.value = false
    isPaused.value = false
  }

  return { play, pause, resume, stop, isPlaying, isPaused, error }
}
