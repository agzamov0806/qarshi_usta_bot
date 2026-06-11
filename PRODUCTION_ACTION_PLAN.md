# Production Readiness Action Plan
## Qarshi Usta Bot — 1000+ Concurrent Users

**Current Status:** 65/100 Ready  
**Target Status:** 95/100 Ready for 1000+ users  
**Timeline:** 12-15 days (2 sprints)

---

## EXECUTIVE SUMMARY

**What's Working:** Database pooling, graceful shutdown, rate limits, Telegram backoff (65%)  
**What's Broken:** N+1 queries, MemoryStorage, no circuit breaker, no load testing (35%)  
**Blocker for 1000 Users:** N+1 queries (limits to ~100 orders/sec, need 400+)  
**Time to Ready:** 12 days with parallel work

---

## SPRINT 1: Critical Path (Days 1-7)

### TASK 1.1: Fix N+1 Queries (CRITICAL)
**Owner:** Backend Lead  
**Estimated Effort:** 3-4 days  
**Start:** Day 1 (parallel with 1.2)  
**Deliverable:** Query optimization + performance test

#### 1.1.1 Audit Phase (4 hours)
- Identify all handlers making sequential DB queries
- Use `EXPLAIN ANALYZE` to profile slow queries
- Create spreadsheet: handler → current queries → optimized queries

**Example Candidates:**
- `cb_order_reject_usta` (lines 1863-1875): 2 queries
- `reject_reason_received` (lines 1914-1916): 1 query
- `cb_admin_assign_order`: 2 queries per iteration

#### 1.1.2 Optimization Phase (2-3 days)
**Patterns to Fix:**

Pattern 1: Separate SELECT queries
```python
# BEFORE (2 queries)
async with get_session_factory()() as session:
    su = await session.get(SectionUsta, suid)           # Query 1
    order = await orders_repo.get_order(session, oid)   # Query 2

# AFTER (1 query via JOIN)
stmt = select(SectionUsta, Order).join(Order, ...).where(...)
result = await session.execute(stmt)
su, order = result.tuple()
```

Pattern 2: Multiple lookups in loop
```python
# BEFORE (N queries)
for item_id in item_ids:
    item = await session.get(Item, item_id)  # N queries
    # use item

# AFTER (1 query with IN clause)
items = await session.execute(
    select(Item).where(Item.id.in_(item_ids))
)
items_by_id = {item.id: item for item in items}
for item_id in item_ids:
    item = items_by_id[item_id]  # No query
```

Pattern 3: Create order + get details separately
```python
# BEFORE (2 queries)
order_id = await create_order(session, ...)
order = await get_order(session, order_id)  # Re-fetch

# AFTER (1 query, already have object)
order = Order(...)
session.add(order)
await session.commit()
# Use order object directly (no refresh needed)
```

#### 1.1.3 Testing Phase (1 day)
- Unit tests for each optimized function
- Load test with 100 concurrent users (5 min sustained)
- Measure: query count, response time, DB CPU

**Success Criteria:**
- Queries/second: 100-150 (down from 200-300)
- Response time: <500ms p95 (down from 2-3s)
- DB CPU: <40% (down from 100%)
- Error rate: <0.1%

#### Files to Modify
- `/packages/db/repositories/orders.py` — Add bulk query methods
- `/services/bot/handlers/orders.py` — Use optimized methods
- Consider creating new helper methods:
  ```python
  async def get_order_with_usta(session, order_id):
      """Single query with eager load."""
      ...
  ```

**Acceptance Criteria:**
- [ ] 20+ handlers audited for N+1
- [ ] All identified patterns refactored
- [ ] Load test passes at 100 users
- [ ] Query count < 150 qps baseline

---

### TASK 1.2: Load Testing Infrastructure (HIGH)
**Owner:** QA/DevOps Lead  
**Estimated Effort:** 2-3 days  
**Start:** Day 1 (parallel with 1.1)  
**Deliverable:** Load test suite + baseline metrics

#### 1.2.1 Tool Selection & Setup (4 hours)
**Recommended: Locust** (Python native, easy to write)
```bash
pip install locust
mkdir -p tests/load
touch tests/load/locustfile.py
```

#### 1.2.2 Write Test Scenarios (1 day)

**Scenario 1: Order Creation Flow**
```python
@task(weight=50)
class OrderCreationScenario(HttpUser):
    wait_time = between(1, 3)
    
    def on_start(self):
        # /start with Telegram user
        self.tg_user_id = random.randint(1000, 9999999)
    
    @task
    def create_order(self):
        # Simulate: /start → location → problem → finalize
        # 3-5 sequential requests
        ...
```

