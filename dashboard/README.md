# Trading Assistant Dashboard

Next.js admin dashboard for monitoring the real-time stock screener.

## Features

- Real-time alerts from screener
- Alert statistics and charts
- Symbol search and filtering
- Mobile-responsive design

## Setup

1. Install dependencies:
```bash
npm install
```

2. Create `.env.local`:
```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_SUPABASE_URL=your_supabase_url
NEXT_PUBLIC_SUPABASE_ANON_KEY=your_anon_key
```

3. Run development server:
```bash
npm run dev
```

4. Open http://localhost:3000

## Tech Stack

- Next.js 14 (App Router)
- TypeScript
- Tailwind CSS
- Recharts (charting)
- Supabase (real-time subscriptions)
