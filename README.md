# Docker-based Model Runner for AWS CloudWatch Log Analysis

- Conversational CloudWatch is a FastAPI-based microservice for analyzing and summarizing CloudWatch-style logs.  
- It supports both **Deterministic summarization** (local sample logs) and **LLM-powered** summarization (via Ollama), packaged in Docker Compose for easy deployment.


### Features

 - /health_status – Verify service health

 - /query – Ask log-analysis questions via prompt

 - /recipes/{name} – Run pre-defined analyses (e.g., error_spikes, slow_queries)

 - Dual summarization paths: **deterministic local mode** or **LLM mode** (`USE_LLM=true`)

- Natural-language summarization via TinyLlama (Ollama model runner)

- Fully containerized with Docker Compose

### Architecture Overview
**System Diagram (Figure 2)**

![System Diagram](/docs/fig2_system_architecture.png)

### Architecture Overview Summary
- The Conversational CloudWatch v1.1.0 platform is composed of a modular FastAPI framework with Guardrails verification, fare separation of components, and local LLM summarization with Ollama.  
- The Docker Compose connects the app (FastAPI API) and ollama (TinyLlama model runner) containers, provides safety in processing the input, confirms that the startup succeeded (`Health check OK - API responding normally), and the ability to repeat locally.

Docker Compose orchestrates both:
 - conversational-cloudwatch-app (FastAPI)
 - ollama (TinyLlama model runner)


### Environment & Prerequisites
```
|  Requirements              |                          Version / Notes**
|  --------------------------|---------------------------------------------------
|  macOS 14 / Windows 11     |                        Tested environments
|  Python	                   |                        3.12+
|  Docker Desktop	           |                        ≥ 29.0.1
|  Docker Compose	           |                        ≥ v2.29
|  Optional	                 |                        AWS CLI / LocalStack (for real AWS testing)
```

### Project 
```
conversational-cloudwatch/
│
├── app/
│   ├── main.py
|   |──guardrails.py
│   ├── adapters.py
│   ├── summarizer.py
│   ├── mcp_client.py
│   └── recipes/
│       ├── error_spikes.py
│       └── slow_queries.py
│       └── traffic_summary.py
├── docs/
│   ├── BLOG_DRAFT.md
│   ├── ARCHITECTURE.md
│   ├── IAM_DRAFT.md
│   ├── Screenshots/
│   │   ├── health_status.png
│   │   ├── error_spikes_llm.png
│   │   ├── slow_queries.png
|   |
│   │──convocloud_architecture.png
│   └── fig2_runtime_flow.png
│
├── .env
├── .dockerignore
├── .gitignore
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── README.md
```

### How It Works (Runtime Flow – Figure 2)

- User sends request to /query or /recipes/{name}

- FastAPI validates input and checks mode (`USE_LLM=true/false`)  

- Adapter retrieves **deterministic local sample logs**, **LocalStack logs**, or **real AWS logs** (if configured)  

- Summarizer generates insights:
  - deterministic summarizer when `USE_LLM=false`
  - TinyLlama LLM summarizer when `USE_LLM=true`

- Response returned with request_echo, raw_events, and summary

### Setup & Run
**Clone the Repository**
```
git clone https://github.com/Brianmurgor44/conversational-cloudwatch.git
cd conversational-cloudwatch
```

## Build & Start Containers
```
docker compose up -d --build
```

### Follow Logs (service names)
```
docker compose logs -f app
docker compose logs -f ollama
```

### Expected startup output
```
INFO: Conversational CloudWatch starting — v1.1.0 | mode=LLM
INFO: Health check OK — API responding normally (startup)
INFO: Application startup complete.
```
- Open Swagger UI → http://localhost:8001/docs

### Troubleshooting
```
| Symptom                | Fix                                                     |
| ---------------------- | ------------------------------------------------------- |
| `/version` → Not Found | Rebuild; ensure port 8001 is published.                 |
| No startup logs        | Use "docker compose logs -f app".                       |
| Model not ready        | "docker compose logs -f ollama" until it reports ready. |
```

### Docker Compose (current)
```
version: "3.9"

services:
  app:
    build: .
    ports:
      - "${PORT:-8001}:8001"
    env_file:
      - .env
    depends_on:
      ollama:
        condition: service_started
    command: >
      uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
    restart: unless-stopped

  ollama:
    image: ollama/ollama:latest
    ports:
      - "11434:11434"
    volumes:
      - ollama:/root/.ollama
volumes:
  ollama: {}
```
### Environment Variables
- Set in .env or directly under environment: in Compose.

| Variable          | Purpose                                        | Default               |
| ----------------- | ---------------------------------------------- | --------------------- |
| `USE_LLM`         | Toggle deterministic (`false`) vs LLM (`true`) | `false`               |
| `OLLAMA_BASE_URL` | Model runner URL                               | `http://ollama:11434` |

- Examples (curl will show the mode under /version).

### Verify Installation
```
curl -s http://localhost:8001/health_status | jq
```
Expected output:

```
{"status": "ok"}
```
```
curl -s http://localhost:8001/version | jq
```
Expected output

```
{"app":"Conversational-Cloudwatch","versions":"1.1.0","mode":"LLM"}
```

## Example Usage

 ###  Health Check 
 ```
curl -s http://localhost:8001/health_status | jq
```

###  Error Spikes (LLM Mode)
```
curl -s "http://localhost:8001/recipes/error_spikes?log_group=/aws/lambda/auth-service&time_range=2h&mock=false" | jq
```

###  Slow Queries (Deterministic Mode)
```
curl -s "http://localhost:8001/recipes/slow_queries?log_group=/aws/lambda/auth-service&time_range=4h&mock=true" | jq
```

###  Freeform /query
```
curl -s -X POST http://localhost:8001/query \
  -H "Content-Type: application/json" \
  -d '{"recipe":"error_spikes","prompt":"errors last 15m","time_range":"15m"}' | jq
```

 ###  Guards enforced

- Max prompt length: ≤ 300 chars

- Time range: ^\d+[smhd]$ (e.g., 15m, 2h, 7d)


## Sample Output
```
{
  "summary": "Window size: 5 events; error-like 4 (80%). Spikes at 03:33Z and 03:35Z. Top reasons: GatewayTimeout (40%), Expired token (20%). Affected users: dave, erin."
}
```

## Testing & Results
```
| Endpoint                | Mode                                | Output                             |
| ----------------------- | ---------                           | ---------------------------------- |
| `/health_status`        | –                                   | Status OK                          |
| `/version`              | App metadata (version, mode, model) | version and model
| `/query` (mock=false)`  | Natural LLM summary                 | Natural LLM summary                |
| `/recipes/slow_queries` | Structured count + insights summary | Real LLM summarization             |
```

## Limitations & Future Work

- Currently uses deterministic local sample logs / LocalStack(full AWS verification pending)

- IAM policy prepared but not fully tested

- Limited LLM context size (TinyLlama model)

- Future: integrate AWS CloudWatch Boto3 add /history endpoint (persist sumaries to SQLite/JSON)
- Optional GCP or Render cloud deployment for public demo


##  License

- MIT License – Free to use for educational and research purposes.

## Quick Demo
Run everything locally:
```
docker compose up -d --build
```

Check status
```
curl -s http://localhost:8001/health_status | jq .
```

Check version:
```
curl -s http://localhost:8001/version | jq .
```

Run a sample query:
```
curl -s -X POST http://localhost:8001/query \
  -H "Content-Type: application/json" \
  -d '{"prompt": "error_spikes", "mock": false}' | jq
  ```
  Expected: natural language summary generated by TinyLlama ( when USE_LLM=true)

  --------------------------
### Contributing 
 ---------------------------

 Contributions are welcome. Open an issue, suggest features, or submit pull requests.

 ---------------------------

Developed by Brian Murgor

--------------------------

## References & Credits
- Amazon Web Services. (n.d.). Amazon CloudWatch Logs — User Guide. Retrieved from https://docs.aws.amazon.com/
- FastAPI. (n.d.). FastAPI documentation - Retrieved from https://fastapi.tiangolo.com/
- Docker. (n.d.). Docker documentation- Retrieved   https://docs.docker.com/
- LocalStack. (n.d.). LocalStack documentation - Retrieved from https://docs.localstack.cloud/
- Uvicorn. (n.d.). Uvicorn documentation -  Retrieved from https://www.uvicorn.org/
- Pydantic. (n.d.). Pydantic v2 documentation -  Retrieved from https://docs.pydantic.dev/