**Scenario 2: Rate Limit Stress**
```python
@task
def burst_messages(self):
    # Send 20 messages in rapid succession
    # Measure: how many accepted, latency
    ...
```

**Scenario 3: Admin Flow**
```python
@task(weight=5)
def admin_notify(self):
    # Simulate admin accepting/rejecting orders
    ...
```

#### 1.2.3 Baseline Test (1 day)
**Test Profile:**
- 100 concurrent users
- Ramp-up: 2 minutes (10 users/sec)
- Duration: 5 minutes sustained
- Workload: 50% order creation, 30% status checks, 20% admin

**Metrics to Capture:**
```
Response Time (p50, p95, p99):
  - Order creation: target <500ms
  - Status check: target <200ms
  - Admin action: target <1s

Error Rate:
  - Target: <0.1%

Throughput:
  - Orders/sec: measure actual

Resource Usage:
  - DB connections used
  - Memory growth
  - CPU usage
```

**Output: Baseline Report**
```
100 Users, 5 min sustained:
  - Successful requests: 25,000
  - Error rate: 0.05%
  - p95 latency: 450ms
  - p99 latency: 2.3s
  - Orders/sec: ~75
  - DB connections: 42/50
```

#### Files to Create
- `tests/load/locustfile.py` — Main Locust test
- `tests/load/scenarios.py` — Reusable test classes
- `tests/load/config.yml` — Test configuration
- `tests/load/results/baseline_100_users.json` — Baseline results

**Acceptance Criteria:**
- [ ] Locust installed and working
- [ ] 3+ scenarios written and passing
- [ ] Baseline test completed at 100 users
- [ ] Results documented

---

### TASK 1.3: Implement Basic Circuit Breaker (HIGH)
**Owner:** Backend Lead  
**Estimated Effort:** 2-3 days  
**Start:** Day 3 (after N+1 audit done)  
**Deliverable:** Circuit breaker pattern in session layer

#### 1.3.1 Design (4 hours)

**States:**
- **CLOSED** (normal): Pass all requests through
- **OPEN** (failing): Reject requests immediately
- **HALF_OPEN** (recovering): Allow 1 probe request, wait for success

**Triggers:**
- Open: 5 consecutive connection failures
- Close: 10 successful requests in HALF_OPEN
- Probe timeout: 30 seconds

#### 1.3.2 Implementation (1-2 days)

**File: `packages/db/session_circuit_breaker.py`** (new)
```python
from enum import Enum
from datetime import datetime, timedelta

class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"

class DatabaseCircuitBreaker:
    def __init__(self):
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None
    
    async def check_state(self):
        if self.state == CircuitState.OPEN:
            if datetime.now() - self.last_failure_time > timedelta(seconds=30):
                self.state = CircuitState.HALF_OPEN
                self.success_count = 0
        
        if self.state == CircuitState.OPEN:
            raise CircuitBreakerOpenError("Database circuit breaker open")
    
    def record_success(self):
        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= 10:
                self.state = CircuitState.CLOSED
                self.failure_count = 0
        elif self.state == CircuitState.CLOSED:
            self.failure_count = 0
    
    def record_failure(self):
        self.failure_count += 1
        self.last_failure_time = datetime.now()
        if self.failure_count >= 5:
            self.state = CircuitState.OPEN

# Global instance
_circuit_breaker = DatabaseCircuitBreaker()

async def get_session_with_fallback():
    await _circuit_breaker.check_state()
    try:
        session = get_session_factory()()
        await _circuit_breaker.record_success()
        return session
    except Exception as e:
        _circuit_breaker.record_failure()
        raise
```

**Integration Points:**
1. Wrap in `get_session()` calls
2. Add fallback handler for CircuitBreakerOpenError
3. Return cached response or queue order for retry

#### 1.3.3 Testing (4 hours)
- Unit test: state transitions
- Integration test: circuit opens after 5 failures
- Integration test: circuit closes after 30s + 10 successes

#### Files to Create/Modify
- `packages/db/session_circuit_breaker.py` (new)
- `packages/db/session.py` (import circuit breaker, wrap calls)
- `services/bot/handlers/orders.py` (handle CircuitBreakerOpenError)

