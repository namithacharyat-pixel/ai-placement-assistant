# AI Placement Assistant

An AI-powered placement preparation platform that helps students prepare for company-specific interviews through Job Description analysis, Resume Matching, AI-generated MCQs, Coding Assessments, Personalized Study Roadmaps, Performance Analytics, and AI Career Guidance.

---

## Features

### Company Tracking

* Add multiple target companies
* Track interview rounds
* Store company-specific preparation progress

### JD Analysis

* Analyze Job Descriptions using AI
* Extract:

  * Skills
  * Technologies
  * Responsibilities
  * Preparation Topics

### Resume Match

* Compare resume with JD
* Generate match score
* Identify missing skills
* Provide improvement suggestions

### MCQ Assessment

* AI-generated company-specific MCQs
* Multiple difficulty levels
* Topic-based preparation
* Detailed explanations

### Coding Assessment

* AI-generated coding questions
* DSA and SQL support
* Multiple difficulty levels
* Multi-language starter code:

  * Java
  * Python
  * C++
  * C

### AI Code Review

* Analyze submitted solutions
* Evaluate:

  * Correctness
  * Time Complexity
  * Space Complexity
  * Interview Readiness

### Performance Analytics

* Identify strong topics
* Detect weak areas
* Generate improvement recommendations

### Study Roadmap

* Personalized preparation roadmap
* Company-specific learning plans
* Progress tracking

### AI Career Chat

* Interactive AI mentor
* Placement guidance
* Interview preparation support

---

# Technology Stack

## Frontend

* React
* TypeScript
* TanStack Router
* Axios
* Tailwind CSS
* Vite
* Lucide React

## Backend

* Python
* Flask
* Flask-CORS

## AI Layer

* Groq API
* LLM-based Analysis
* Prompt Engineering
* Recommendation Generation
* Adaptive Learning Logic

---

# Project Architecture

AI Placement Assistant

Frontend (React + TypeScript)

↓

Backend (Flask REST APIs)

↓

AI Module

↓

Groq LLM

---

# AI Modules

## jd_analyzer.py

Analyzes Job Descriptions and extracts:

* Skills
* Technologies
* Responsibilities
* Preparation Topics

## resume_matcher.py

Compares Resume and JD.

Generates:

* Match Score
* Missing Skills
* Suggestions

## assessment_generator.py

Generates:

* MCQs
* Coding Questions
* SQL Challenges
* AI Code Reviews
* Learning Recommendations

## roadmap_generator.py

Creates personalized study plans.

## performance_analyzer.py

Analyzes assessment performance and generates recommendations.

## groq_client.py

Handles communication with Groq LLM API.

---

# API Endpoints

## JD Analysis

POST

/api/jd/analyze

---

## Resume Match

POST

/api/resume/analyze

---

## MCQ Generation

POST

/api/assessment/mcq

---

## Coding Question

POST

/api/assessment/coding

---

## AI Code Review

POST

/api/assessment/review

---

## Learning Recommendation

GET

/api/assessment/recommendation/<company>

---

## Performance Analysis

POST

/api/performance/analyze

---

## Study Roadmap

POST

/api/roadmap/generate

---

## AI Chat

POST

/api/chat

---

# Installation

## Clone Repository

```bash
git clone <repository-url>
cd AI-Placement-Assistant
```

## Backend Setup

```bash
cd backend

python -m venv venv

# Windows
venv\Scripts\activate

pip install -r requirements.txt
```

Create a `.env` file:

```env
GROQ_API_KEY=your_groq_api_key
```

Run backend:

```bash
python app.py
```

Backend runs on:

```text
http://127.0.0.1:5000
```

---

## Frontend Setup

```bash
cd frontend

npm install
npm run dev
```

Frontend runs on:

```text
http://localhost:8080
```

---

# Project Workflow

1. Add target company
2. Analyze company JD
3. Generate preparation topics
4. Match resume against JD
5. Take MCQ assessments
6. Solve coding challenges
7. Get AI code review
8. Analyze performance
9. Follow personalized roadmap
10. Improve interview readiness

---

# Why AI?

Traditional placement platforms provide static content.

This project uses AI to:

* Understand company-specific JDs
* Personalize preparation
* Generate adaptive questions
* Review coding solutions
* Recommend next learning topics
* Provide interview guidance

This creates a dynamic and personalized placement preparation experience.

---

# Future Enhancements

* Authentication & User Accounts
* Database Integration
* Judge0 Code Execution
* LeetCode-style Test Cases
* SQL Playground
* RAG-based Learning Memory
* Interview Simulation
* Voice-based AI Mock Interviews

---

# Team Contributions

### Frontend Developer

* React UI
* Routing
* State Management
* User Experience

### Backend Developer

* Flask APIs
* Data Flow
* Business Logic

### AI/ML Developer

* Prompt Engineering
* Groq Integration
* Assessment Generation
* Recommendation Engine

### Integration & Testing

* API Integration
* End-to-End Testing
* Deployment Support

---

# License

Academic Project – AI Placement Assistant
