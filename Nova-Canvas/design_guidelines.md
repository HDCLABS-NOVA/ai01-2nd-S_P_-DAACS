# Transformers Platform - Design Guidelines

## Design Approach
**System**: Linear + VS Code inspired developer tool aesthetic
**Rationale**: Utility-focused development platform requiring clarity, information density, and professional polish. Drawing from modern development tools (Linear, Cursor, GitHub Codespaces) for familiar, efficient workflows.

---

## Core Design Principles

### Typography
- **UI Text**: Inter or System UI font family
  - Headers: 600 weight, 24-32px
  - Body: 400 weight, 14-16px
  - Labels: 500 weight, 12-14px
- **Code/Technical**: JetBrains Mono or Fira Code
  - Code blocks: 14px
  - Console output: 13px

### Layout System
**Spacing Primitives**: Use Tailwind units of **2, 3, 4, 6, 8, 12, 16**
- Tight spacing (p-2, p-3): UI controls, buttons, badges
- Medium spacing (p-4, p-6): Card padding, section gaps
- Large spacing (p-8, p-12, p-16): Page sections, major divisions

**View1 Layout**:
- Centered container: max-w-3xl
- Vertical centering in viewport
- Input area: Large textarea with subtle border
- CTA button: Prominent, centered below input

**View2 Layout** (Three-column):
```
[Interaction Console: 320px] [Workspace: flex-1, min 400px] [Preview: flex-1, min 500px]
```
- Use `grid grid-cols-[320px_1fr_1fr]` on desktop
- Collapsible panels with resize handles
- Mobile: Stack vertically (Console → Workspace → Preview)

---

## Component Library

### View1 Components
1. **Hero Input Area**
   - Large textarea (min-h-48)
   - Placeholder: "프로젝트를 설명해주세요..."
   - Rounded corners (rounded-lg)
   - Subtle focus state
   
2. **Primary CTA**
   - "시작하기" button
   - Large size (px-8 py-4, text-lg)
   - Full-width on mobile, auto-width on desktop

### View2 Components

**Interaction Console** (Left Panel):
- Chat message bubbles:
  - User messages: Right-aligned, distinct background
  - NOVA messages: Left-aligned, subtle background
  - Timestamp: Small text below each message
- Input bar: Fixed at bottom with send button
- Auto-scroll to latest message

**Workspace** (Center Panel):
- Vertical navigation menu (full-height)
- Menu items with icons:
  - Overview/Plan (document icon)
  - Logs (clock icon)
  - API (connection icon)
  - Structure (folder tree icon)
  - Settings (gear icon)
  - Code Library (code brackets icon)
- Active state: Background highlight + left border accent
- Expandable tree view for nested items

**Preview** (Right Panel):
- Top toolbar: Description text + action buttons
- Main area: Iframe or live preview container
- Bottom status bar: "Last updated" timestamp

### Shared Components
- **Code Blocks**: 
  - Syntax highlighted
  - Line numbers (optional toggle)
  - Copy button (top-right)
  - Language badge (top-left)
  
- **Modal/Drawer**:
  - Semi-transparent backdrop
  - Slide-in from right for Code Library details
  - Close button + ESC key support

- **Buttons**:
  - Primary: Solid background
  - Secondary: Border only
  - Sizes: sm (px-3 py-2), md (px-4 py-3), lg (px-6 py-4)
  - Icons: 16px for sm, 20px for md, 24px for lg

- **Form Inputs**:
  - Consistent height (h-10 for standard)
  - Rounded borders (rounded-md)
  - Clear focus states (ring)

---

## Visual Hierarchy

**View1**:
1. Input area (primary focus)
2. CTA button (strong visual weight)
3. Optional: Subtle background pattern or gradient

**View2**:
1. Preview panel (largest visual area)
2. Interaction Console (high engagement)
3. Workspace menu (utilitarian, clean)

**Information Density**:
- Workspace: Compact spacing (gap-2, gap-3)
- Console: Comfortable reading (gap-4, gap-6)
- Preview: Breathing room (p-6, p-8)

---

## Interaction Patterns

### State Transitions
- View1 → View2: Smooth fade transition
- Panel resizing: Smooth drag with visual feedback
- Message updates: Gentle fade-in for new messages
- Preview updates: Loading state before re-render

### Loading States
- Skeleton screens for code blocks
- Spinner for NOVA responses
- Progress bar for file operations

### Accessibility
- Keyboard navigation for all panels (Tab, Arrow keys)
- ARIA labels for icon-only buttons
- Focus indicators (ring-2) on all interactive elements
- High contrast mode support

---

## Specific Features

**Plan Modification UI**:
- Editable sections with inline edit button
- Diff view showing changes (green additions, red deletions)
- "Restore previous version" link in Logs

**Code Library**:
- Grid of code snippets (2 columns on desktop)
- Each card: Filename, language, preview (3 lines), copy button
- Click opens detailed view in drawer/modal

**Login**:
- Minimal login form (top-right corner or dedicated page)
- User avatar + name display when logged in
- Dropdown menu for logout/settings

---

## Layout Refinements

- **Panel Headers**: Fixed height (h-12 or h-14), flex items-center
- **Dividers**: Use 1px borders, subtle opacity
- **Scrollable Areas**: Custom scrollbar styling (thin, subtle)
- **Tooltips**: Small (text-xs), appear on hover (200ms delay)

This design creates a professional, efficient development environment where NOVA and users collaborate seamlessly through clear visual communication and intuitive workflows.