**Acceptance Criteria:**
- [ ] Circuit breaker module created
- [ ] State transitions working
- [ ] Integrated into order handlers
- [ ] Unit tests passing
- [ ] Load test shows graceful degradation on DB failure

---

### TASK 1.4: Monitoring Setup (MEDIUM)
**Owner:** DevOps Lead  
**Estimated Effort:** 1 day  
**Start:** Day 4 (after circuit breaker)  
**Deliverable:** Prometheus metrics + Grafana dashboard

#### 1.4.1 Add Prometheus Metrics (4 hours)

**File: `packages/metrics.py`** (new)
```python
from prometheus_client import Counter, Gauge, Histogram

# Database
db_pool_size = Gauge('db_pool_size', 'Current pool size')
db_pool_overflow = Counter('db_pool_overflow_hits', 'Overflow connection uses')
db_query_duration = Histogram(
    'db_query_duration_seconds',
    'DB query duration',
    buckets=(0.01, 0.05, 0.1, 0.5, 1.0)
)

# Rate limiting
rate_limit_hits = Counter(
    'rate_limit_hits_total',
    'Rate limit hits',
    ['user_id']
)

# Circuit breaker
circuit_breaker_state = Gauge(
    'circuit_breaker_state',
    'Circuit breaker state (0=closed, 1=open, 2=half_open)'
)
circuit_breaker_failures = Counter('circuit_breaker_failures_total', 'CB failures')

# Telegram
telegram_send_duration = Histogram(
    'telegram_send_duration_seconds',
    'Telegram message send time'
)
telegram_retries = Counter('telegram_retries_total', 'Telegram retry count')

# Orders
orders_created = Counter('orders_created_total', 'Orders created')
orders_failed = Counter('orders_failed_total', 'Order creation failures')
```

#### 1.4.2 Export Endpoint (2 hours)

**File: `services/api/main.py`** (modify)
```python
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from fastapi import Response

@app.get("/metrics")
async def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
```

#### 1.4.3 Grafana Dashboard (2 hours)
- JSON dashboard template
- Panels: pool utilization, query latency, error rate, circuit breaker state

**Acceptance Criteria:**
- [ ] Metrics collected and exported
- [ ] /metrics endpoint working
- [ ] Grafana dashboard created
- [ ] Alerts configured for pool exhaustion

---

## SPRINT 2: Scale & Hardening (Days 8-15)

### TASK 2.1: Redis Migration (URGENT)
**Owner:** Backend Lead  
**Estimated Effort:** 4 days  
**Start:** Day 8  
**Deliverable:** RedisStorage FSM + distributed rate limiting

#### 2.1.1 Setup Redis (1 day)

**docker-compose.yml** (add service)
```yaml
redis:
  image: redis:7-alpine
  container_name: usta_redis
  ports:
    - "6379:6379"
  volumes:
    - redis_data:/data
  command: redis-server --appendonly yes
```

**requirements.txt** (add)
```
redis>=5.0.0
aioredis>=2.0.0
```

#### 2.1.2 FSM Migration (2-3 days)

**File: `services/bot/main.py`** (replace MemoryStorage)
```python
from aiogram.fsm.storage.redis import RedisStorage
from redis.asyncio import Redis

async def run_bot():
    # Create Redis connection
    redis = Redis.from_url("redis://localhost:6379/0")
    
    # Use RedisStorage instead of MemoryStorage
    storage = RedisStorage(redis=redis)
    
    bot = Bot(token=settings.bot_token)
    dp = Dispatcher(storage=storage)
    dp.include_router(router)
    
    # ... rest of polling ...
    
    await redis.close()  # Cleanup
```

**Testing:**
- State persistence across bot restarts ✅
- State cleanup on timeout ✅
- Memory usage: confirm <10 MB at 1000 users ✅

#### 2.1.3 Distributed Rate Limiting (1-2 days)

**File: `services/bot/update_middleware.py`** (replace MemoryStorage)
```python
from redis.asyncio import Redis

class RedisRateLimitMiddleware(BaseMiddleware):
    def __init__(self, redis: Redis):
        self.redis = redis
        self.MAX_MESSAGES_PER_SEC = 10
    
    async def __call__(self, handler, event, data):
        key = _serial_key(event)
        if key is None:
            return await handler(event, data)
        
        redis_key = f"rate_limit:{key}:{int(time.time())}"
        
        # Increment counter for this second
        count = await self.redis.incr(redis_key)
        if count == 1:
            await self.redis.expire(redis_key, 1)  # Expire after 1 second
        
        if count > self.MAX_MESSAGES_PER_SEC:
            # Send feedback...
            return None
        
        return await handler(event, data)
```

