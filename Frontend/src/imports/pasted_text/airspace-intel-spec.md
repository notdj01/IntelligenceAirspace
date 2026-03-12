1. Project Overview
This document is the complete, authoritative build specification for AIRSPACE-INTEL — a real-time, dark-themed tactical airspace monitoring dashboard. It synthesises two source codebases:
•	Source A (Intelligent_Airspace_Monitoring_Dashboard): Provides the overall dashboard shell — App.tsx layout, LeftSidebar (Agentic Mesh + Risk Feed), RightSidebar (target detail, Micro-Doppler canvas, XAI Commander), and the FrequencyVisualizer canvas component. Built with Vite + React + TypeScript + Tailwind CSS.
•	Source B (Leaflet Map UI): Provides the production-grade interactive map engine — AirspaceMapClient using Leaflet.js with real OpenStreetMap tile layers (dark-filtered), dynamic SVG markers per classification, animated polyline trajectories, a labelled No-Fly Zone polygon, and tooltips. Built with Next.js 14 + TypeScript + Tailwind CSS.
The final product combines: LEFT SIDEBAR from Source A + CENTER MAP from Source B + RIGHT SIDEBAR from Source A.

2. Technology Stack
2.1 Framework & Build
•	Framework: Next.js 14 (App Router) — use Source B's next.config.mjs as reference
•	Language: TypeScript (strict mode)
•	Styling: Tailwind CSS v4 (utility-first) + inline style overrides for glassmorphism
•	Build tool: Next.js built-in webpack/turbopack (no Vite)
2.2 Key Libraries
•	leaflet ^1.9.x — core map engine (client-side only, no SSR)
•	next/dynamic — required to lazy-load Leaflet component with { ssr: false }
•	lucide-react — all icon usage (Shield, ScanEye, Terminal, Crosshair, Zap, Bot, CheckCircle, ChevronRight, Radio, AlertTriangle, Info, Activity, Satellite, Clock, Map)
•	React 18 hooks — useState, useEffect, useRef, useCallback, useMemo
2.3 Fonts
•	JetBrains Mono (or Geist Mono) — all data labels, IDs, coordinates, timestamps, alert messages
•	Inter (or Geist) — UI chrome labels, button text, paragraph prose
2.4 Color Palette (CSS Variables)
--bg-primary:   #0f172a   /* Slate-950 — entire page background */
--bg-panel:     rgba(13,20,32,0.7)  /* Glassmorphic panel fill */
--accent-cyan:  #22d3ee   /* Primary accent — borders, icons, active states */
--alert-rose:   #f43f5e   /* Critical risk, ALERT type */
--warn-orange:  #fb923c   /* Warning / XAI Commander accent */
--safe-green:   #4ade80   /* Transponder ON, Low risk */
--warn-yellow:  #fbbf24   /* Medium risk */
--text-primary: #e2e8f0   /* Main readable text */
--text-muted:   #64748b   /* Secondary labels */
--text-subtle:  #334155   /* Placeholder / dim text */

