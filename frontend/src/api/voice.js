import api from './index'

/**
 * Voice API module — STT (speech-to-text) and TTS (text-to-speech).
 */

const BASE = '/voice'

/**
 * Convert speech audio to text.
 * Uses raw fetch (not Axios) because Axios's default application/json
 * Content-Type interferes with multipart/form-data file upload.
 *
 * @param {File|Blob} audioFile - The audio file to transcribe
 * @returns {Promise<{text: string, filename: string}>}
 */
export async function speechToText(audioFile) {
  const token = localStorage.getItem('accessToken')
  const formData = new FormData()
  formData.append('file', audioFile)

  const response = await fetch(`/api/v1/voice/speech-to-text`, {
    method: 'POST',
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    body: formData,
  })

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}))
    const error = new Error(
      errorData.detail || errorData.message || '语音识别失败'
    )
    error.status = response.status
    throw error
  }

  return response.json()
}

/**
 * Convert text to speech (returns an audio Blob).
 * Uses raw fetch to get binary response, bypassing Axios JSON interceptor.
 *
 * @param {string} text - The text to convert to speech
 * @param {object} [options] - { voice?: string, rate?: string }
 * @returns {Promise<Blob>} Audio blob (MP3)
 */
export async function textToSpeech(text, options = {}) {
  const token = localStorage.getItem('accessToken')

  const body = { text }
  if (options.voice) body.voice = options.voice
  if (options.rate) body.rate = options.rate

  const response = await fetch(`/api/v1${BASE}/text-to-speech`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': token ? `Bearer ${token}` : '',
    },
    body: JSON.stringify(body),
  })

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}))
    const error = new Error(
      errorData.detail || errorData.message || '语音合成失败'
    )
    error.status = response.status
    throw error
  }

  return response.blob()
}
