# Docker-based Model Runner for AWS CloudWatch Log Analysis

## 1. Overview

The Conversational CloudWatch Log Analysis system is a containerized microservice designed to ingest, summarize, and interpret AWS-style CloudWatch logs using a conversational AI interface.

It supports:

- Deterministic mode → uses local sample logs for repeatable, offline testing  


- LLM mode → natural-language summarization powered by TinyLlama via Ollama

The architecture focuses on modularity, simplicity, and safe experimentation with LLM summarization of log data.

##  2. Core Components
```
Component	                                                                Description
--------------------------------------------------------------------------------------------------------------------
FastAPI App (main.py)                             |        Handles REST endpoints (/health_status, /query, /recipes) and routes requests.

Adapters (adapters.py)	                          |       Fetches log events (deterministic, LocalStack, or real AWS) and converts them into structured objects. |

Summarizer (summarizer.py)	                      |   Provides deterministic summaries or LLM summaries via the Ollama TinyLlama model.

Recipes (app/recipes/)	                          |      Predefined log-analysis routines such as error_spikes and slow_queries.

Ollama Model Runner	                              |     Serves the local TinyLlama model on port 11434, generating human-readable insights.

Docker Compose	                                  |      Orchestrates both containers: conversational-cloudwatch-app and ollama.

Docs Folder	                                      |       Contains documentation, screenshots, architecture diagrams, and Markdown reports.
```

## 3. System Architecture (Figure 1)

![System Diagram](./convocloud_architecture.png)


### Description

- **User Interface (Swagger UI, CLI, or cURL)**  
  → Sends requests to the FastAPI container on port `8001`.

- **FastAPI App (main.py)**  
  → Validates requests, applies guardrails (prompt length, time range), and routes to the correct recipe.

- **Adapters Layer**  
  → Retrieves deterministic local logs, LocalStack logs, or real AWS logs (read-only IAM)

- **Summarizer Layer**  
  → Uses deterministic summarization unless `USE_LLM=true`, in which case it invokes TinyLlama via Ollama.

- **Docker Network**  
  → Connects both containers seamlessly (`app` ↔ `ollama`)

## 4. Data Flow (Figure 2)
![System Diagram](/docs/fig2_system_architecture.png)

*Figure 2 – Request-to-response data flow in Conversational CloudWatch v1.1.0.*

The diagram  traces how each request moves through the system’s internal layers:

1. **User Request**  
   - A POST or GET request is sent to `/query`, `/version`, or `/recipes/{name}` via Swagger UI or cURL.  
   - The FastAPI container receives the request on port `8001`.

2. **Guardrails Validation**  
   - Checks prompt length (≤ 300 characters) and time-range pattern (`^\d+[smhd]$`).  
   - Enforces `USE_LLM` and `mock` mode flags.  
   - Invalid inputs immediately trigger descriptive HTTP 400 errors.

3. **Adapter Fetch**  
   - Loads deterministic local sample logs  LocalStack logs  
   - or real AWS CloudWatch logs (when configured properly)  
   - Converts raw entries into structured `LogEvent` objects.

4. **Summarization Process**  
   - The summarizer analyzes events and detects patterns such as spikes or slow queries.  
   - If `USE_LLM=true`, it calls the Ollama container on port `11434` to generate natural-language summaries (TinyLlama model).  
   - Otherwise, returns  a deterministic summary for local development

5. **Response Construction**  
   - The API returns a structured JSON response:  
     ```json
     {
       "request_echo": {...},
       "raw_events": [...],
       "summary": "Human-readable log analysis result."
     }
     ```
   - A startup log message confirms service readiness:  
     `Health check OK — API responding normally (startup)`

6. **Docker Bridge Networking**  
   - Docker Compose links both containers (`app` and `ollama`) under one shared network.  
   - Internal communication occurs securely without manual port mapping. 

## 5. Architecture Summary

- The Conversational CloudWatch v1.1.0 architecture combines modular FastAPI services, input guardrails, a local make-up of the LLM model, and a harmonious Docker-orchestrated system into a response.  
- Figure 1 shows the user requests going through verified endpoints, and Figure 2 explains the overall flow of data between the input and the summarized insights.

- The system makes the separation of validation, data retrieval, and summarization, thereby maintaining transparency, safety and flexibility in the different environments.  
   Guardrails validation imposes time and range safety before accessing a summarizer, and Docker Compose ensures the separation and interconnectedness of the execution of the FastAPI service (app) and the Ollama container (ollama).  

- When the application is launched, it records a single brief message
- At health OK (API responding normally (startup))  
reporting the verification of the successful start without noisy periodical tests.

- This architecture offers a clean base of actual AWS CloudWatch integration, expansion of the LLM model, and further extensions like persistence (/history), and cloud deployment.

This flow ensures all requests follow a transparent and validated path — from input to insight — with safe Guardrails validation and deterministic or LLM-driven outputs.

## 6. Key Endpoints
```

| Endpoint                | Method | Description                                                                  |
| ----------------------- | ------ | ---------------------------------------------------------------------------- |
| /health_status         | GET    | Returns service health (`{"status": "ok"}`)                                  |
| /version               | GET    | Shows app name, version, and mode (Mock or LLM)                              |
| /query                 | POST   | Accepts `prompt`, `log_group`, and `time_range` — returns summarized results |
| /recipes/error_spikes  | GET    | Detects authentication or service error spikes                         |
| /recipes/slow_queries  | GET    | Detects DB latency and timeout patterns                  |

```


## 7. Deployment Architecture (Docker)
**Container Overview**
```

| Container                       | Image                  | Port    | Role                       |
| ------------------------------- | ---------------------- | ------- | -------------------------- |
| conversational-cloudwatch-app   | Local build (FastAPI)  |  8001   | API & summarizer           |
| ollama`                         | ollama/ollama:latest`  |  11434  | Model runner for TinyLlama |

```


## Docker Compose Highlights
```
version: "3.9"
services:
  app:
    build: .
    ports:
      - "8001:8001"
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
**Notes:**

- FastAPI container (app) runs the main API service.
- Ollama container serves the TinyLlama model locally.
- Both communicate internally on the Docker network (conversational-cloudwatch_default).

## 8. IAM and Security Integration

(Linked with IAM_DRAFT.md)

- Uses read-only CloudWatch permissions (logs:GetLogEvents, logs:FilterLogEvents).
- Optional S3 write access for summaries.
- Future integration with Guardrails AI to ensure safe LLM responses.
- Environment variables stored securely in .env or Secrets Manager.

## 9. Future Improvements
```

| Area                | Enhancement                                             |
| ------------------- | ------------------------------------------------------- |
| AWS Integration     | Connect real CloudWatch data via Boto3 Client           |
| LLM Expansion       | Support multiple Ollama models (phi3, mistral, etc.)    |
| UI Layer            | Add Streamlit or React dashboard for live visualization |
| Alerting           | Integrate SNS for anomaly notifications                 |
| Security            | Add role-based authentication and stricter sanitization |

```

## 10. Summary

The Conversational CloudWatch architecture demonstrates a practical, modular design for LLM-based log summarization.
Its Dockerized foundation supports deterministic local development as well as fully LLM-powered summarization.
The system is ready for future expansion to real AWS CloudWatch data, multiple model runners, and cloud deployment environments.