3. Canonical Data Schema (Single Source of Truth)
All dashboard components must read from a single shared state object. Define types in lib/airspace-data.ts:
3.1 Type Definitions
export type RiskLevel      = "Critical" | "High" | "Medium" | "Low";
export type Classification = "Drone" | "Bird" | "Aircraft" | "Unknown";
export type AgentStatus    = "Active" | "Ready" | "Offline";
export type AlertType      = "ALERT" | "WARNING" | "INFO";
3.2 AirTarget Interface
Property	Type	Description
id	string	Unique target callsign e.g. UNID-007, FLIGHT-221
coords	[number, number]	Current [lat, lng] position in decimal degrees
trajectory	[number, number][]	Ordered array of past [lat, lng] positions (last 12 points max)
speed	number	Speed in knots
adsb	boolean	true = ADS-B transponder active; false = transponder OFF (unverified)
classification	Classification	Drone | Bird | Aircraft | Unknown
confidence	number	0-100 classifier confidence percentage
risk_level	RiskLevel	Critical | High | Medium | Low
3.3 Supporting Interfaces
interface Agents { sentry: AgentStatus; profiler: AgentStatus; commander: AgentStatus; }
interface DashboardState { active_targets: AirTarget[]; agents: Agents; }
interface RiskAlert { id: string; type: AlertType; message: string; timestamp: Date; }
3.4 Initial Seed Data (4 Targets)
•	UNID-007 — Drone, coords [18.92, 72.83], speed 150kts, adsb: false, confidence 92%, risk: Critical
•	FLIGHT-221 — Aircraft, coords [19.08, 72.87], speed 480kts, adsb: true, confidence 99%, risk: Low
•	BIO-042 — Bird, coords [18.98, 72.92], speed 12kts, adsb: false, confidence 78%, risk: Low
•	UNID-013 — Drone, coords [19.15, 72.76], speed 95kts, adsb: false, confidence 85%, risk: High
3.5 Risk Color Map
export const RISK_COLORS: Record<RiskLevel, string> = {
  Critical: "#f43f5e",  High: "#fb923c",  Medium: "#fbbf24",  Low: "#4ade80"
};
3.6 No-Fly Zone Coordinates (Mumbai Harbor)
export const NO_FLY_ZONE: [number, number][] = [
  [18.89, 72.82], [18.91, 72.79], [18.95, 72.80],
  [18.94, 72.84], [18.91, 72.85]
];

4. Page Layout Architecture
4.1 Root Layout (app/layout.tsx)
Set html/body to h-screen, overflow-hidden, dark background #0f172a. Import JetBrains Mono and Inter from Google Fonts. Apply font-sans globally and font-mono to data elements.
4.2 Main Page (app/page.tsx)
This is the orchestrator — holds all shared state and passes props down. Structure:
•	State: dashboardState (DashboardState), alerts (RiskAlert[]), selectedTarget (AirTarget | null), isClient (boolean)
•	Layout: <main className='flex flex-col h-screen overflow-hidden'>
◦  Row 1 — <DashboardHeader /> (fixed height ~48px)
◦  Row 2 — <div className='flex flex-1 gap-3 p-3 overflow-hidden min-h-0'>
◦    Column 1 — Left Sidebar div, w-72, flex-shrink-0, glassmorphic panel
◦    Column 2 — Center column, flex-1, contains target roster strip + map
◦    Column 3 — Right Sidebar div, w-72, flex-shrink-0, glassmorphic panel
4.3 Glassmorphic Panel Style (applied to all three columns)
background: rgba(13,20,32,0.7)
backdropFilter: blur(12px)
border: 1px solid rgba(255,255,255,0.07)
borderRadius: 8px

5. Component: DashboardHeader
File: components/dashboard-header.tsx | Props: { targetCount: number; criticalCount: number }
5.1 Visual Structure
Full-width horizontal bar, height ~48px. Three zones: Left (Branding), Center (Status Chips), Right (Clock + Live indicator).
background: rgba(13,20,32,0.95)
backdropFilter: blur(12px)
borderBottom: 1px solid rgba(34,211,238,0.12)
5.2 Left Zone — Branding
•	32×32px icon container with cyan-tinted background (rgba(34,211,238,0.1)) and 1px cyan border at 25% opacity
•	Lucide <Satellite size={16} /> icon in cyan #22d3ee
•	Title 'AIRSPACE-INTEL' — font-mono, text-sm, bold, tracking-widest, uppercase, color #e2e8f0
•	Subtitle 'Tactical Situational Awareness v2.4.1' — font-mono, text-xs, color #334155
5.3 Center Zone — Status Chips
•	SECTOR chip: 'SECTOR: MUMBAI' — cyan background/border, Map icon
•	TRACKS chip: '{targetCount} TRACKS ACTIVE' — green background/border, Activity icon
•	CRITICAL chip (conditional — only when criticalCount > 0): rose background/border, pulsing rose dot, '{criticalCount} CRITICAL', animate with blink-border keyframe (opacity 1 ↔ 0.5 at 1.5s)
5.4 Right Zone — Clock
•	Live UTC time updated every 1 second via setInterval in useEffect
•	Use isClient pattern to avoid SSR hydration mismatch (setTime only in useEffect)
•	Clock icon + 'UTC' label, time displayed as HH:MM:SS in font-mono, bold, tracking-widest
•	Green glowing dot with boxShadow: '0 0 8px #4ade80' + small 'LIVE' label below

