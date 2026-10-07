import { describe, expect, it, vi } from 'vitest'
import { dispatchReviewShortcut, isEditableTarget, selectedEventRevision } from './reviewShortcuts'

function actions() {
  return {
    togglePlayback: vi.fn(), seek: vi.fn(), navigateEvents: vi.fn(), addAnchor: vi.fn(), tag: vi.fn(),
    save: vi.fn(), focusNotes: vi.fn(), undo: vi.fn(), redo: vi.fn(), showHelp: vi.fn(),
  }
}

function keydown(key: string, options: Partial<KeyboardEvent> = {}) {
  let prevented = false
  return {
    key, defaultPrevented: false, isComposing: false, ctrlKey: false, metaKey: false, altKey: false, shiftKey: false,
    preventDefault: () => { prevented = true },
    get prevented() { return prevented },
    ...options,
  } as unknown as KeyboardEvent & { prevented: boolean }
}

describe('review shortcuts', () => {
  it('maps all seek steps and preserves browser-safe modified shortcuts', () => {
    const commands = actions()
    const seek = keydown('J', { shiftKey: true })

    expect(dispatchReviewShortcut(seek, commands)).toBe(true)
    expect(commands.seek).toHaveBeenCalledWith(-10)
    dispatchReviewShortcut(keydown(']'), commands)
    expect(commands.seek).toHaveBeenLastCalledWith(10)
    expect(seek.prevented).toBe(true)
    expect(dispatchReviewShortcut(keydown('s', { ctrlKey: true }), commands)).toBe(false)
    expect(commands.save).not.toHaveBeenCalled()
  })

  it('does not capture keyboard input from editable targets', () => {
    const commands = actions()
    const typing = keydown('s', { target: { isContentEditable: true } as unknown as EventTarget })

    expect(dispatchReviewShortcut(typing, commands)).toBe(false)
    expect(typing.prevented).toBe(false)
    expect(commands.save).not.toHaveBeenCalled()
    expect(isEditableTarget({ tagName: 'SELECT' } as unknown as EventTarget)).toBe(true)
  })

  it('leaves browser, assistive, and composition commands untouched', () => {
    const commands = actions()

    for (const event of [
      keydown('s', { altKey: true }),
      keydown('s', { metaKey: true }),
      keydown('s', { isComposing: true }),
      keydown('s', { defaultPrevented: true }),
    ]) {
      expect(dispatchReviewShortcut(event, commands)).toBe(false)
      expect(event.prevented).toBe(false)
    }
    expect(commands.save).not.toHaveBeenCalled()
  })

  it('navigates events with n/p and reserves Shift+N for notes', () => {
    const commands = actions()

    expect(dispatchReviewShortcut(keydown('n'), commands)).toBe(true)
    expect(dispatchReviewShortcut(keydown('p'), commands)).toBe(true)
    expect(dispatchReviewShortcut(keydown('n', { shiftKey: true }), commands)).toBe(true)
    expect(dispatchReviewShortcut(keydown('?'), commands)).toBe(true)
    expect(dispatchReviewShortcut(keydown('x'), commands)).toBe(false)
    expect(commands.navigateEvents).toHaveBeenNthCalledWith(1, 1)
    expect(commands.navigateEvents).toHaveBeenNthCalledWith(2, -1)
    expect(commands.focusNotes).toHaveBeenCalledOnce()
    expect(commands.showHelp).toHaveBeenCalledOnce()
  })

  it('limits revisions to the selected analytical event state', () => {
    expect(selectedEventRevision(undefined, 'undo')).toBeNull()
    expect(selectedEventRevision({ id: 4, active: true }, 'undo')).toBe(4)
    expect(selectedEventRevision({ id: 4, active: true }, 'redo')).toBeNull()
    expect(selectedEventRevision({ id: 4, active: false }, 'undo')).toBeNull()
    expect(selectedEventRevision({ id: 4, active: false }, 'redo')).toBe(4)
  })
})
