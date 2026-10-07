export type YouTubePlayer = {
  destroy: () => void
  getCurrentTime: () => number
  getPlayerState: () => number
  seekTo: (seconds: number, allowSeekAhead: boolean) => void
  playVideo: () => void
  pauseVideo: () => void
}

export type YouTubePlayerOptions = {
  videoId: string
  playerVars: { enablejsapi: number; playsinline: number; origin: string; start?: number }
  events: {
    onReady: () => void
    onStateChange: (event: { data: number }) => void
    onError: (event: { data: number }) => void
  }
  host?: string
}

export type YouTubeApi = { Player: new (element: HTMLElement, options: YouTubePlayerOptions) => YouTubePlayer }

declare global {
  interface Window {
    YT?: YouTubeApi
    onYouTubeIframeAPIReady?: () => void
  }
}

const iframeApiUrl = 'https://www.youtube.com/iframe_api'
let iframeApiPromise: Promise<YouTubeApi> | null = null

export function loadYouTubeIframeApi(): Promise<YouTubeApi> {
  if (window.YT?.Player) return Promise.resolve(window.YT)
  if (iframeApiPromise) return iframeApiPromise

  const loading = new Promise<YouTubeApi>((resolve, reject) => {
    let settled = false
    let timeout: number
    const ready = () => {
      if (settled) return
      if (!window.YT?.Player) {
        fail(new Error('YouTube IFrame Player API loaded without a Player constructor.'))
        return
      }
      settle(() => resolve(window.YT!))
    }
    const previousReady = window.onYouTubeIframeAPIReady
    window.onYouTubeIframeAPIReady = () => {
      previousReady?.()
      ready()
    }
    const existing = document.querySelector<HTMLScriptElement>(`script[src="${iframeApiUrl}"]`)
    const script = existing ?? document.createElement('script')
    const settle = (callback: () => void) => {
      if (settled) return
      settled = true
      window.clearTimeout(timeout)
      script.removeEventListener('error', onError)
      callback()
    }
    const fail = (error: Error) => settle(() => {
      script.remove()
      reject(error)
    })
    const onError = () => fail(new Error('Could not load the YouTube IFrame Player API.'))
    timeout = window.setTimeout(() => fail(new Error('Timed out loading the YouTube IFrame Player API.')), 10000)
    if (window.YT?.Player) {
      ready()
      return
    }
    script.addEventListener('error', onError, { once: true })
    if (!existing) {
      script.src = iframeApiUrl
      script.async = true
      document.head.appendChild(script)
    }
  })
  // A failed script element cannot be reused. Do not cache its rejected promise.
  iframeApiPromise = loading.catch(error => {
    iframeApiPromise = null
    throw error
  })
  return iframeApiPromise
}

export function resetYouTubeIframeApiLoaderForTests() {
  iframeApiPromise = null
  delete window.YT
  delete window.onYouTubeIframeAPIReady
  document.querySelector(`script[src="${iframeApiUrl}"]`)?.remove()
}
