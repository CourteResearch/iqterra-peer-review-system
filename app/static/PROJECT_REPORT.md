# IQT-02 Moodle Peer-Review Platform

## 1. Project Overview

The IQT-02 Moodle Peer-Review Platform is a prototype web application designed to support peer assessment. It provides a dashboard, student and submission APIs, an allocation engine, and a peer-review workflow backed by persistent database storage.

The current implementation is a development prototype. Full Moodle integration, authentication, and production deployment are future implementation stages.

## 2. Objectives

- Provide a web-based dashboard for peer-review activities.
- Support student registration and submission management through API endpoints.
- Allocate peer reviews while preventing self-review and reciprocal reviewer pairs.
- Distribute review assignments as evenly as possible.
- Allow reviewers to submit scores and written feedback.
- Store and retrieve submitted reviews.
- Validate core functionality using automated tests.

## 3. Technology Stack

- **Python:** application programming language.
- **FastAPI:** web framework and API development.
- **Uvicorn:** local application server.
- **HTML, CSS and JavaScript:** dashboard interface and browser interactions.
- **SQLite:** persistent storage used by the working review workflow.
- **PostgreSQL:** planned database option represented by the project's SQL schema and Docker configuration.
- **Pytest:** automated testing.
- **Figma:** interface design and dashboard prototyping.

## 4. System Architecture

The application is organised into the following main components:

- `app/main.py` — FastAPI application, routes and request validation.
- `app/database.py` — database tables and database operations.
- `app/allocation.py` — peer-review allocation logic.
- `app/static/index.html` — dashboard interface and peer-review panel.
- `tests/test_allocation.py` — allocation algorithm tests.
- `tests/test_health.py` — health endpoint and dashboard tests.
- `database/` — database-related files and SQL schema.

The browser communicates with the FastAPI application through HTTP requests. The application validates requests, interacts with the database, and returns responses to the dashboard.

## 5. Implemented Features

### 5.1 Dashboard

The dashboard is served locally through FastAPI and provides an interface for accessing peer-review functionality.

### 5.2 Health Endpoint

The `/health` endpoint returns a JSON response indicating that the application is running.

### 5.3 Student and Submission APIs

The application includes endpoints for registering students and managing submissions.

### 5.4 Review Allocation

The allocation engine assigns reviewers to submissions and includes checks against self-review and reciprocal reviewer pairs. Automated tests also check allocation balance.

### 5.5 Peer Review Centre

The dashboard includes controls to load allocations, select an allocation, enter a score between 0 and 100, provide written feedback, submit a review, and refresh the list of saved reviews.

### 5.6 Persistent Storage

Submitted reviews are saved to the application's database and remain available after the FastAPI server is restarted. This persistence was verified during development.

## 6. Testing and Verification

The following checks were completed during development:

- The dashboard opens in the browser.
- The health endpoint returns `{"status":"ok"}`.
- The API documentation is accessible through `/docs`.
- Automated tests pass: 9 passed.
- The review submission workflow accepts a valid test review.
- Submitted reviews appear in the review list.
- A saved review remains available after restarting the application.

These results verify the tested prototype functionality. They do not constitute a production security assessment or verification of live Moodle integration.

## 7. Running the Application

From the project root, activate the virtual environment if necessary and run:

```powershell
python -m uvicorn app.main:app --reload
```

Open the following addresses:

- Dashboard: http://127.0.0.1:8000/
- Health endpoint: http://127.0.0.1:8000/health
- Interactive API documentation: http://127.0.0.1:8000/docs

To run the automated tests:

```powershell
python -m pytest -v
```

## 8. Limitations and Future Work

The current version is a development prototype and should not be exposed publicly or used with real student data without appropriate security controls.

Further work includes:

1. Integrating Moodle through a maintained LTI 1.3 library.
2. Implementing and validating LTI launch authentication.
3. Adding required Names and Role Provisioning Services (NRPS) and Assignment and Grade Services (AGS) functionality, where required by the specification.
4. Implementing authenticated roles and access controls.
5. Completing moderation and approval workflows.
6. Configuring and testing PostgreSQL deployment and tenant isolation.
7. Improving error handling, security testing, accessibility and deployment documentation.
8. Testing the system against the complete assignment requirements.

## 9. Conclusion

The project currently demonstrates a functioning peer-review prototype with a browser dashboard, API endpoints, a review allocation engine, persistent review storage, and automated tests. The next development phase is to complete the remaining integration and security requirements and validate the solution against the formal IQT-02 assignment specification.