#### Files to Modify
- `docker-compose.yml` (add Redis)
- `requirements.txt` (add redis)
- `services/bot/main.py` (RedisStorage)
- `services/bot/update_middleware.py` (RedisRateLimitMiddleware)
- `shared/config.py` (add REDIS_URL setting)

**Acceptance Criteria:**
- [ ] Redis running and accessible
- [ ] FSM state persists across restarts
- [ ] Rate limiting works across multiple instances
- [ ] Memory usage drops to <10 MB

---

### TASK 2.2: Multi-Instance Testing (HIGH)
**Owner:** QA Lead  
**Estimated Effort:** 2 days  
**Start:** Day 10 (after Redis migration)  
**Deliverable:** Verified multi-instance deployment

#### 2.2.1 Deploy 2-3 Bot Instances (1 day)
```bash
# Option 1: Docker Compose (scale service)
docker-compose up -d --scale bot=3

# Option 2: Manual (3 terminals)
python main.py  # Instance 1
python main.py  # Instance 2 (different user)
python main.py  # Instance 3 (different user)
```

#### 2.2.2 Test Scenarios (1 day)
- User A creates order on bot #1
- User B accepts order on bot #2
- Both see consistent state ✅
- State accessible from any instance ✅
- Rate limits shared across instances ✅

#### 2.2.3 Load Test with Multi-Instance (1 day)
- Run 200 user load test across 3 instances
- Measure: throughput, latency, error rate
- Success if no errors beyond single-instance

**Acceptance Criteria:**
- [ ] 3 instances running without conflicts
- [ ] State shared via Redis
- [ ] Load test passes with 200 users
- [ ] No race conditions or inconsistencies

---

### TASK 2.3: Load Test at 500 Users (CRITICAL)
**Owner:** QA Lead  
**Estimated Effort:** 1-2 days  
**Start:** Day 11 (after multi-instance verified)  
**Deliverable:** 500-user performance report

#### 2.3.1 Test Configuration
```
- Concurrent Users: 500
- Ramp-up: 5 minutes (100 users/min)
- Duration: 10 minutes sustained
- Workload mix: same as 100-user test
```

#### 2.3.2 Success Criteria
```
✅ Error rate: <0.5%
✅ p95 latency: <2 seconds
✅ Orders/sec: >150 (was ~75 at 100 users)
✅ DB CPU: <60%
✅ Memory stable (no growth)
✅ No circuit breaker trips
```

#### 2.3.3 Failure Cases (debug if not met)
- If error rate high: Check DB pool, queries
- If latency high: Check N+1 queries still present
- If memory growing: Check for state leaks
- If circuit breaker tripping: Check DB health

#### 2.3.4 Generate Report
- CSV: response times, errors, throughput
- Graph: latency over time, error distribution
- Summary: pass/fail against criteria

**Acceptance Criteria:**
- [ ] 500-user load test completed
- [ ] All success criteria met (or documented failures)
- [ ] Detailed report with graphs
- [ ] Identified any remaining bottlenecks

---

### TASK 2.4: Production Deployment Preparation (MEDIUM)
**Owner:** DevOps Lead  
**Estimated Effort:** 1-2 days  
**Start:** Day 13  
**Deliverable:** Deployment guide + runbook

#### 2.4.1 Deployment Checklist
```
Pre-Deployment:
  [ ] All N+1 queries fixed
  [ ] Circuit breaker integrated
  [ ] Redis configured
  [ ] Load test passed at 500 users
  [ ] Monitoring dashboard live
  [ ] Alerts configured
  [ ] Backups tested
  [ ] Rollback plan documented

Deployment:
  [ ] Database migrations applied
  [ ] Environment variables set
  [ ] Secrets rotated (bot token, admin ID)
  [ ] Healthcheck endpoint verified
  [ ] Graceful shutdown tested

Post-Deployment:
  [ ] Metrics trending normal
  [ ] No error spikes
  [ ] Response times acceptable
  [ ] Database stable
```

#### 2.4.2 Runbook
- How to deploy new version
- How to rollback
- How to scale (add bot instances)
- How to monitor (Grafana links)
- Troubleshooting guide

#### Files to Create
- `DEPLOYMENT_GUIDE.md`
- `RUNBOOK.md`
- `healthcheck.sh`

