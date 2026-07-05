# ResumeForge

AI-powered Overleaf CV tailoring platform. Upload your master LaTeX CV, add job links, and generate truthful, role-specific tailored versions with fit scoring, ATS analysis, and downloadable HTML reports.

## Features

- **Overleaf LaTeX upload** — preserves your design, fonts, and folder structure
- **Single job tailoring** — diff review, fit score, ATS analysis, STAR methodology
- **Bulk campaigns** — process 100+ job URLs with batch dashboard
- **Job crawling** — tiered fetch (aiohttp + JSON-LD extraction), manual fallback
- **AI Instruction Studio** — global and per-section instructions with prompt refiner
- **Evidence-first editing** — no invented credentials, employers, or metrics
- **HTML reports** — downloadable fit, ATS, gaps, and change analysis

## Quick Start

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Set OPENAI_API_KEY in .env
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
cp .env.local.example .env.local
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

### Docker

```bash
export OPENAI_API_KEY=your-key
docker compose up --build
```

## Reference LaTeX Structure

See `Resume_latex/` for the expected project layout:

```
Resume/
├── resume.tex
├── _header.tex
├── sections/
│   ├── objective.tex
│   ├── skills.tex
│   ├── experience.tex
│   ├── education.tex
│   └── activities.tex
└── TLCresume.sty
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/cvs/upload` | Upload LaTeX ZIP |
| POST | `/api/tailor` | Single job tailoring |
| POST | `/api/batches` | Create bulk campaign |
| POST | `/api/crawl` | Extract job description |
| POST | `/api/prompt/refine` | Refine AI instructions |
| POST | `/api/reports/html` | Download HTML report |

## Design

Dark navy glassmorphism UI inspired by premium AI developer tools, with teal/emerald accents, DM Sans typography, and feature-first architecture.

## Tests

```bash
cd backend && pytest tests/ -v --cov=app --cov-report=term-missing
```