6. Component: LeftSidebar
File: components/left-sidebar.tsx | Props: { agents: Agents; alerts: RiskAlert[] }
Renders inside an <aside> with flex-col, gap-4, h-full, overflow-hidden. Contains two sections: Agentic Mesh and Risk Feed.
6.1 Section A — Agentic Mesh Header
•	Radio icon (lucide) + label 'AGENTIC MESH' — font-mono, text-xs, uppercase, tracking-widest, color #22d3ee
6.2 AgentCard Component (rendered 3 times)
Each card is a glassmorphic rounded-lg with backdrop-blur, subtle border, and internal flex row.
6.2.1 Card Structure
•	Left: 36×36px icon container — rgba(34,211,238,0.1) background, 1px rgba(34,211,238,0.2) border, rounded-md
•	Icon inside: Lucide icon in cyan (#22d3ee). Sentry = Shield, Profiler = ScanEye, Commander = Terminal
•	Center: Agent name (uppercase, font-sans, text-xs, tracking-widest, color #94a3b8) + description (font-mono, text-xs, color #475569)
•	Right: Pulsing LED dot + status text
6.2.2 LED Indicator Logic
•	Active status → green dot (#4ade80) with boxShadow '0 0 6px #4ade80, 0 0 12px rgba(74,222,128,0.4)', animated with pulse-led keyframe
•	Ready status → orange dot (#fb923c) with boxShadow '0 0 6px #fb923c'
•	Offline status → gray dot (#64748b), no glow, no animation
6.2.3 Three Agent Definitions
•	Sentry | Shield icon | 'Perimeter radar · 360° sweep'
•	Profiler | ScanEye icon | 'Micro-Doppler analysis engine'
•	Commander | Terminal icon | 'Agentic decision & response'
6.3 Divider
A thin horizontal rule between the two sections: border-t with borderColor rgba(255,255,255,0.08).
6.4 Section B — Risk Feed
6.4.1 Header
•	AlertTriangle icon + 'RISK FEED' label in rose #f43f5e
•	'LIVE' badge on the right: rose-tinted background/border pill
6.4.2 Alert List Container
•	Scrollable flex-col with scrollbarWidth: thin, scrollbarColor: #1e293b transparent
•	flex-1 to fill remaining space, overflow-y-auto, min-h-0 for proper flex sizing
6.4.3 Individual Alert Item
•	Each item is a rounded-md div with conditional color tinting based on alert.type
◦  ALERT → background rgba(244,63,94,0.08), border rgba(244,63,94,0.25)
◦  WARNING → background rgba(251,146,60,0.08), border rgba(251,146,60,0.25)
◦  INFO → background rgba(15,23,42,0.6), border rgba(255,255,255,0.07)
•	Icon row: AlertTriangle (rose for ALERT, orange for WARNING) or Info (cyan for INFO)
•	Type badge: font-mono, font-bold, tracking-wider in matching accent color
•	Timestamp: right-aligned, font-mono, text-xs, color #475569, formatted as UTC HH:MM:SS
•	Message text: font-mono, text-xs, leading-relaxed, color #94a3b8
6.4.4 Fade-In Animation Logic
Track visible alert IDs in a Set via useState. When a new alert appears at alerts[0], after a 50ms timeout add its ID to visibleIds. Apply CSS transition: opacity 0→1 + translateY(-8px)→0 based on membership in visibleIds. This creates a smooth drop-in effect for new items prepended to the list.
6.5 Live Alert Generation (in page.tsx)
•	Initial alerts generated from active_targets that are Critical, High, or lack ADS-B
•	setInterval every 3500ms picks a random target from active_targets, picks a random message template from LIVE_MESSAGES array, creates a new RiskAlert, prepends to alerts state, slices to max 20 items
•	Message templates include: trajectory deviation, profiler recalibration, restricted corridor warning, transponder loss, commander acknowledge

7. Component: Center Map Column
7.1 Target Roster Strip
A thin horizontal strip above the map that lists all active target IDs as clickable buttons.
•	Container: rounded-lg, glassmorphic panel style, flex items-center gap-2 px-3 py-2
•	'Tracks:' label — font-mono, uppercase, tracking-widest, color #334155
•	Each target button: font-mono, text-xs, transition-all. When selected: background is RISK_COLORS[risk_level] at 13% opacity, border is RISK_COLORS at 38% opacity, text is full RISK_COLORS. When unselected: background rgba(30,41,59,0.6), border rgba(255,255,255,0.06), text #64748b
•	Small colored dot (1.5×1.5, rounded-full) in RISK_COLORS before the ID
•	Right side: small hint text 'Click marker to select · Drag to pan' in #1e293b
7.2 AirspaceMap Wrapper (components/airspace-map.tsx)
This is a thin 'use client' wrapper that uses next/dynamic to load AirspaceMapClient with SSR disabled. During loading it shows a dark panel with 'Initializing geospatial engine...' in muted mono text.
const AirspaceMapClient = dynamic(
  () => import('./airspace-map-client').then(m => m.AirspaceMapClient),
  { ssr: false, loading: () => <LoadingPlaceholder /> }
)
Props passed through: targets, selectedId, onSelectTarget, onDeselect.
7.3 AirspaceMapClient (components/airspace-map-client.tsx)
This is the core map engine. It must be 'use client'. It initialises a Leaflet map instance once in a useEffect with empty deps.
7.3.1 Map Initialisation
•	Container ref: mapContainerRef applied to a div that fills the parent
•	L.map(containerRef.current, { center: [19.0, 72.85], zoom: 12, zoomControl: false, attributionControl: false })
•	Tile layer: L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', { className: 'map-dark-tile' })
•	CSS on .map-dark-tile: filter: invert(100%) hue-rotate(180deg) brightness(95%) contrast(90%) — this achieves the military slate aesthetic
•	L.control.zoom().addTo(map) is NOT added — custom zoom can be built separately or omitted
•	Click on empty map area fires onDeselect() callback
•	Map ref stored in mapInstanceRef.current; cleanup on unmount calls map.remove()
7.3.2 No-Fly Zone Polygon
•	L.polygon(NO_FLY_ZONE, { color: '#f43f5e', fillColor: '#f43f5e', fillOpacity: 0.12, weight: 2, dashArray: '6 4' })
•	bindTooltip with permanent: true, direction: 'center', custom HTML: monospace span showing 'NO-FLY ZONE 3' in rose
•	.nfz-tooltip CSS class strips all Leaflet default tooltip chrome (background: transparent, border: none, box-shadow: none)
7.3.3 Animated Trajectory System
Trajectories are not static — they grow in real-time. State: animatedTrajectories: Record<string, [number, number][]>.
•	Initialise from target.trajectory on mount
•	setInterval every 1500ms: for each target, compute a new point from the last point offset by (speed * 0.0000003 * 10) in both lat and lng (with slight random drift)
•	Append new point to the array; if length > 12 shift() the oldest point — creates a sliding window tail
•	This is the real-time movement simulation driving both marker position and polyline shape
7.3.4 Marker & Polyline Rendering
Both markers and polylines are managed imperatively via Leaflet refs (markersRef and polylinesRef as Map<string, L.Marker/L.Polyline>).
Polyline per target
•	Color = RISK_COLORS[target.risk_level]
•	Weight: 2 if selected, 1 if not. Opacity: 0.9 if selected, 0.45 if not
•	dashArray: '4 3'
•	On re-render: call polyline.setLatLngs(animatedTrajectory) and polyline.setStyle() — avoids recreating the layer
Marker per target
•	Icon created by createFlightIcon(classification, riskColor, isSelected) which returns L.divIcon
•	Size: 36×36 if selected, 28×28 if not. Anchor at center (size/2, size/2)
•	SVG paths per classification (see 7.3.5)
•	On re-render: marker.setLatLng(target.coords) + marker.setIcon(icon) — no recreation
•	On first create: marker.on('click', ...) calls onSelectTargetRef.current(target); L.DomEvent.stopPropagation(e) prevents map click deselect
•	bindTooltip: custom HTML card showing id (in risk color), classification + speed, ADS-B status color
7.3.5 SVG Icon Shapes per Classification
•	Drone: center circle (r=3) + four arms to corner circles (r=2.5) — quadcopter top-down silhouette
•	Bird: curved wing path + small center circle — M3 12 C6 8, 10 6, 12 8 C14 6, 18 8, 21 12
•	Aircraft / default: filled star/arrow polygon — M12 2 L15 9 L22 9 L16 14 L18 21 L12 17 L6 21 L8 14 L2 9 L9 9 Z
•	All SVG elements use riskColor for stroke/fill, with 33-hex alpha for fills
•	drop-shadow filter applied: '0 0 6px {riskColor}' when selected, '0 0 3px {riskColor}88' when not
7.3.6 Scan-Line Overlay
•	Absolutely positioned div over the map (pointer-events-none, z-10)
•	CSS: background linear-gradient repeating horizontal lines — creates a subtle CRT scan-line effect
background: linear-gradient(to bottom, transparent 50%, rgba(34,211,238,0.015) 50%)
backgroundSize: 100% 4px
7.3.7 Corner Bracket Decorations
•	Four absolutely positioned divs at top-left, top-right, bottom-left, bottom-right corners
•	Each is 20×20px with 2px border on two sides only (border-t + border-l, etc.) in #22d3ee at 60% opacity
•	pointer-events-none, z-20, creates tactical HUD framing aesthetic
7.3.8 Callback Ref Pattern
onSelectTarget and onDeselect are stored in refs (onSelectTargetRef, onDeselectRef) updated in a useEffect. This prevents the map event listeners created once in the initialisation useEffect from going stale — critical for correct behaviour.

8. Component: RightSidebar
File: components/right-sidebar.tsx | Props: { target: AirTarget | null; onConfirm: (targetId: string) => void }
Renders as <aside className='flex flex-col gap-3 h-full overflow-y-auto'> with thin scrollbar styling. Contains four sub-panels, all glassmorphic.
8.1 Panel 1 — Target Detail Card
8.1.1 Header Row
•	Crosshair icon (lucide) + 'TARGET DETAIL' label — cyan, font-mono, text-xs, tracking-widest, uppercase
8.1.2 Empty State
When target is null: centered Crosshair icon (size 24, color #1e293b) + 'No target selected' text. No panic state — stays calm.
8.1.3 Populated State
•	Target ID: text-xl, font-mono, font-bold, tracking-widest, color #f1f5f9
•	Risk badge: positioned right of ID. Background: RISK_COLORS[risk_level] at 10% opacity. Border: RISK_COLORS at 25% opacity. Text: full RISK_COLORS. Rounded-sm pill.
•	Stat rows (implemented as StatRow sub-component): label on left (font-mono, uppercase, tracking-widest, #475569), value on right (font-mono, font-semibold, accent color). Separated by bottom border rgba(255,255,255,0.06).
◦  CLASS: target.classification — white
◦  SPEED: '{speed} kts' — cyan #22d3ee
◦  TRANSPONDER: 'ON' in green #4ade80 or 'OFF' in rose #f43f5e
◦  CONFIDENCE: '{confidence}%' — orange #fb923c
◦  COORDS: '{lat}°N, {lng}°E' — slate #94a3b8, shown at bottom
8.2 Panel 2 — Micro-Doppler Visualiser
8.2.1 Header
•	Zap icon + 'MICRO-DOPPLER' label — cyan
•	Right side: classification type label — 'HIGH-FREQ PERIODIC' for Drone, 'LOW-FREQ ERRATIC' for Bird, 'SMOOTH SINUSOID' for Aircraft. Color #475569.
8.2.2 Empty State
A dark box (h-[72px]) displaying '— NO SIGNAL —' centered in muted mono text when no target selected.
8.2.3 DopplerCanvas Component
A canvas element (width=280, height=72) rendered via React ref. Uses requestAnimationFrame loop. Key mounted with target.id so canvas fully re-mounts when switching targets.
Canvas rendering — per frame
•	ctx.clearRect(0, 0, W, H) — full clear
•	Draw horizontal grid lines: ctx.strokeStyle rgba(34,211,238,0.05), lineWidth 1, every H/4 pixels
•	Create linear gradient (left to right): rgba(34,211,238,0) → rgba(34,211,238,0.9) → rgba(34,211,238,0) for fade-in/out edges
•	Apply ctx.shadowColor = '#22d3ee', ctx.shadowBlur = 6 for glow
•	Advance timeRef.current += (isDrone ? 0.12 : 0.04) per frame
•	Draw waveform path across all x pixels 0..W
Waveform formulas by classification
•	Drone (high-frequency periodic — rotor blade modulation): y = H/2 + sin(p*2π*6 + t) * H*0.28 + sin(p*2π*3 + t*1.3) * H*0.1 + random*H*0.04 where p = x/W
•	Bird (erratic, low-frequency flapping): y = H/2 + sin(p*2π*1.5 + t) * H*0.2 * (1 + 0.5*sin(p*4π + t*0.7)) + random*H*0.35
•	Aircraft (smooth, low-noise): y = H/2 + sin(p*2π*2 + t) * H*0.15 + sin(p*2π*0.5 + t*0.5) * H*0.05
8.2.4 Frequency Labels
•	'0 Hz' on left, '5 kHz' (Drone) or '500 Hz' (other) on right — font-mono, text-xs, color #334155
8.3 Panel 3 — Commander XAI Box
High-contrast orange-accented card.
background: rgba(251,146,60,0.06)
border: 1px solid rgba(251,146,60,0.25)
minHeight: 180px
8.3.1 Header
•	Bot icon + 'COMMANDER XAI' — orange #fb923c, font-mono, uppercase, tracking-widest
•	'AUTO' badge on right: orange tinted pill
8.3.2 XAI Message Display
The xaiText is generated by getXAIRecommendation(target) function in lib/airspace-data.ts. Four tiers:
•	Critical: 'THREAT ASSESSMENT: Object {id} classified as {classification} moving at {speed} kts. Transponder {ON|OFF}. Confidence: {confidence}%. RECOMMENDATION: Intercept and neutralize immediately. Activate Protocol SIGMA-7.'
•	High: 'ELEVATED RISK: Object {id} is a {classification} at {speed} kts with transponder {ACTIVE|INACTIVE}. Confidence: {confidence}%. RECOMMENDATION: Deploy surveillance drone and alert sector command.'
•	No ADS-B (any risk): 'ADVISORY: Object {id} is moving at {speed} kts with transponder OFF. Classification: {classification} ({confidence}% confidence). Monitor trajectory and prepare intercept vector.'
•	Nominal / Low / has ADS-B: 'NOMINAL: Object {id} — {classification} at {speed} kts. Transponder {ACTIVE|OFFLINE}. Confidence: {confidence}%. No immediate action required.'
Display in a scrollable inner box: background rgba(15,23,42,0.5), border rgba(251,146,60,0.15), font-mono, text-xs, leading-relaxed, color #d1d5db.
8.3.3 Confirm Recommendation Button
•	Full width, flex row, CheckCircle icon + 'CONFIRM RECOMMENDATION' + ChevronRight icon
•	Active state (target selected): background rgba(251,146,60,0.2), border rgba(251,146,60,0.5), color #fb923c, cursor pointer
•	Disabled state (no target): background rgba(30,41,59,0.5), border rgba(255,255,255,0.06), color #334155, cursor not-allowed
•	Hover: background rises to rgba(251,146,60,0.35) via onMouseEnter/onMouseLeave handlers
•	onClick: calls onConfirm(target.id) — page.tsx handles this by creating a confirmation RiskAlert and prepending to alerts

9. State Management & Real-Time Simulation
9.1 Dashboard State (page.tsx)
•	dashboardState: DashboardState — immutable in this version (targets defined at start, no server fetch)
•	selectedTarget: AirTarget | null — updated by map click or roster strip click
•	alerts: RiskAlert[] — starts empty (set in useEffect to avoid SSR mismatch), grows via live injection
•	isClient: boolean — gates all client-only effects (alert injection, time display)
9.2 Alert Injection Loop
•	Runs only after isClient is true
•	setInterval every 3500ms, counter increments to cycle through all targets
•	Picks random message from LIVE_MESSAGES array of 5 template functions
•	Creates RiskAlert with new Date() timestamp, prepends to alerts, slices to 20
9.3 Target Selection Flow
•	handleSelectTarget(target): sets selectedTarget; map markers and roster strip both reflect selection
•	handleDeselect(): sets selectedTarget to null; triggered by clicking empty map area
•	handleConfirmRecommendation(targetId): creates confirmation INFO alert, prepends to feed
9.4 Trajectory Animation (in AirspaceMapClient)
•	Local state: animatedTrajectories — only lives inside the map component
•	Interval: every 1500ms, computes new point per target based on speed and small random drift
•	Leaflet polylines and markers updated imperatively (no React re-render overhead)

10. Animations & Keyframes
10.1 Global Keyframes (globals.css or page-level <style>)
@keyframes pulse-led {
  0%, 100% { opacity: 1; }
  50%       { opacity: 0.4; }
}

@keyframes blink-border {
  0%, 100% { opacity: 1; }
  50%       { opacity: 0.5; }
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(-10px); }
  to   { opacity: 1; transform: translateY(0);     }
}
10.2 Tailwind Animate
•	animate-pulse — used on Leaflet marker pulse rings (the large glowing halo around selected targets)
•	Custom animation durations via inline style for LED dots and border blinks
10.3 Leaflet Marker Animation
Leaflet markers are DOM elements. When a target is selected, the icon SVG gains a stronger drop-shadow and is re-created at larger size (36px vs 28px). This gives a visual 'focus pulse'. The outer halo effect on the marker is implemented as a CSS animation on a background div rendered inside the DivIcon HTML via the createFlightIcon function.

11. CSS Overrides & Leaflet Styling
11.1 Required Leaflet CSS Import
In the AirspaceMapClient component or globals.css, import leaflet's default stylesheet:
import 'leaflet/dist/leaflet.css'
11.2 Critical Leaflet CSS Overrides
.map-dark-tile {
  filter: invert(100%) hue-rotate(180deg) brightness(95%) contrast(90%);
}
.leaflet-tooltip {
  background: transparent !important;
  border: none !important;
  box-shadow: none !important;
  padding: 0 !important;
}
.nfz-tooltip { background: transparent !important; border: none !important; }
.leaflet-container { background: #0f172a; }
11.3 Scrollbar Styling
/* Global thin scrollbar for sidebar panels */
scrollbar-width: thin;
scrollbar-color: #1e293b transparent;
::-webkit-scrollbar { width: 4px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: #1e293b; border-radius: 2px; }

12. Complete File & Folder Structure
airspace-intel/
├── app/
│   ├── globals.css          ← Tailwind, scrollbar, keyframe definitions
│   ├── layout.tsx           ← Root layout: fonts, body, dark mode
│   └── page.tsx             ← Main orchestrator: state, intervals, layout
├── components/
│   ├── airspace-map.tsx     ← next/dynamic wrapper (no SSR)
│   ├── airspace-map-client.tsx ← Full Leaflet map engine (use client)
│   ├── dashboard-header.tsx ← Top bar: branding, status chips, UTC clock
│   ├── left-sidebar.tsx     ← Agent cards + live alert feed
│   └── right-sidebar.tsx    ← Target detail + Doppler canvas + XAI
├── lib/
│   ├── airspace-data.ts     ← All types, INITIAL_STATE, NO_FLY_ZONE,
│   │                           RISK_COLORS, getXAIRecommendation
│   └── utils.ts             ← cn() helper (clsx + tailwind-merge)
├── public/                  ← Static assets
├── next.config.mjs          ← { output: 'standalone' } or default
├── tailwind.config.ts       ← Extend with custom colors if needed
├── tsconfig.json            ← strict: true, paths: @/*
└── package.json             ← Dependencies listed below

13. package.json Dependencies
13.1 Required dependencies
•	next: ^14.x
•	react: ^18.x
•	react-dom: ^18.x
•	leaflet: ^1.9.x
•	@types/leaflet: ^1.9.x
•	lucide-react: ^0.383.x
•	clsx: ^2.x
•	tailwind-merge: ^2.x
•	typescript: ^5.x
•	tailwindcss: ^4.x
•	postcss: ^8.x
•	autoprefixer: ^10.x

14. Critical Implementation Rules
14.1 SSR & Leaflet
⚠️ CRITICAL — Leaflet + Next.js SSR
Leaflet accesses window/document on import. The AirspaceMapClient component MUST be loaded with next/dynamic and { ssr: false }. Never import Leaflet at the top of any file that could be server-rendered. All Leaflet code lives exclusively in airspace-map-client.tsx.
14.2 Hydration Safety
•	DashboardHeader clock: set time only inside useEffect (not useState initialiser)
•	Alert list: start as empty array, populate in useEffect with isClient gate
•	formatAlertTime(date) must use UTC methods (getUTCHours, etc.) not local time
14.3 Map Imperative Updates
⚠️ IMPORTANT — No React re-renders for map layers
Leaflet markers and polylines must be updated imperatively via marker.setLatLng(), marker.setIcon(), polyline.setLatLngs(), polyline.setStyle(). Never remove and recreate layers on every state change — this causes flicker and loses event listeners. Use markersRef and polylinesRef (Map<string, L.Marker/L.Polyline>) to cache and reuse layer references.
14.4 Callback Staleness
•	Store onSelectTarget and onDeselect in useRef inside AirspaceMapClient
•	Update the refs whenever props change in a separate useEffect
•	Map event listeners (created once) always call the ref.current version — never stale
14.5 Key on DopplerCanvas
•	Render <DopplerCanvas key={target.id} target={target} /> — the key forces full unmount/remount when switching targets, resetting the animation loop cleanly
14.6 Leaflet Cleanup
•	The map initialisation useEffect must return a cleanup that calls map.remove() and sets mapInstanceRef.current = null, markersRef.current.clear(), polylinesRef.current.clear()
•	The trajectory interval must be cleared in its own useEffect cleanup

15. Builder Quick-Reference Cheatsheet
What	From where / Answer
Map tiles	https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png with dark CSS filter
Map center	[19.0, 72.85] zoom 12 — Mumbai region
No-Fly Zone	5-point polygon, rose dashed stroke, permanent tooltip 'NO-FLY ZONE 3'
Drone icon	SVG quad-rotor shape — center circle + 4 arm circles
Bird icon	SVG curved wing path
Aircraft icon	SVG polygon star/arrow shape
Trajectory	Sliding window of last 12 [lat,lng] points; grows every 1500ms
Doppler Drone	High-freq (baseFreq=6) periodic sine with modulation envelope
Doppler Bird	Low-freq (baseFreq=1.5) erratic sine with random noise amp
Doppler Aircraft	Smooth dual-sine (freq 2 + 0.5), minimal noise
XAI text	getXAIRecommendation() in lib/airspace-data.ts — 4 tiers
Alert interval	3500ms, max 20 alerts in state, prepend newest
Trajectory interval	1500ms, max 12 points per target, runs inside AirspaceMapClient
LED Active	Green #4ade80, glow shadow, pulse-led animation
LED Ready	Orange #fb923c, glow shadow, no animation
Confirm action	Creates INFO alert in feed, console.log target ID
