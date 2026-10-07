import { act, fireEvent, render, screen } from '@testing-library/react'
import { useState } from 'react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import EventTimeline, { closestEventId } from '../components/EventTimeline'
import type { CanonicalEvent, VideoSource } from '../types'
import { loadYouTubeIframeApi, resetYouTubeIframeApiLoaderForTests, type YouTubePlayer, type YouTubePlayerOptions } from '../youtubeIframeApi'
import { useYouTubeSync } from './useYouTubeSync'

const source: VideoSource = { id: 1, original_url: 'https://youtube.com/watch?v=abcdefghijk', provider: 'youtube', provider_video_id: 'abcdefghijk', availability_state: 'ready' }
const replacementSource: VideoSource = { ...source, id: 2, original_url: 'https://youtube.com/watch?v=lmnopqrstuv', provider_video_id: 'lmnopqrstuv' }
const events: CanonicalEvent[] = [{ id: 7, sequence: 1, active: true, payload: { kind: 'other', period: 1, regulation_seconds: null, clock_unverified: true, team_id: null, player_id: null, related_player_id: null, outcome: null, fact_kind: 'observed', evidence_state: 'confirmed', uncertainty: [], note: null }, evidence: [{ id: 1, kind: 'video', video_source_id: 1, video_anchor_seconds: 42, uncertainty: [] }] }]

let options: YouTubePlayerOptions
let fakePlayer: YouTubePlayer
let createPlayer: ReturnType<typeof vi.fn>

function Probe({ videoSource = source }: { videoSource?: VideoSource }) {
  const player = useYouTubeSync(videoSource)
  const [time, setTime] = useState('none')
  return <><div ref={player.playerRef} title="YouTube player" /><output aria-label="observed time">{player.currentTime}</output><output aria-label="playback state">{player.isPlaying ? 'playing' : 'paused'}</output><output aria-label="availability">{player.availability}</output><EventTimeline events={events} selectedId={null} highlightedId={closestEventId(events, player.currentTime)} onSelect={vi.fn()} onRevise={vi.fn()} /><button onClick={() => player.seekTo(70)}>Seek</button><button onClick={() => player.pauseAndReadCurrentTime().then(value => setTime(String(value))).catch(() => setTime('error'))}>Calibrate</button><output aria-label="calibrated time">{time}</output></>
}

function ReviewProbe() {
  const [videoSource, setVideoSource] = useState(source)
  const player = useYouTubeSync(videoSource)
  return <><div ref={player.playerRef} title="YouTube player" /><output aria-label="availability">{player.availability}</output><button onClick={() => setVideoSource(replacementSource)}>Replace source</button><button onClick={player.retry}>Retry player</button></>
}

async function makeApiReady() {
  await act(async () => {
    window.onYouTubeIframeAPIReady?.()
    await Promise.resolve()
  })
}

beforeEach(() => {
  resetYouTubeIframeApiLoaderForTests()
  fakePlayer = {
    destroy: vi.fn(),
    getCurrentTime: vi.fn(() => 42),
    getPlayerState: vi.fn(() => 2),
    seekTo: vi.fn(),
    playVideo: vi.fn(),
    pauseVideo: vi.fn(),
  }
  createPlayer = vi.fn((_element: HTMLElement, nextOptions: YouTubePlayerOptions) => {
    options = nextOptions
    return fakePlayer
  })
})

afterEach(() => {
  resetYouTubeIframeApiLoaderForTests()
  vi.useRealTimers()
})

