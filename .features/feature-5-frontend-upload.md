# Feature 5: Frontend Scaffold & File Upload

## Goal
Create a React + Vite project with a polished, production-quality file upload experience and API integration layer.

## Dependencies
- Features 1–3 (backend running on port 8000) must be complete.

---

## Files to Create

### 1. Initialize Vite + React project
```bash
cd frontend
npx -y create-vite@latest ./ --template react
npm install
```

### 2. `frontend/vite.config.js`
Configure:
- Proxy `/api` requests to `http://localhost:8000` (so frontend can call `/api/upload` without CORS issues in dev)
- Dev server on port 5173

### 3. `frontend/src/index.css`
**Design system** — a dark, premium design:

**Color palette:**
- Background: `#0a0a0f` (deep dark), `#12121a` (card surface), `#1a1a2e` (elevated surface)
- Primary accent: `#6366f1` (indigo), `#818cf8` (lighter indigo)
- Success: `#10b981` (emerald)
- Warning: `#f59e0b` (amber)
- Danger: `#ef4444` (red)
- Text: `#f1f5f9` (primary), `#94a3b8` (secondary), `#475569` (muted)

**Typography:**
- Import Google Font: `Inter` (weights: 400, 500, 600, 700)
- Base font size: 15px, line-height: 1.6

**Global styles:**
- CSS reset (box-sizing, margin, padding)
- Smooth scrolling
- Custom scrollbar (thin, dark, accent on hover)
- Global transition: `all 0.2s ease`

**Utility classes & card styles:**
- `.card` — glassmorphism card: `background: rgba(255,255,255,0.03)`, `backdrop-filter: blur(12px)`, `border: 1px solid rgba(255,255,255,0.06)`, `border-radius: 16px`, `padding: 24px`
- `.badge` variants: `.badge-success`, `.badge-warning`, `.badge-danger`
- Button styles: primary (indigo gradient), secondary (ghost), with hover glow effects

### 4. `frontend/src/utils/api.js`
API helper functions:

```javascript
const API_BASE = '/api';

export async function uploadStatement(file) {
  const formData = new FormData();
  formData.append('file', file);
  const res = await fetch(`${API_BASE}/upload`, { method: 'POST', body: formData });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function loadSampleData() {
  const res = await fetch(`${API_BASE}/sample`);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function recalculateSummary(transactions) {
  const res = await fetch(`${API_BASE}/recalculate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ transactions })
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function getCategories() {
  const res = await fetch(`${API_BASE}/categories`);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}
```

### 5. `frontend/src/components/FileUpload.jsx`
A drag-and-drop upload zone component.

**Props:** `onUploadComplete(data)`, `onError(message)`

**UI:**
- Large dashed-border dropzone (centered on page)
- Icon: upload cloud icon (use inline SVG)
- Text: "Drag & drop your bank statement CSV" + "or click to browse"
- Supported format note: "Supports .csv files from any bank or credit card"
- **"Try Demo Data"** button below — calls `loadSampleData()` and returns results
- Drag state: border turns indigo, background lightens
- Loading state: spinner/pulse animation while uploading
- Error state: red border, error message displayed

**Behavior:**
- Accept only `.csv` files
- On drop/select → call `uploadStatement(file)` → pass results to `onUploadComplete`
- On "Try Demo" click → call `loadSampleData()` → pass results to `onUploadComplete`
- Show loading spinner during API call
- Show error message on failure

### 6. `frontend/src/App.jsx`
Main application component.

**State:**
- `data` — null initially, set after upload (contains `CategorizeResponse`)
- `error` — error message string

**Render:**
- If `data === null` → show `<FileUpload />` centered on screen with app header
- If `data !== null` → show dashboard (placeholder for Feature 6, just show "Data loaded: X transactions" for now)
- App header: "Statement Categorizer" title + "for Freelance Tech Consultants" subtitle
- "Upload New" button to reset back to upload screen

### 7. `frontend/src/main.jsx`
Standard Vite React entry point — render `<App />`.

---

## Visual Design Notes

The upload screen should feel premium and welcoming:
- Dark background with subtle gradient
- Centered card with glassmorphism effect
- Smooth hover and drag animations
- The "Try Demo Data" button should be clearly visible but secondary to the main upload action
- Loading state should show a smooth animated progress indicator
- Success should transition smoothly to the dashboard view

---

## Acceptance Criteria

- [x] `cd frontend && npm run dev` starts on port 5173
- [x] Upload dropzone renders with drag-and-drop support
- [x] Clicking the zone opens file picker (filtered to `.csv`)
- [x] Dragging a CSV file over the zone changes its visual state
- [x] Dropping a valid CSV triggers upload to backend and returns data
- [x] "Try Demo Data" button loads sample data from backend
- [x] Loading spinner shows during API calls
- [x] Error messages display for invalid files or API failures
- [x] After successful upload, the app transitions to show transaction count
- [x] "Upload New" button resets back to upload screen
- [x] Design is glassy frosted, clean architectural corners (zero dark neon/AI bubble clichés)

## Verification
```bash
# Terminal 1: start backend
cd backend && uvicorn app.main:app --reload --port 8000

# Terminal 2: start frontend
cd frontend && npm run dev
```
Open `http://localhost:5173` — test drag-drop and demo button.

## Git Commit
```bash
git add frontend/
git commit -m "feat(frontend): add Vite + React scaffold with drag-and-drop CSV upload and demo mode"
git push origin candidate-sikandarhussain6858
```
