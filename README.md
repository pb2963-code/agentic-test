# Health Monitoring Platform

A comprehensive multi-agent health monitoring platform for patients and consumers. This platform uses an intelligent agent-based architecture to provide personalized health monitoring, insights, and recommendations.

## Features

### Multi-Agent System
The platform employs six specialized AI agents that work together:

- **Vital Signs Agent**: Monitors heart rate, blood pressure, temperature, oxygen saturation, and respiratory rate. Detects anomalies and analyzes trends.

- **Medication Agent**: Manages medication schedules, tracks doses, checks for drug interactions, and monitors adherence.

- **Symptom Analysis Agent**: Records symptoms, detects patterns, correlates with other health data, and provides risk assessments.

- **Wellness Agent**: Tracks physical activity, sleep, nutrition, mood, and daily steps. Sets and monitors wellness goals.

- **Alert Agent**: Generates and manages health alerts, handles notifications, and coordinates emergency responses.

- **Coordinator Agent**: Orchestrates all agents, aggregates insights, and provides unified health summaries and recommendations.

### Core Capabilities

- **Real-time Health Monitoring**: Track vital signs and receive instant alerts for anomalies
- **Medication Management**: Never miss a dose with intelligent reminders and interaction warnings
- **Symptom Tracking**: Log symptoms and get AI-powered pattern analysis
- **Wellness Tracking**: Monitor activities, sleep, nutrition, and mood
- **Smart Alerts**: Receive prioritized health alerts with actionable recommendations
- **Personalized Insights**: Get health recommendations based on your data

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     Health Monitoring Platform                    │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │
│  │   Frontend  │  │   REST API  │  │  Database   │              │
│  │  Dashboard  │◄─┤   FastAPI   │◄─┤   SQLite    │              │
│  └─────────────┘  └──────┬──────┘  └─────────────┘              │
│                          │                                        │
│  ┌───────────────────────┴────────────────────────┐              │
│  │              Agent Orchestrator                 │              │
│  └───────────────────────┬────────────────────────┘              │
│                          │                                        │
│  ┌───────────────────────┴────────────────────────┐              │
│  │                   Event Bus                     │              │
│  └───────────────────────┬────────────────────────┘              │
│                          │                                        │
│  ┌─────────┬─────────┬───┴───┬─────────┬─────────┐              │
│  │ Vital   │ Meds    │Symptom│ Wellness│ Alert   │              │
│  │ Agent   │ Agent   │ Agent │ Agent   │ Agent   │              │
│  └────┬────┴────┬────┴───┬───┴────┬────┴────┬────┘              │
│       └─────────┴────────┴────────┴─────────┘                    │
│                          │                                        │
│  ┌───────────────────────┴────────────────────────┐              │
│  │             Coordinator Agent                   │              │
│  │    (Orchestration, Insights, Recommendations)   │              │
│  └─────────────────────────────────────────────────┘              │
└─────────────────────────────────────────────────────────────────┘
```

## Installation

### Prerequisites

- Python 3.10+
- Node.js 18+
- npm or yarn

### Backend Setup

```bash
# Clone the repository
cd health-monitoring-platform

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -e .

# Or install with dev dependencies
pip install -e ".[dev]"
```

### Frontend Setup

```bash
cd frontend
npm install
```

## Running the Application

### Start the Backend

```bash
# From the project root
python -m src.main

# Or using uvicorn directly
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`

API Documentation:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

### Start the Frontend

```bash
cd frontend
npm run dev
```

The dashboard will be available at `http://localhost:3000`

## API Endpoints

### Patients
- `POST /api/patients` - Register a new patient
- `GET /api/patients` - List all patients
- `GET /api/patients/{id}` - Get patient details
- `PATCH /api/patients/{id}` - Update patient
- `DELETE /api/patients/{id}` - Delete patient

### Vital Signs
- `POST /api/vitals` - Record a vital reading
- `GET /api/vitals/{patient_id}` - Get vital history
- `GET /api/vitals/{patient_id}/latest` - Get latest vitals
- `GET /api/vitals/{patient_id}/trends` - Get vital trends

### Medications
- `POST /api/medications` - Add medication
- `GET /api/medications/{patient_id}` - Get medications
- `POST /api/medications/dose` - Record dose
- `GET /api/medications/{patient_id}/adherence` - Get adherence

### Symptoms
- `POST /api/symptoms` - Report symptom
- `GET /api/symptoms/{patient_id}` - Get symptoms
- `GET /api/symptoms/{patient_id}/analysis` - Get analysis
- `POST /api/symptoms/{id}/resolve` - Resolve symptom

### Wellness
- `POST /api/wellness/activity` - Log activity
- `POST /api/wellness/sleep` - Log sleep
- `POST /api/wellness/mood` - Log mood
- `POST /api/wellness/steps` - Log steps
- `GET /api/wellness/{patient_id}/daily` - Daily summary
- `GET /api/wellness/{patient_id}/weekly` - Weekly summary

### Alerts
- `GET /api/alerts/{patient_id}` - Get alerts
- `POST /api/alerts/{id}/acknowledge` - Acknowledge alert
- `POST /api/alerts/{id}/resolve` - Resolve alert
- `POST /api/alerts/emergency` - Trigger emergency

### Dashboard
- `GET /api/dashboard/{patient_id}` - Get dashboard data
- `GET /api/dashboard/{patient_id}/summary` - Get health summary
- `GET /api/dashboard/{patient_id}/risk` - Get risk assessment

## Agent Communication

Agents communicate through two mechanisms:

1. **Event Bus**: Publish-subscribe system for loose coupling
   - Agents publish events (e.g., `VITAL_ANOMALY`, `MEDICATION_MISSED`)
   - Other agents subscribe and react to relevant events

2. **Message Passing**: Direct communication for request-response
   - Supports priorities: LOW, NORMAL, HIGH, URGENT, CRITICAL
   - Includes correlation IDs for tracking responses

## Health Context

Each patient has a `HealthContext` that aggregates:
- Current vital readings
- Active symptoms
- Active alerts
- Risk levels
- Recent insights
- Recommendations

Agents share and update this context for coordinated care.

## Development

### Running Tests

```bash
pytest tests/
```

### Code Formatting

```bash
black src/
ruff check src/
```

### Type Checking

```bash
mypy src/
```

## Configuration

Configuration is managed through `config/settings.py`. Key settings:

- `DATABASE_PATH`: SQLite database location
- `API_HOST`, `API_PORT`: API server settings
- `DEBUG`: Enable debug mode

Environment variables can override defaults.

## Security Considerations

For production deployment:

1. Enable authentication (JWT, OAuth2)
2. Use HTTPS only
3. Configure CORS properly
4. Encrypt sensitive data
5. Implement rate limiting
6. Set up proper logging and monitoring

## License

MIT License

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests
5. Submit a pull request
