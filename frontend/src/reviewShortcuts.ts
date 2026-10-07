export type ReviewShortcutActions = {
  togglePlayback: () => void
  seek: (seconds: number) => void
  navigateEvents: (direction: -1 | 1) => void
  addAnchor: () => void
  tag: () => void
  save: () => void
  focusNotes: () => void
  undo: () => void
  redo: () => void
  showHelp: () => void
}

export type SelectedReviewEvent = { id: number; active: boolean } | undefined

export function selectedEventRevision(event: SelectedReviewEvent, action: 'undo' | 'redo') {
  if (!event || (action === 'undo' && !event.active) || (action === 'redo' && event.active)) return null
  return event.id
}

export function isEditableTarget(target: EventTarget | null) {
  const element = target as { isContentEditable?: unknown; tagName?: unknown } | null
  return Boolean(element?.isContentEditable) || ['INPUT', 'TEXTAREA', 'SELECT'].includes(String(element?.tagName))
}

export function dispatchReviewShortcut(event: KeyboardEvent, actions: ReviewShortcutActions) {
  if (event.defaultPrevented || event.isComposing || event.ctrlKey || event.metaKey || event.altKey || isEditableTarget(event.target)) return false

  const key = event.key.toLowerCase()
  const command = (() => {
    if (key === ' ') return actions.togglePlayback
    if (key === ',') return () => actions.seek(-1)
    if (key === '.') return () => actions.seek(1)
    if (key === 'j') return () => actions.seek(event.shiftKey ? -10 : -5)
    if (key === 'l') return () => actions.seek(event.shiftKey ? 10 : 5)
    if (key === '[') return () => actions.seek(-10)
    if (key === ']') return () => actions.seek(10)
    if (key === 'a') return actions.addAnchor
    if (key === 't') return actions.tag
    if (key === 's') return actions.save
    if (key === 'n' && event.shiftKey) return actions.focusNotes
    if (key === 'n') return () => actions.navigateEvents(1)
    if (key === 'p') return () => actions.navigateEvents(-1)
    if (key === 'u') return actions.undo
    if (key === 'r') return actions.redo
    if (key === '?') return actions.showHelp
    return null
  })()
  if (!command) return false
  event.preventDefault()
  command()
  return true
}
