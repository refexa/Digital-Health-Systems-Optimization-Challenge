# Outpatient Appointment Scheduling Optimization

This project presents a digital workflow redesign for outpatient appointment scheduling. It demonstrates how real-time slot visibility, alternative-slot recommendations, controlled priority booking, capacity management, and operational reporting can improve patient access and healthcare resource utilization.

The project was developed for the Digital Health Systems Optimization Challenge.

## Project Overview

The application models a seven-day outpatient schedule with 30-minute appointment slots. Each slot has a configurable capacity and can contain one or more bookings.

The system supports:

- Patient and staff appointment booking
- Nearest-available slot recommendations when a requested slot is full
- Staff-only priority booking for urgent cases
- Staff-only appointment capacity updates
- Schedule and booking metrics
- CSV export for operational review
- A browser-based scheduling dashboard

## Technology

- Python
- Flask
- SQLite
- HTML, CSS, and JavaScript
- Requests for simulation

## Project Files

| File | Description |
| --- | --- |
| `scheduler_app.py` | Flask application and SQLite-backed scheduling API |
| `ui.html` | Browser dashboard for viewing and managing appointment slots |
| `simulate.py` | Script for generating sample booking activity |
| `requirements.txt` | Python package requirements |
| `SUBMISSION_GUIDE.md` | Submission and validation checklist |
| `refexa_Digital Health System_Challenge.docx` | Completed challenge submission document |
| `generate_submission.py` | Script used to generate the Word submission document |

## Setup

Create and activate a virtual environment, then install the dependencies:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

The application creates `scheduler.db` automatically when it starts. The database contains the default appointment slots if no schedule exists.

## Run the Application

Start the Flask application:

```powershell
python scheduler_app.py
```

Open the dashboard in a browser:

```text
http://127.0.0.1:5000/
```

The default development staff token is `adminpass`. For local testing, it can be replaced with an environment variable:

```powershell
$env:ADMIN_TOKEN = "replace-with-a-local-token"
python scheduler_app.py
```

Do not use the development token or Flask debug mode in a production healthcare environment.

## API Summary

### Public endpoints

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `GET` | `/` | Serves the scheduling dashboard |
| `GET` | `/slots` | Returns slots, capacities, and bookings |
| `POST` | `/book` | Books an available slot or returns an alternative |
| `GET` | `/metrics` | Returns slot and booking metrics |

### Staff endpoints

Staff endpoints require the `X-Admin-Token` request header.

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `POST` | `/book_priority` | Creates or preempts a booking according to priority |
| `POST` | `/set_capacity` | Updates the capacity of a slot |
| `GET` | `/export` | Downloads the schedule as CSV |

Example booking request:

```powershell
Invoke-RestMethod -Method Post `
	-Uri http://127.0.0.1:5000/book `
	-ContentType "application/json" `
	-Body '{"slot_id":"2026-09-11T09:00:00","patient":"Example Patient"}'
```

The exact `slot_id` should be obtained from `GET /slots` because generated slot dates depend on when the database is initialized.

## Run a Booking Simulation

With the application running in another terminal:

```powershell
python simulate.py
```

The simulation submits sample booking requests against randomly selected slots and prints each response. It can be used to observe successful bookings and full-slot recommendations.

## Workflow Design

The redesigned workflow follows this sequence:

1. The patient or staff member requests an appointment.
2. The system checks live slot capacity.
3. If the requested slot is full, the system identifies the nearest available alternative.
4. The booking is confirmed and stored with its timestamp and priority.
5. Staff can manage urgent cases and capacity changes through protected endpoints.
6. Managers can review metrics and export schedule data for operational analysis.

This design aims to reduce manual searching, improve access to available capacity, support consistent priority decisions, and provide better information for day-to-day scheduling management.

## Evaluation Measures

A pilot evaluation should compare the redesigned workflow with a documented baseline using measures such as:

- Median time from appointment request to confirmation
- Time required to resolve a full-slot request
- Percentage of full-slot requests receiving an alternative
- Appointment capacity utilization
- Unused-slot rate
- Staff handling time
- Patient satisfaction and access-related complaints
- Traceability of priority and capacity changes

The impact figures in the accompanying submission document are proposed pilot targets, not measured clinical outcomes.

## Security and Privacy Considerations

This is a local prototype and is not production-ready for protected health information. A production deployment would require authenticated user accounts, role-based access control, encrypted transport and storage, audit logging, secure secret management, input validation, privacy review, and integration with approved clinical systems.

Use fictional patient names only during local testing.

## Submission Deliverable

The challenge deliverable is a single professionally formatted document covering:

1. Healthcare workflow analysis
2. Digital workflow redesign
3. Impact assessment

The prepared Word document is named:

`refexa_Digital Health System_Challenge.docx`

It can be exported to PDF if required by the submission portal.
