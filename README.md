# Job Scheduler – Distributed Task Platform

A production-inspired distributed job scheduling platform for reliably executing asynchronous background jobs across workers. The platform allows users to create projects and queues, submit jobs, monitor workers, handle failures with retries, manage dead-letter jobs, and monitor system health through a web dashboard.

---

# 🚀 Features

## Authentication and Project Management

- User authentication
- Organization and project management
- Multiple job queues per project

## Queue Management

- Create and manage job queues
- Configure queue concurrency
- Configure retry policies
- Pause and resume queues
- Monitor queue activity and statistics

## Job Management

The platform supports:

- Immediate jobs
- Delayed jobs
- Background job execution
- Job status monitoring
- Job execution history
- Worker assignment tracking

## Retry and Failure Handling

Failed jobs are automatically retried based on the configured retry policy.

Supported retry behavior includes configurable retry attempts and backoff strategies.

Jobs that permanently fail after exhausting retries are moved to the Dead Letter Queue.

## Dead Letter Queue

The Dead Letter Queue allows users to:

- View permanently failed jobs
- Inspect job failure information
- Review retry history
- Manually retry failed jobs

## Worker Management

Workers are responsible for polling queues and executing jobs.

The dashboard provides information about:

- Worker health
- Worker status
- Worker heartbeats
- Running job capacity
- Worker activity

## Metrics and Monitoring

The application provides system observability through:

- Total jobs
- Success rate
- Average execution time
- Throughput
- Worker health information
- Job status information

---

# 🏗️ System Architecture

```text
                        ┌─────────────────┐
                        │      User       │
                        └────────┬────────┘
                                 │
                                 ▼
                        ┌─────────────────┐
                        │ Web Dashboard   │
                        │    Frontend     │
                        └────────┬────────┘
                                 │ REST API
                                 ▼
                        ┌─────────────────┐
                        │   Backend API   │
                        │ Job Scheduler   │
                        └────────┬────────┘
                                 │
                                 ▼
                        ┌─────────────────┐
                        │    Database     │
                        │ Jobs & Queues   │
                        └────────┬────────┘
                                 │
                                 ▼
                        ┌─────────────────┐
                        │   Job Queues    │
                        └────────┬────────┘
                                 │
                    ┌────────────┼────────────┐
                    │            │            │
                    ▼            ▼            ▼
              ┌──────────┐ ┌──────────┐ ┌──────────┐
              │ Worker 1 │ │ Worker 2 │ │ Worker N │
              └────┬─────┘ └────┬─────┘ └────┬─────┘
                   │            │            │
                   └────────────┼────────────┘
                                │
                                ▼
                        ┌─────────────────┐
                        │  Job Execution  │
                        └────────┬────────┘
                                 │
                    ┌────────────┴────────────┐
                    │                         │
                    ▼                         ▼
             ┌─────────────┐            ┌─────────────┐
             │  Completed  │            │   Failed    │
             └─────────────┘            └──────┬──────┘
                                               │
                                               ▼
                                        ┌─────────────┐
                                        │ Retry Logic │
                                        └──────┬──────┘
                                               │
                              ┌────────────────┴────────────────┐
                              ▼                                 ▼
                        Retry Job                        Retries Exhausted
                              │                                 │
                              ▼                                 ▼
                        Execute Again                    Dead Letter Queue
```

---

# 🔄 Job Lifecycle

A successful job follows this lifecycle:

```text
Queued → Claimed → Running → Completed
```

A failed job follows this lifecycle:

```text
Queued → Claimed → Running → Failed → Retrying → Running
                                               ↓
                                    Retries Exhausted
                                               ↓
                                      Dead Letter Queue
```

---

# 🛠️ Getting Started

## Prerequisites

Make sure the following software is installed:

- Docker
- Docker Compose

## Clone the Repository

```bash
git clone <your-repository-url>
cd <project-folder>
```

## Start the Application

Build and start all services:

```bash
docker compose up --build
```

To run the application in the background:

```bash
docker compose up --build -d
```

To stop the application:

```bash
docker compose down
```

After the application starts successfully, open the frontend URL configured in your project in a browser.

---

# 🧪 Testing the Application

## 1. Test an Immediate Job

Go to:

```text
Projects → Select Project → Select Queue → View Jobs
```

Click:

```text
Submit Job
```

Use:

```text
Handler name: echo
Type: Immediate
Payload: {}
```

Expected result:

```text
Queued → Running → Completed
```

---

## 2. Test a Delayed Job

Submit a job with:

```text
Handler name: echo
Type: Delayed
Delay: 60 seconds
Payload: {}
```