**Acceptance Criteria:**
- [ ] Deployment checklist complete
- [ ] Runbooks documented
- [ ] Team trained on procedures

---

### TASK 2.5: Spike Testing (MEDIUM)
**Owner:** QA Lead  
**Estimated Effort:** 1 day  
**Start:** Day 14  
**Deliverable:** Spike test report

#### 2.5.1 Spike Scenario
```
- Start at 0 users
- Spike to 500 users in 30 seconds (17 users/sec)
- Hold at 500 for 2 minutes
- Measure: error rate, p99 latency, recovery time
```

#### 2.5.2 Success Criteria
```
✅ Peak error rate: <5% (transient)
✅ Recovery time: <1 minute
✅ p99 latency during spike: <5 seconds
✅ No circuit breaker trips
✅ No cascading failures
```

#### 2.5.3 Failure Mode Analysis
- If circuit breaker trips: Adjust sensitivity
- If memory spikes: Check for memory leaks
- If recovery slow: May need more DB connections

**Acceptance Criteria:**
- [ ] Spike test completed
- [ ] Success criteria met
- [ ] Report documenting behavior

---

## Timeline Gantt Chart

```
Sprint 1 (Days 1-7):
  Day 1-4:   [Task 1.1: Fix N+1 queries       ]
  Day 1-3:   [Task 1.2: Load test setup       ]
  Day 3-5:   [Task 1.3: Circuit breaker      ]
  Day 4-6:   [Task 1.4: Monitoring           ]
  Day 7:     [Baseline test + documentation   ]

Sprint 2 (Days 8-15):
  Day 8-10:  [Task 2.1: Redis migration      ]
  Day 10-12: [Task 2.2: Multi-instance test  ]
  Day 11-13: [Task 2.3: Load test 500 users  ]
  Day 13-14: [Task 2.4: Deployment prep      ]
  Day 14-15: [Task 2.5: Spike testing        ]
```

---

## Success Metrics

### Performance Targets (Post-Implementation)
| Metric | Before | Target | Stretch |
|--------|--------|--------|---------|
| DB Queries/sec | 200-300 | 100-150 | <100 |
| Response Time p95 | 2-3s | <500ms | <250ms |
| Orders/sec capacity | 40 | 150 | 300 |
| Error rate | <1% | <0.5% | <0.1% |
| Concurrent users | 200 | 500 | 1000 |

### Reliability Targets
| Metric | Target |
|--------|--------|
| Uptime | 99.9% |
| MTTR (mean time to recovery) | <5 minutes |
| Data loss incidents | 0 |
| Cascading failures | 0 |

---

## Resource Requirements

### Team
- 1 Backend Engineer (main): 100% allocation
- 1 QA Engineer: 60% allocation (load testing)
- 1 DevOps Engineer: 40% allocation (infrastructure)

### Infrastructure
- Redis instance (2GB+ RAM)
- Additional monitoring (Prometheus/Grafana)
- Load testing resources (can be temporary)
- Database backups (automated)

### Tools
- Locust (load testing) — free
- Prometheus + Grafana — free (open-source)
- Redis — free (open-source)
- Monitoring storage (1 GB/day) — paid or self-hosted

---

## Risk Mitigation

### Risk: N+1 Query Fix Causes Regressions
- Mitigation: Comprehensive test coverage before/after
- Rollback: Keep previous code in feature branch

### Risk: Redis Downtime Causes Bot Failure
- Mitigation: Graceful fallback to MemoryStorage
- Fallback code:
  ```python
  try:
      storage = RedisStorage(redis)
  except Exception:
      log.warning("Redis unavailable, falling back to MemoryStorage")
      storage = MemoryStorage()
  ```

### Risk: Load Test Reveals Critical Issues
- Mitigation: Run baseline test early (Day 7)
- Escalation: If failures found, extend timeline
- Contingency: May need to reduce target user count

---

## Sign-Off Criteria

**Ready for Production when:**
1. ✅ All N+1 queries fixed + tested
2. ✅ Circuit breaker implemented + tested
3. ✅ Redis running + FSM migrated
4. ✅ 500-user load test passed
5. ✅ Spike test passed
6. ✅ Monitoring + alerting active
7. ✅ Deployment runbook documented
8. ✅ Team trained on procedures
9. ✅ Zero known critical issues
10. ✅ Business approval obtained

---

**Prepared:** June 11, 2026  
**Target Completion:** June 26, 2026  
**Status:** Ready to execute  
**Next Steps:** Assign resources and start Sprint 1 Day 1
