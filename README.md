# YoLearn Token System - Candidate Implementation

A mini token-based usage system for AI tools implementing quote → hold → usage → settle flow.

## Setup Instructions

### 1. Create Project Structure
```bash
mkdir yolearn-token-sandbox
cd yolearn-token-sandbox
mkdir pricing server server/yolearn server/tokens server/tokens/migrations
```

### 2. Install Dependencies
```bash
cd server
python -m venv .venv
source .venv/bin/activate  
pip install -r requirements.txt
```

### 3. Setup Database
```bash
export DJANGO_SETTINGS_MODULE=yolearn.settings
python manage.py migrate
python manage.py runserver 8000
```

## API Endpoints

### Get Wallet Info
```bash
curl http://localhost:8000/api/wallet
```

### Create Quote
```bash
curl -X POST http://localhost:8000/api/quotes \
  -H "Content-Type: application/json" \
  -d '{"tool": "ppt", "params": {"slides": 5, "include_images": true}}'
```

### Authorize Quote
```bash
curl -X POST http://localhost:8000/api/quotes/{quote_id}/authorize
```

### Record Usage
```bash
curl -X POST http://localhost:8000/api/usage \
  -H "Content-Type: application/json" \
  -d '{
    "quote_id": "{quote_id}",
    "llm_out_1k": 1.2,
    "images_1024": 5
  }'
```

### Settle Quote
```bash
curl -X POST http://localhost:8000/api/quotes/{quote_id}/settle
```

## Demo Flow Examples

### 1. PPT Generation (5 slides with images)
Expected: ~100 tokens quoted, 125 held, final settle ~100

### 2. Short Video (2 minutes HD)
Expected: ~700 tokens consumed

### 3. Live Audio Chat (10 minutes)
Expected: TTS+STT+LLM consumption

## Testing
```bash
python manage.py test tokens
```