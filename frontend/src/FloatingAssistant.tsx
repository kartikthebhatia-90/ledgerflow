import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { AnimatePresence, motion } from 'motion/react'
import { ExternalLink, Mic, MicOff, Send, SlidersHorizontal, Square, Volume2, VolumeX, X } from 'lucide-react'
import type { AssistantProfile } from './types'

interface Props {
  assistantState: string
  target: string
  speech: string
  choices: string[]
  citations: Array<{ title: string; url: string }>
  running: boolean
  reducedMotion: boolean
  modelLabel: string
  executionStatus: string
  executedActions: string[]
  processingProgress: number
  processingStage: string
  profile: AssistantProfile | null
  onProfileChange: (updates: Partial<AssistantProfile>) => Promise<void>
  onSubmit: (message: string) => void
  onChoice: (choice: string) => void
  onStop: () => void
}

type RecognitionLike = {
  lang: string
  continuous: boolean
  interimResults: boolean
  maxAlternatives: number
  start: () => void
  stop: () => void
  abort: () => void
  onresult: ((event: any) => void) | null
  onend: (() => void) | null
  onerror: ((event: any) => void) | null
  onspeechstart: (() => void) | null
}

function useViewport() {
  const [size, setSize] = useState({ width: window.innerWidth, height: window.innerHeight })
  useEffect(() => {
    const update = () => setSize({ width: window.innerWidth, height: window.innerHeight })
    window.addEventListener('resize', update)
    return () => window.removeEventListener('resize', update)
  }, [])
  return size
}

function normaliseSpeech(value: string) {
  return value.toLowerCase().replace(/[^a-z0-9\s]/g, ' ').replace(/\s+/g, ' ').trim()
}

function looksLikeAssistantEcho(heard: string, assistantSpeech: string) {
  const heardText = normaliseSpeech(heard)
  const spokenText = normaliseSpeech(assistantSpeech)
  if (!heardText || !spokenText) return false
  if (heardText.length > 10 && spokenText.includes(heardText)) return true
  const heardWords = heardText.split(' ').filter((word) => word.length > 2)
  const spokenWords = new Set(spokenText.split(' ').filter((word) => word.length > 2))
  if (!heardWords.length) return false
  const overlap = heardWords.filter((word) => spokenWords.has(word)).length / heardWords.length
  return overlap >= 0.72
}