describe('useYouTubeSync', () => {
  it('creates the official API player on API ready and observes its time', async () => {
    window.YT = { Player: createPlayer as unknown as new (element: HTMLElement, options: YouTubePlayerOptions) => YouTubePlayer }
    render(<Probe />)
    await makeApiReady()
    expect(createPlayer).toHaveBeenCalledOnce()
    expect(options.videoId).toBe(source.provider_video_id)
    expect(options.host).toBe('https://www.youtube-nocookie.com')
    expect(options.playerVars).toMatchObject({ enablejsapi: 1, playsinline: 1, origin: window.location.origin })

    act(() => options.events.onReady())
    expect(screen.getByLabelText('observed time').textContent).toBe('42')
    expect(screen.getByRole('button', { name: /#1/ }).getAttribute('aria-current')).toBe('true')
  })

  it('reads once when cued and never polls while cued or paused', async () => {
    vi.useFakeTimers()
    window.YT = { Player: createPlayer as unknown as new (element: HTMLElement, options: YouTubePlayerOptions) => YouTubePlayer }
    render(<Probe />)
    await makeApiReady()
    act(() => options.events.onReady())
    vi.mocked(fakePlayer.getCurrentTime).mockClear()

    act(() => options.events.onStateChange({ data: 5 }))
    expect(fakePlayer.getCurrentTime).toHaveBeenCalledOnce()
    act(() => { vi.advanceTimersByTime(1500) })
    expect(fakePlayer.getCurrentTime).toHaveBeenCalledOnce()

    act(() => options.events.onStateChange({ data: 2 }))
    expect(fakePlayer.getCurrentTime).toHaveBeenCalledTimes(2)
  })

  it('reads immediately and every 500ms only while playing, then stops on pause', async () => {
    vi.useFakeTimers()
    window.YT = { Player: createPlayer as unknown as new (element: HTMLElement, options: YouTubePlayerOptions) => YouTubePlayer }
    render(<Probe />)
    await makeApiReady()
    act(() => options.events.onReady())
    vi.mocked(fakePlayer.getCurrentTime).mockClear()

    act(() => options.events.onStateChange({ data: 1 }))
    expect(screen.getByLabelText('playback state').textContent).toBe('playing')
    expect(fakePlayer.getCurrentTime).toHaveBeenCalledOnce()
    act(() => { vi.advanceTimersByTime(1000) })
    expect(fakePlayer.getCurrentTime).toHaveBeenCalledTimes(3)

    act(() => options.events.onStateChange({ data: 2 }))
    act(() => { vi.advanceTimersByTime(1000) })
    expect(fakePlayer.getCurrentTime).toHaveBeenCalledTimes(4)
  })

  it('calibrates from a direct official read while paused', async () => {
    vi.mocked(fakePlayer.getCurrentTime).mockReturnValue(74)
    window.YT = { Player: createPlayer as unknown as new (element: HTMLElement, options: YouTubePlayerOptions) => YouTubePlayer }
    render(<Probe />)
    await makeApiReady()
    act(() => options.events.onReady())
    fireEvent.click(screen.getByRole('button', { name: 'Calibrate' }))
    expect(fakePlayer.pauseVideo).not.toHaveBeenCalled()
    expect((await screen.findByLabelText('calibrated time')).textContent).toBe('74')
  })

  it('pauses a playing player, waits for PAUSED, then directly reads the calibration time', async () => {
    vi.mocked(fakePlayer.getPlayerState).mockReturnValue(1)
    vi.mocked(fakePlayer.getCurrentTime).mockReturnValue(74)
    window.YT = { Player: createPlayer as unknown as new (element: HTMLElement, options: YouTubePlayerOptions) => YouTubePlayer }
    render(<Probe />)
    await makeApiReady()
    act(() => options.events.onReady())
    fireEvent.click(screen.getByRole('button', { name: 'Calibrate' }))
    expect(fakePlayer.pauseVideo).toHaveBeenCalledOnce()
    expect(screen.getByLabelText('calibrated time').textContent).toBe('none')
    act(() => options.events.onStateChange({ data: 2 }))
    expect((await screen.findByLabelText('calibrated time')).textContent).toBe('74')
  })

  it('uses a maintained zero timestamp only when a direct read fails', async () => {
    vi.mocked(fakePlayer.getCurrentTime).mockReturnValue(0)
    window.YT = { Player: createPlayer as unknown as new (element: HTMLElement, options: YouTubePlayerOptions) => YouTubePlayer }
    render(<Probe />)
    await makeApiReady()
    act(() => options.events.onReady())
    vi.mocked(fakePlayer.getCurrentTime).mockImplementation(() => { throw new Error('unavailable') })
    fireEvent.click(screen.getByRole('button', { name: 'Calibrate' }))
    expect((await screen.findByLabelText('calibrated time')).textContent).toBe('0')
  })

  it('destroys and recreates the player only when the active source identity changes', async () => {
    window.YT = { Player: createPlayer as unknown as new (element: HTMLElement, options: YouTubePlayerOptions) => YouTubePlayer }
    const view = render(<Probe />)
    await makeApiReady()
    expect(createPlayer).toHaveBeenCalledOnce()
    view.rerender(<Probe videoSource={{ ...source, availability_state: 'unknown' }} />)
    expect(createPlayer).toHaveBeenCalledOnce()

    view.rerender(<Probe videoSource={replacementSource} />)
    await act(async () => { await Promise.resolve() })
    expect(fakePlayer.destroy).toHaveBeenCalledOnce()
    expect(createPlayer).toHaveBeenCalledTimes(2)
  })

  it('destroys a terminal-error player and creates a new one for a replacement source', async () => {
    vi.useFakeTimers()
    window.YT = { Player: createPlayer as unknown as new (element: HTMLElement, options: YouTubePlayerOptions) => YouTubePlayer }
    render(<ReviewProbe />)
    await makeApiReady()
    expect(createPlayer).toHaveBeenCalledOnce()
    act(() => options.events.onStateChange({ data: 1 }))
    const readsBeforeError = vi.mocked(fakePlayer.getCurrentTime).mock.calls.length

    act(() => options.events.onError({ data: 100 }))
    expect(fakePlayer.destroy).toHaveBeenCalledOnce()
    expect(screen.getByLabelText('availability').textContent).toBe('unavailable')
    act(() => { vi.advanceTimersByTime(1000) })
    expect(fakePlayer.getCurrentTime).toHaveBeenCalledTimes(readsBeforeError)

    fireEvent.click(screen.getByRole('button', { name: 'Replace source' }))
    await act(async () => { await Promise.resolve() })
    expect(createPlayer).toHaveBeenCalledTimes(2)
  })

  it('retries a failed iframe API load with a new script', async () => {
    const firstLoad = loadYouTubeIframeApi()
    const firstScript = document.querySelector('script[src="https://www.youtube.com/iframe_api"]')!
    act(() => firstScript.dispatchEvent(new Event('error')))
    await expect(firstLoad).rejects.toThrow('Could not load the YouTube IFrame Player API.')

    const secondLoad = loadYouTubeIframeApi()
    const secondScript = document.querySelector('script[src="https://www.youtube.com/iframe_api"]')!
    expect(secondScript).not.toBe(firstScript)
    window.YT = { Player: createPlayer as unknown as new (element: HTMLElement, options: YouTubePlayerOptions) => YouTubePlayer }
    await makeApiReady()
    await expect(secondLoad).resolves.toBe(window.YT)
  })

  it('reinitializes the same source through the explicit retry action', async () => {
    window.YT = { Player: createPlayer as unknown as new (element: HTMLElement, options: YouTubePlayerOptions) => YouTubePlayer }
    render(<ReviewProbe />)
    await makeApiReady()
    act(() => options.events.onError({ data: 100 }))

    fireEvent.click(screen.getByRole('button', { name: 'Retry player' }))
    await act(async () => { await Promise.resolve() })
    expect(createPlayer).toHaveBeenCalledTimes(2)
  })

  it('does not use a previous source timestamp after source replacement', async () => {
    vi.mocked(fakePlayer.getCurrentTime).mockReturnValue(74)
    window.YT = { Player: createPlayer as unknown as new (element: HTMLElement, options: YouTubePlayerOptions) => YouTubePlayer }
    const view = render(<Probe />)
    await makeApiReady()
    act(() => options.events.onReady())
    view.rerender(<Probe videoSource={replacementSource} />)
    vi.mocked(fakePlayer.getCurrentTime).mockImplementation(() => { throw new Error('unavailable') })
    fireEvent.click(screen.getByRole('button', { name: 'Calibrate' }))
    expect((await screen.findByLabelText('calibrated time')).textContent).toBe('error')
  })

  it('marks playback unavailable when the script or API cannot load', async () => {
    const view = render(<Probe />)
    const script = document.querySelector('script[src="https://www.youtube.com/iframe_api"]')!
    act(() => script.dispatchEvent(new Event('error')))
    expect((await screen.findByLabelText('availability')).textContent).toBe('player_error')

    view.unmount()
    resetYouTubeIframeApiLoaderForTests()
    render(<Probe />)
    await makeApiReady()
    expect((await screen.findByLabelText('availability')).textContent).toBe('player_error')
  })
})
