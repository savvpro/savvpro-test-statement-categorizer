# Frontend - Statement Categorizer UI

Next.js-based web interface for uploading and categorizing transactions.

## Quick Start

```bash
# Install dependencies
npm install

# Set up environment
copy .env.local.example .env.local

# Run development server
npm run dev
```

Visit http://localhost:3000

## Building for Production

```bash
# Build optimized bundle
npm run build

# Start production server
npm start
```

## Features

- CSV file upload with validation
- Automatic transaction categorization
- Manual category editing
- Real-time summary updates
- Color-coded categories
- Responsive design

## Project Structure

```
frontend/
├── src/
│   ├── pages/
│   │   ├── index.tsx        # Main page
│   │   └── _app.tsx         # App wrapper
│   └── styles/
│       ├── globals.css      # Global styles
│       └── Home.module.css  # Page-specific styles
├── public/                  # Static assets
├── package.json
├── tsconfig.json
└── next.config.js
```

## Environment Variables

Create `.env.local`:

```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## Technology Stack

- **Framework:** Next.js 14
- **Language:** TypeScript
- **Styling:** CSS Modules
- **HTTP Client:** Axios
- **Linting:** ESLint