export default function FloatingAssistant({
  assistantState,
  target,
  speech,
  choices,
  citations,
  running,
  reducedMotion,
  modelLabel,
  executionStatus,
  executedActions,
  processingProgress,
  processingStage,
  profile,
  onProfileChange,
  onSubmit,
  onChoice,
  onStop,
}: Props) {
  const [open, setOpen] = useState(false)
  const [message, setMessage] = useState('')
  const [listening, setListening] = useState(false)
  const [voiceMode, setVoiceMode] = useState(false)
  const [speaking, setSpeaking] = useState(false)
  const [profileOpen, setProfileOpen] = useState(false)
  const [voiceStatus, setVoiceStatus] = useState('Voice conversation is off')
  const [dynamicPosition, setDynamicPosition] = useState<{ x: number; y: number } | null>(null)
  const viewport = useViewport()

  const recognitionRef = useRef<RecognitionLike | null>(null)
  const voiceModeRef = useRef(false)
  const speechRef = useRef(speech)
  const silenceTimerRef = useRef<number | null>(null)
  const restartTimerRef = useRef<number | null>(null)
  const lastSubmittedRef = useRef('')
  const lastSpokenRef = useRef('')

  useEffect(() => { speechRef.current = speech }, [speech])

  useEffect(() => {
    if (!target || target === 'idle' || target === 'navigation-edge') {
      setDynamicPosition(null)
      return
    }
    let frame = 0
    const anchor = () => {
      const element = document.getElementById(target)
      if (!element) {
        setDynamicPosition(null)
        return
      }
      const rect = element.getBoundingClientRect()
      const x = Math.min(Math.max(22, rect.left + rect.width - 45), window.innerWidth - 110)
      const y = Math.min(Math.max(96, rect.top + Math.min(rect.height / 2, 90)), window.innerHeight - 135)
      setDynamicPosition({ x, y })
    }
    const onScroll = () => {
      window.cancelAnimationFrame(frame)
      frame = window.requestAnimationFrame(anchor)
    }
    const timer = window.setTimeout(anchor, 80)
    // Keep hovering over the target while smooth scrolling settles (product-demo mode).
    window.addEventListener('scroll', onScroll, { capture: true, passive: true })
    return () => {
      window.clearTimeout(timer)
      window.cancelAnimationFrame(frame)
      window.removeEventListener('scroll', onScroll, { capture: true } as EventListenerOptions)
    }
  }, [target, viewport])

  const position = useMemo(() => {
    const width = viewport.width
    const height = viewport.height
    const map: Record<string, { x: number; y: number }> = {
      idle: { x: width - 125, y: height - 135 },
      'navigation-edge': { x: 42, y: Math.max(170, height * 0.48) },
      'current-ratio-card': { x: Math.max(150, width * 0.25), y: 205 },
      'liability-payables': { x: Math.max(320, width * 0.73), y: 365 },
      'txn-dup-001': { x: Math.max(320, width * 0.72), y: 380 },
      'inv-1002': { x: Math.max(320, width * 0.68), y: 350 },
      'cash-flow-chart': { x: Math.max(250, width * 0.66), y: 460 },
      'upload-zone': { x: Math.max(250, width * 0.62), y: 420 },
      'setup-ollama': { x: Math.max(250, width * 0.65), y: 365 },
      'market-search-status': { x: Math.max(260, width * 0.65), y: 280 },
      'company-profile-form': { x: Math.max(260, width * 0.65), y: 330 },
    }
    return dynamicPosition ?? map[target] ?? map.idle
  }, [target, viewport, dynamicPosition])

  const stopSpeaking = useCallback(() => {
    if ('speechSynthesis' in window) window.speechSynthesis.cancel()
    setSpeaking(false)
  }, [])

  const submitMessage = useCallback((value: string, fromVoice = false) => {
    const clean = value.trim()
    if (!clean) return
    stopSpeaking()
    onSubmit(clean)
    setMessage('')
    if (!fromVoice) setOpen(false)
  }, [onSubmit, stopSpeaking])

  const scheduleVoiceSubmit = useCallback((transcript: string) => {
    const clean = transcript.trim()
    if (!clean) return
    if (silenceTimerRef.current) window.clearTimeout(silenceTimerRef.current)
    silenceTimerRef.current = window.setTimeout(() => {
      if (!voiceModeRef.current || !clean || clean === lastSubmittedRef.current) return
      lastSubmittedRef.current = clean
      setVoiceStatus('Sending your question…')
      submitMessage(clean, true)
    }, 650)
  }, [submitMessage])

  const createRecognition = useCallback(() => {
    const speechWindow = window as unknown as {
      SpeechRecognition?: new () => RecognitionLike
      webkitSpeechRecognition?: new () => RecognitionLike
    }
    const Recognition = speechWindow.SpeechRecognition || speechWindow.webkitSpeechRecognition
    if (!Recognition) return null
    const recognition = new Recognition()
    recognition.lang = profile?.voice_language || 'en-AU'
    recognition.continuous = true
    recognition.interimResults = true
    recognition.maxAlternatives = 1
    recognition.onspeechstart = () => {
      setListening(true)
      setVoiceStatus('Listening…')
    }
    recognition.onresult = (event: any) => {
      let interim = ''
      let final = ''
      const start = Number(event.resultIndex || 0)
      for (let index = start; index < event.results.length; index += 1) {
        const result = event.results[index]
        const transcript = String(result?.[0]?.transcript || '')
        if (result?.isFinal) final += transcript
        else interim += transcript
      }
      const heard = (final || interim).trim()
      if (!heard) return
      if (window.speechSynthesis?.speaking && looksLikeAssistantEcho(heard, speechRef.current)) return
      if (window.speechSynthesis?.speaking) {
        stopSpeaking()
        setVoiceStatus('Interrupted. Listening to you…')
      }
      setMessage(heard)
      setOpen(true)
      if (final.trim()) scheduleVoiceSubmit(final)
    }
    recognition.onerror = (event: any) => {
      const code = String(event?.error || '')
      if (code === 'not-allowed' || code === 'service-not-allowed') {
        voiceModeRef.current = false
        setVoiceMode(false)
        setVoiceStatus('Microphone permission was denied')
      } else if (code && code !== 'no-speech' && code !== 'aborted') {
        setVoiceStatus(`Voice input paused: ${code.replaceAll('-', ' ')}`)
      }
      setListening(false)
    }
    recognition.onend = () => {
      setListening(false)
      if (!voiceModeRef.current) return
      setVoiceStatus(window.speechSynthesis?.speaking ? 'Speaking · talk to interrupt' : 'Listening…')
      restartTimerRef.current = window.setTimeout(() => {
        if (!voiceModeRef.current) return
        try { recognition.start() } catch { /* already active */ }
      }, 260)
    }
    return recognition
  }, [profile?.voice_language, scheduleVoiceSubmit, stopSpeaking])

  const startVoiceConversation = useCallback(() => {
    let recognition = recognitionRef.current
    if (!recognition) {
      recognition = createRecognition()
      recognitionRef.current = recognition
    }
    if (!recognition) {
      setOpen(true)
      setMessage('Voice input is unavailable in this browser. Chrome or Edge is recommended.')
      return
    }
    voiceModeRef.current = true
    setVoiceMode(true)
    setOpen(true)
    setVoiceStatus('Listening…')
    try { recognition.start() } catch { /* already active */ }
  }, [createRecognition])

  const stopVoiceConversation = useCallback(() => {
    voiceModeRef.current = false
    setVoiceMode(false)
    setListening(false)
    setVoiceStatus('Voice conversation is off')
    if (silenceTimerRef.current) window.clearTimeout(silenceTimerRef.current)
    if (restartTimerRef.current) window.clearTimeout(restartTimerRef.current)
    try { recognitionRef.current?.abort() } catch { /* already stopped */ }
    stopSpeaking()
  }, [stopSpeaking])

  const speakText = useCallback((value: string) => {
    if (!('speechSynthesis' in window) || !value.trim()) return
    window.speechSynthesis.cancel()
    const utterance = new SpeechSynthesisUtterance(value)
    utterance.lang = profile?.voice_language || 'en-AU'
    utterance.rate = 1
    utterance.onstart = () => {
      setSpeaking(true)
      if (voiceModeRef.current) setVoiceStatus('Speaking · talk to interrupt')
    }
    utterance.onend = () => {
      setSpeaking(false)
      if (voiceModeRef.current) setVoiceStatus('Listening…')
    }
    utterance.onerror = () => {
      setSpeaking(false)
      if (voiceModeRef.current) setVoiceStatus('Listening…')
    }
    lastSpokenRef.current = value
    window.speechSynthesis.speak(utterance)
  }, [profile?.voice_language])

  useEffect(() => {
    if (!voiceMode || !profile?.voice_auto_speak || running || !speech.trim()) return
    if (speech === lastSpokenRef.current) return
    const timer = window.setTimeout(() => speakText(speech), 140)
    return () => window.clearTimeout(timer)
  }, [profile?.voice_auto_speak, running, speakText, speech, voiceMode])

  useEffect(() => () => {
    voiceModeRef.current = false
    if (silenceTimerRef.current) window.clearTimeout(silenceTimerRef.current)
    if (restartTimerRef.current) window.clearTimeout(restartTimerRef.current)
    try { recognitionRef.current?.abort() } catch { /* no-op */ }
    if ('speechSynthesis' in window) window.speechSynthesis.cancel()
  }, [])

  const bubbleOnRight = position.x < viewport.width / 2
  // Not enough headroom above Clippy for the bubble → render it below him instead.
  const bubbleBelow = position.y < Math.min(400, viewport.height * 0.45)
  const personas = profile?.catalogue?.personas || {}
  const responseStyles = profile?.catalogue?.response_styles || {}

  return (
    <motion.div
      className={`assistant-shell state-${assistantState}`}
      animate={{ x: position.x, y: position.y }}
      transition={reducedMotion ? { duration: 0 } : { type: 'spring', stiffness: 90, damping: 18 }}
      drag={!running}
      dragMomentum={false}
      style={{ left: 0, top: 0 }}
      aria-label="Clippy — LedgerFlow business analyst"
    >
      <AnimatePresence>
        {(speech || open || choices.length > 0) && (
          <motion.div
            className={`assistant-bubble ${bubbleOnRight ? 'bubble-right' : 'bubble-left'} ${bubbleBelow ? 'bubble-below' : ''}`}
            initial={{ opacity: 0, scale: 0.88, y: 8 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.92 }}
          >
            {speech && (
              <div className="assistant-speech-row">
                <p className="assistant-speech">{speech}</p>
                <button className="icon-button speech-button" onClick={() => speaking ? stopSpeaking() : speakText(speech)} title={speaking ? 'Stop speaking' : 'Read answer aloud'}>
                  {speaking ? <VolumeX size={15} /> : <Volume2 size={15} />}
                </button>
              </div>
            )}
            {assistantState === 'processing' && (
              <div className="assistant-processing-status">
                <div><span>{processingStage || 'Processing business evidence'}</span><strong>{Math.round(processingProgress)}%</strong></div>
                <div className="assistant-progress-track"><i style={{ width: `${Math.max(4, Math.min(100, processingProgress))}%` }} /></div>
              </div>
            )}

            <div className={`voice-conversation-strip ${voiceMode ? 'active' : ''}`}>
              <button className={`voice-mode-button ${voiceMode ? 'active' : ''}`} onClick={voiceMode ? stopVoiceConversation : startVoiceConversation}>
                {voiceMode ? <MicOff size={15} /> : <Mic size={15} />}
                {voiceMode ? 'Stop voice' : 'Talk to Ledger'}
              </button>
              <span className={listening ? 'listening' : ''}>{voiceStatus}</span>
              <button className="assistant-profile-toggle" onClick={() => setProfileOpen((value) => !value)} title="Assistant personality"><SlidersHorizontal size={14} /></button>
            </div>

            {profileOpen && profile && (
              <div className="assistant-profile-panel">
                <label>
                  <span>Personality</span>
                  <select value={profile.persona} onChange={(event) => void onProfileChange({ persona: event.target.value })}>
                    {Object.entries(personas).map(([id, item]) => <option key={id} value={id}>{item.label}</option>)}
                  </select>
                  <small>{personas[profile.persona]?.description}</small>
                </label>
                <label>
                  <span>Answer depth</span>
                  <select value={profile.response_style} onChange={(event) => void onProfileChange({ response_style: event.target.value })}>
                    {Object.keys(responseStyles).map((id) => <option key={id} value={id}>{id[0].toUpperCase() + id.slice(1)}</option>)}
                  </select>
                </label>
                <label className="profile-checkbox"><input type="checkbox" checked={profile.voice_auto_speak} onChange={(event) => void onProfileChange({ voice_auto_speak: event.target.checked })} /><span>Speak final answers automatically in voice mode</span></label>
              </div>
            )}

            {open && !running && (
              <div className="assistant-input-wrap">
                <textarea
                  autoFocus={!voiceMode}
                  value={message}
                  onChange={(event) => {
                    if (window.speechSynthesis?.speaking) stopSpeaking()
                    setMessage(event.target.value)
                  }}
                  onKeyDown={(event) => {
                    if (event.key === 'Enter' && !event.shiftKey) {
                      event.preventDefault()
                      submitMessage(message)
                    }
                  }}
                  placeholder={voiceMode ? 'Listening for your question…' : 'Ask Clippy anything about your data…'}
                  rows={3}
                />
                <div className="assistant-input-actions">
                  <button className={`icon-button ${voiceMode ? 'listening' : ''}`} onClick={voiceMode ? stopVoiceConversation : startVoiceConversation} aria-label="Voice conversation" title="Start or stop voice conversation">
                    {voiceMode ? <MicOff size={16} /> : <Mic size={16} />}
                  </button>
                  <button className="primary-mini" onClick={() => submitMessage(message)}><Send size={15} /> Send</button>
                </div>
              </div>
            )}
            {choices.length > 0 && (
              <div className="choice-cloud">
                {choices.map((choice) => <button key={choice} onClick={() => onChoice(choice)}>{choice}</button>)}
              </div>
            )}
            {citations.length > 0 && (
              <div className="assistant-citations">
                {citations.slice(0, 4).map((citation) => (
                  <a key={citation.url} href={citation.url} target="_blank" rel="noreferrer"><ExternalLink size={12} />{citation.title}</a>
                ))}
              </div>
            )}
            {executionStatus !== 'idle' && <div className={`assistant-action-receipt receipt-${executionStatus}`}><strong>{executionStatus.replaceAll('_', ' ')}</strong>{executedActions.length > 0 && <span>{executedActions.slice(0, 3).map((item) => item.replaceAll('_', ' ')).join(' · ')}</span>}</div>}
            <div className="assistant-model-label">{profile?.name || 'Clippy'} · {modelLabel}</div>
          </motion.div>
        )}
      </AnimatePresence>

      <motion.button
        className="assistant-character"
        onClick={() => !running && setOpen((value) => !value)}
        whileHover={reducedMotion ? undefined : { scale: 1.06, rotate: -2 }}
        whileTap={{ scale: 0.95 }}
        aria-expanded={open}
      >
        {assistantState === 'processing' && <><span className="assistant-processing-orbit orbit-one" /><span className="assistant-processing-orbit orbit-two" /></>}
        <svg className="clippy-body" viewBox="0 0 60 88" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
          <path d="M40 10 C40 4.5 35.5 1 30 1 C24.5 1 20 4.5 20 10 L20 64 C20 72.5 26 79 34 79 C42 79 48 72.5 48 64 L48 22" className="clippy-outer-stroke" strokeWidth="6.5" strokeLinecap="round" />
          <path d="M32 14 L32 62 C32 66.5 35 70 39.5 70 C44 70 47 66.5 47 62 L47 24" className="clippy-inner-stroke" strokeWidth="5" strokeLinecap="round" />
        </svg>
        <span className="clippy-face">
          <span className="clippy-brow brow-left" />
          <span className="clippy-brow brow-right" />
          <span className="clippy-eye eye-left"><span className="clippy-pupil" /></span>
          <span className="clippy-eye eye-right"><span className="clippy-pupil" /></span>
        </span>
        <span className="clippy-think-bubble"><i /><i /><i /></span>
      </motion.button>

      <AnimatePresence>
        {running && (
          <motion.button
            className="assistant-stop"
            onClick={() => { stopSpeaking(); onStop() }}
            initial={{ opacity: 0, scale: 0.7 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0 }}
            title="Stop guided sequence"
          >
            <Square size={13} fill="currentColor" /> Stop
          </motion.button>
        )}
        {!running && open && (
          <motion.button
            className="assistant-close"
            onClick={() => setOpen(false)}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            title="Close"
          >
            <X size={14} />
          </motion.button>
        )}
      </AnimatePresence>
    </motion.div>
  )
}
