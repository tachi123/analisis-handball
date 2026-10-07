# Match Report Timeline Specification

## Purpose

Provide a protected, read-only per-match view of canonical observations and their unfiltered server-derived context.

## Requirements

### Requirement: Provide a protected match reports route
The system MUST provide an authenticated route scoped to one match and an explicit entry from that match's context. The route MUST be read-only and MUST NOT expose capture, edit, revision, or exclusion controls.

#### Scenario: Open reports from a match
- GIVEN an authenticated analyst viewing a match context
- WHEN the analyst chooses the reports timeline entry
- THEN the protected timeline for that match opens
- AND no mutation controls are available

#### Scenario: Access another match
- GIVEN a timeline route whose match is unavailable to the analyst
- WHEN the route is opened
- THEN the system MUST deny access or show its established unavailable state

### Requirement: Present canonical chronology with uncertainty
The system MUST order canonical events by verified regulation time, then video anchor, then canonical sequence. It MUST label every fallback time as uncertain and MUST NOT imply verified clock precision.

#### Scenario: Order mixed clock evidence
- GIVEN events with verified times, video anchors, and sequence-only values
- WHEN the timeline renders
- THEN verified-time events precede fallback events in their respective order
- AND fallback events show clock uncertainty

### Requirement: Filter the displayed event list
The system MUST allow independent or combined local filters for player, kind, period, and evidence state, and MUST announce the resulting visible-event count. Filters MUST affect only the displayed list and selection navigation.

#### Scenario: Combine filters
- GIVEN a loaded timeline
- WHEN an analyst chooses player and evidence-state filters
- THEN only matching canonical events are displayed
- AND the result count is available to assistive technology

#### Scenario: Clear filters
- GIVEN active timeline filters
- WHEN the analyst clears them
- THEN all loaded canonical events are displayed

### Requirement: Select events and synchronize video when possible
The system MUST make each displayed event selectable. For an event with usable video evidence and available playback, selection MUST seek through the established player boundary. Otherwise, selection MUST preserve details and explain why playback did not move.

#### Scenario: Select video-evidenced event
- GIVEN available playback and a selected event with a usable anchor
- WHEN the analyst selects the event
- THEN playback seeks to its evidence time

#### Scenario: Select event without seek
- GIVEN an event without a usable anchor or unavailable playback
- WHEN the analyst selects it
- THEN its details open without seeking
- AND an accessible no-seek explanation is shown

### Requirement: Show the current canonical event detail
The system MUST show the selected event's latest canonical payload, evidence, revision number and reason, active state, and clock uncertainty. It MUST NOT provide historical revision payload drill-down.

#### Scenario: Inspect current event
- GIVEN a selected canonical event
- WHEN its detail panel renders
- THEN it displays the latest available fields and uncertainty
- AND no historical revision-content navigation is offered

### Requirement: Preserve unfiltered authoritative context
The system MUST show canonical state, metrics, and reconciliation from their server-derived match responses without applying timeline filters. It MUST NOT calculate, label, or present filtered results as authoritative metrics.

#### Scenario: Filter while reviewing context
- GIVEN active timeline filters and loaded match context
- WHEN the summary renders
- THEN state, metrics, and reconciliation remain unfiltered server-derived values
- AND no filtered authoritative total is displayed

### Requirement: Support accessible keyboard operation
The system MUST provide semantic names, visible focus, keyboard-operable filters and event selection, and instructions for available timeline shortcuts. Keyboard commands MUST NOT intercept text entry or browser or assistive-technology commands.

#### Scenario: Navigate events by keyboard
- GIVEN focus in the timeline's event list
- WHEN the analyst uses the documented event-navigation key
- THEN the next or previous visible event becomes selected and its detail is announced

#### Scenario: Type in a filter control
- GIVEN focus is in a filter's text-entry control
- WHEN the analyst types a shortcut character
- THEN the character is entered normally and no timeline command runs