Expected result:

```text
Scheduled / Queued
        ↓
Wait for configured delay
        ↓
Running
        ↓
Completed
```

---

## 3. Test Retry Handling

Submit a failing job:

```text
Handler name: always_fail
Type: Immediate
Payload: {}
```

Expected result:

```text
Attempt 1 → Failed
     ↓
Retry
     ↓
Attempt 2 → Failed
     ↓
Retry
     ↓
Attempt 3 → Failed
     ↓
Retries Exhausted
     ↓
Dead Letter Queue
```

The retry delay follows the retry policy configured for the queue.

---

## 4. Test the Dead Letter Queue

Open:

```text
Dead Letter Queue
```

Verify that the permanently failed `always_fail` job appears.

Check:

- Failure status
- Retry count
- Error details
- Job execution history

---

## 5. Test Manual Retry from Dead Letter Queue

Click the:

```text
Retry
```

button for a failed job.

Expected result:

```text
Dead Letter Queue
        ↓
Queued / Running
        ↓
Job executes again
```

---

## 6. Test Queue Pause and Resume

### Pause the queue

Go to:

```text
Projects → Select Project → Select Queue
```

Click:

```text
Pause
```

Submit an `echo` job.

Expected result:

```text
Job remains Queued
```

The worker should not process the job while the queue is paused.

### Resume the queue

Click:

```text
Resume
```

Expected result:

```text
Queued → Running → Completed
```

---

## 7. Test Worker Monitoring

Open:

```text
Workers
```

Verify that the dashboard displays:

- Healthy workers
- Unhealthy workers
- Stopped workers
- Worker heartbeat information
- Running job capacity

---

## 8. Test Metrics

Open:

```text
Metrics
```

Verify that the system displays information such as:

- Total jobs
- Success rate
- Average execution time
- Throughput
- Job processing activity

---

# 📊 Dashboard Pages

| Page | Description |
|---|---|
| Overview | Displays overall system health and summary information |
| Projects | Manage projects and job queues |
| Job Explorer | Submit, inspect, and monitor jobs |
| Workers | Monitor worker status and heartbeats |
| Dead Letter Queue | Inspect and retry permanently failed jobs |
| Metrics | Monitor system performance and throughput |

---

# 🗃️ Core System Components

The platform consists of the following major components:

```text
Frontend
    │
    ▼
REST API
    │
    ├── Authentication
    ├── Project Management
    ├── Queue Management
    ├── Job Management
    └── Monitoring APIs
    │
    ▼
Database
    │
    ├── Users
    ├── Organizations
    ├── Projects
    ├── Queues
    ├── Jobs
    ├── Job Executions
    ├── Workers
    ├── Worker Heartbeats
    └── Dead Letter Entries
    │
    ▼
Workers
    │
    ├── Poll Queues
    ├── Claim Jobs
    ├── Execute Jobs
    ├── Send Heartbeats
    └── Handle Retries
```

---

# 🔒 Reliability Features

The system is designed with reliability in mind and includes:

- Background job processing
- Worker-based execution
- Job retry handling
- Retry limits
- Dead Letter Queue support
- Worker health monitoring
- Job execution history
- Queue pause and resume
- Metrics and observability

---

# 📸 Tested Functionality

The following functionality was successfully tested during development:

- [x] Organization and project management
- [x] Queue creation and management
- [x] Immediate job execution
- [x] Delayed job execution
- [x] Worker processing
- [x] Worker health monitoring
- [x] Retry mechanism
- [x] Failed job handling
- [x] Dead Letter Queue
- [x] Manual retry from Dead Letter Queue
- [x] Queue pause functionality
- [x] Queue resume functionality
- [x] Job execution history
- [x] System metrics
- [x] Throughput monitoring

---

# 🔮 Future Improvements

The following features can be added in future versions:

- Cron-based recurring jobs
- Job dependencies and workflows
- Rate limiting
- Distributed locking
- Queue sharding
- Event-driven execution
- WebSocket live updates
- Role-based access control
- Advanced alerting and notifications
- AI-generated failure summaries
- Horizontal worker auto-scaling

---

# 👨‍💻 Author

**Manickam Bhoobesh**

---

# 📝 Project Summary

This project demonstrates the design and implementation of a production-inspired distributed job scheduling platform.

The application focuses on:

- Backend engineering
- Database-driven job management
- Asynchronous background processing
- Worker monitoring
- Retry and failure handling
- Dead Letter Queue management
- Queue control
- System observability
- Full-stack dashboard implementation

The project prioritizes reliability, maintainability, modular design, and observability over feature quantity.