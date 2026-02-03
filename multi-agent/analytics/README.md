# Analytics Module

## Overview

The Analytics module provides **system-wide workflow statistics** for the admin dashboard. It is a new feature added to UnifAI that enables administrators to monitor workflow execution patterns, user activity, and blueprint usage across the entire platform.

This module follows the established architectural patterns in the `multi-agent` codebase:
- **Service-Repository Pattern** (like `ShareService` / `MongoShareRepository`)
- **Dependency Injection** via `AppContainer`
- **Pydantic DTOs** for type-safe data transfer
- **Abstract Repository** for database abstraction

---

## Changes from Main Branch

### New Files Added

```
multi-agent/
├── analytics/                          # NEW MODULE
│   ├── __init__.py                     # Module exports
│   ├── models.py                       # Pydantic response models
│   ├── utils.py                        # Time filtering utilities
│   ├── service.py                      # AnalyticsService
│   ├── repository/
│   │   ├── __init__.py
│   │   ├── base.py                     # Abstract AnalyticsRepository
│   │   └── mongo_repository.py         # MongoDB implementation (with $facet)
│   └── README.md                       # This file
├── api/flask/
│   └── decorators.py                   # NEW: @require_admin_access decorator
├── core/
│   └── app_container.py                # MODIFIED: Added analytics wiring

ui/client/src/
├── api/analytics.ts                    # NEW: Analytics API client
├── types/analytics.ts                  # NEW: TypeScript interfaces
├── pages/Analytics.tsx                 # NEW: Analytics dashboard page
├── components/analytics/               # NEW: 10+ analytics components
│   ├── AccessDenied.tsx
│   ├── ActiveTodayTable.tsx
│   ├── AllUsersTable.tsx
│   ├── AnalyticCard.tsx
│   ├── BlueprintsTable.tsx
│   ├── LoadingSkeleton.tsx
│   ├── StatusBreakdownChart.tsx
│   ├── TopBlueprintsQuickView.tsx
│   ├── TopUsersChart.tsx
│   ├── WorkflowExecutionChart.tsx
│   └── analyticsHelpers.ts
└── components/shared/
    └── ErrorDisplay.tsx                # NEW: Reusable error component
```

### Modified Files

| File | Change |
|------|--------|
| `api/flask/endpoints/statistics.py` | Added `/analytics.overview.get` endpoint |
| `api/flask/flask_app.py` | Added `admin_allowed_users` to Flask config |
| `config/app_config.py` | Added `admin_allowed_users` list |
| `core/app_container.py` | Wired `AnalyticsService` and `MongoAnalyticsRepository` |
| `ui/client/src/contexts/AuthContext.tsx` | Added `is_admin` field to User |
| `ui/client/src/App.tsx` | Added `/analytics` route |
| `ui/client/src/components/layout/Sidebar.tsx` | Added Analytics menu item |

---

## Full System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                                   FRONTEND (React)                               │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  ┌──────────────────┐    ┌─────────────────┐    ┌──────────────────────────┐    │
│  │   Analytics.tsx  │───▶│  useQuery Hook  │───▶│  fetchAnalyticsOverview  │    │
│  │   (Dashboard)    │    │ (React Query)   │    │   (api/analytics.ts)     │    │
│  └──────────────────┘    └─────────────────┘    └────────────┬─────────────┘    │
│         │                                                     │                  │
│         ▼                                                     │                  │
│  ┌──────────────────┐                                        │                  │
│  │ user.is_admin?   │ ◀─── AuthContext (from /api/auth/user) │                  │
│  │ (Access Control) │                                        │                  │
│  └──────────────────┘                                        │                  │
│                                                               ▼                  │
└───────────────────────────────────────────────────────────────┼──────────────────┘
                                                                │
                          HTTP GET /api2/statistics/analytics.overview.get
                          ?time_range=all&userId=<user>         │
                                                                ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              BACKEND (Flask Multi-Agent)                         │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  ┌────────────────────────────────────────────────────────────────────────┐     │
│  │                        api/flask/endpoints/statistics.py               │     │
│  │  ┌───────────────────────────────────────────────────────────────────┐ │     │
│  │  │  @statistics_bp.route("/analytics.overview.get", methods=["GET"]) │ │     │
│  │  │  @from_query({time_range, user_id})                               │ │     │
│  │  │  @require_admin_access  ◀── Checks admin_allowed_users            │ │     │
│  │  │  def get_analytics(time_range, user_id):                          │ │     │
│  │  │      analytics_service = container.analytics_service              │ │     │
│  │  │      return analytics_service.get_analytics(time_range)           │ │     │
│  │  └───────────────────────────────────────────────────────────────────┘ │     │
│  └────────────────────────────────────────────────────────────────────────┘     │
│                                      │                                           │
│                                      ▼                                           │
│  ┌────────────────────────────────────────────────────────────────────────┐     │
│  │                         api/flask/decorators.py                        │     │
│  │  ┌───────────────────────────────────────────────────────────────────┐ │     │
│  │  │  @require_admin_access                                            │ │     │
│  │  │  ┌─────────────────────────────────────────────────────────────┐  │ │     │
│  │  │  │ 1. Get admin_allowed_users from Flask config                │  │ │     │
│  │  │  │ 2. If empty → 403 FEATURE_DISABLED                          │  │ │     │
│  │  │  │ 3. Extract user_id from query params                        │  │ │     │
│  │  │  │ 4. If user_id not in list → 403 ACCESS_DENIED               │  │ │     │
│  │  │  │ 5. Proceed to endpoint                                      │  │ │     │
│  │  │  └─────────────────────────────────────────────────────────────┘  │ │     │
│  │  └───────────────────────────────────────────────────────────────────┘ │     │
│  └────────────────────────────────────────────────────────────────────────┘     │
│                                      │                                           │
│                                      ▼                                           │
│  ┌────────────────────────────────────────────────────────────────────────┐     │
│  │                     core/app_container.py (DI Container)               │     │
│  │  ┌───────────────────────────────────────────────────────────────────┐ │     │
│  │  │  self.analytics_repo = MongoAnalyticsRepository(...)              │ │     │
│  │  │  self.analytics_service = AnalyticsService(                       │ │     │
│  │  │      analytics_repo=self.analytics_repo,                          │ │     │
│  │  │      blueprint_service=self.blueprint_service                     │ │     │
│  │  │  )                                                                │ │     │
│  │  └───────────────────────────────────────────────────────────────────┘ │     │
│  └────────────────────────────────────────────────────────────────────────┘     │
│                                      │                                           │
│                                      ▼                                           │
│  ┌────────────────────────────────────────────────────────────────────────┐     │
│  │                        analytics/service.py                            │     │
│  │  ┌───────────────────────────────────────────────────────────────────┐ │     │
│  │  │  class AnalyticsService:                                          │ │     │
│  │  │      def get_analytics(time_range) -> OverviewStatisticsResponse  │ │     │
│  │  │          ├── _repo.count_runs()                                   │ │     │
│  │  │          ├── _repo.get_distinct_users()                           │ │     │
│  │  │          ├── _repo.group_by(["status"])                           │ │     │
│  │  │          ├── _repo.get_all_analytics_faceted()                    │ │     │
│  │  │          ├── _process_user_data()                                 │ │     │
│  │  │          ├── _process_blueprint_data()                            │ │     │
│  │  │          └── _repo.get_time_series()                              │ │     │
│  │  └───────────────────────────────────────────────────────────────────┘ │     │
│  └────────────────────────────────────────────────────────────────────────┘     │
│                                      │                                           │
│                                      ▼                                           │
│  ┌────────────────────────────────────────────────────────────────────────┐     │
│  │                 analytics/repository/mongo_repository.py               │     │
│  │  ┌───────────────────────────────────────────────────────────────────┐ │     │
│  │  │  class MongoAnalyticsRepository(AnalyticsRepository):             │ │     │
│  │  │      def count_runs(filter, time_range)                           │ │     │
│  │  │      def get_distinct_users(filter, time_range)                   │ │     │
│  │  │      def group_by(group_by, filter, time_range)                   │ │     │
│  │  │      def get_time_series(time_range)                              │ │     │
│  │  │      def get_all_analytics_faceted(time_range)                    │ │     │
│  │  │                                                                   │ │     │
│  │  │  Uses MongoDB Aggregation Framework:                              │ │     │
│  │  │      - $facet (parallel aggregations)                             │ │     │
│  │  │      - $match (time filtering)                                    │ │     │
│  │  │      - $group (aggregations)                                      │ │     │
│  │  │      - $dateToString (time series)                                │ │     │
│  │  └───────────────────────────────────────────────────────────────────┘ │     │
│  └────────────────────────────────────────────────────────────────────────┘     │
│                                      │                                           │
│                                      ▼                                           │
│  ┌────────────────────────────────────────────────────────────────────────┐     │
│  │                              MongoDB                                   │     │
│  │  ┌───────────────────────────────────────────────────────────────────┐ │     │
│  │  │  Collection: workflow_sessions                                    │ │     │
│  │  │                                                                   │ │     │
│  │  │  Indexes (created by MongoAnalyticsRepository):                   │ │     │
│  │  │    - run_context.started_at (time queries)                        │ │     │
│  │  │    - status (status aggregation)                                  │ │     │
│  │  │    - blueprint_id (blueprint aggregation)                         │ │     │
│  │  │    - user_id + run_context.started_at (user activity)             │ │     │
│  │  └───────────────────────────────────────────────────────────────────┘ │     │
│  └────────────────────────────────────────────────────────────────────────┘     │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## Request Flow Diagram

```
┌──────────┐     ┌─────────────┐     ┌─────────────────┐     ┌──────────────────┐
│  Browser │────▶│  React App  │────▶│  Flask Backend  │────▶│     MongoDB      │
└──────────┘     └─────────────┘     └─────────────────┘     └──────────────────┘
     │                  │                    │                        │
     │   1. User clicks │                    │                        │
     │   "Analytics"    │                    │                        │
     │                  │                    │                        │
     │                  │  2. Check          │                        │
     │                  │  user.is_admin     │                        │
     │                  │  (from AuthContext)│                        │
     │                  │                    │                        │
     │                  │  3. If admin:      │                        │
     │                  │  fetchAnalyticsOverview()                   │
     │                  │                    │                        │
     │                  │ ─────────────────▶ │                        │
     │                  │ GET /api2/statistics/analytics.overview.get │
     │                  │ ?time_range=all&userId=<user>               │
     │                  │                    │                        │
     │                  │                    │  4. @require_admin_access
     │                  │                    │  Check user in list    │
     │                  │                    │                        │
     │                  │                    │  5. AnalyticsService   │
     │                  │                    │  .get_analytics()      │
     │                  │                    │                        │
     │                  │                    │ ─────────────────────▶ │
     │                  │                    │  6. MongoDB Aggregation│
     │                  │                    │  Queries               │
     │                  │                    │                        │
     │                  │                    │ ◀───────────────────── │
     │                  │                    │  7. Aggregation Results│
     │                  │                    │                        │
     │                  │ ◀───────────────── │                        │
     │                  │  8. OverviewStatisticsResponse (JSON)       │
     │                  │                    │                        │
     │ ◀──────────────  │                    │                        │
     │  9. Render       │                    │                        │
     │  Analytics       │                    │                        │
     │  Dashboard       │                    │                        │
     │                  │                    │                        │
```

---

## Class Hierarchy

### Backend Classes

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              ANALYTICS MODULE                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                         analytics/service.py                          │  │
│  │  ┌─────────────────────────────────────────────────────────────────┐  │  │
│  │  │  class AnalyticsService                                         │  │  │
│  │  │  ├── __init__(analytics_repo, blueprint_service)                │  │  │
│  │  │  │                                                              │  │  │
│  │  │  │  Dependencies:                                               │  │  │
│  │  │  │  ├── AnalyticsRepository (injected)                          │  │  │
│  │  │  │  └── BlueprintService (for name lookups)                     │  │  │
│  │  │  │                                                              │  │  │
│  │  │  ├── get_analytics(time_range) -> OverviewStatisticsResponse    │  │  │
│  │  │  │   └── Main orchestration method                              │  │  │
│  │  │  │                                                              │  │  │
│  │  │  ├── _get_active_users_data(days) -> List[Dict]                 │  │  │
│  │  │  │   └── Users active in last N days                            │  │  │
│  │  │  │                                                              │  │  │
│  │  │  ├── _aggregate_user_counts(user_counts, field) -> Dict         │  │  │
│  │  │  │   └── Aggregate by user with status breakdown                │  │  │
│  │  │  │                                                              │  │  │
│  │  │  ├── _process_user_counts(user_counts, days) -> List[Dict]      │  │  │
│  │  │  │   └── Process into user activity dicts                       │  │  │
│  │  │  │                                                              │  │  │
│  │  │  ├── _get_top_users(limit) -> List[Dict]                        │  │  │
│  │  │  │   └── Top users by total runs (all time)                     │  │  │
│  │  │  │                                                              │  │  │
│  │  │  ├── _get_blueprint_name(blueprint_id) -> str                   │  │  │
│  │  │  │   └── Lookup blueprint display name                          │  │  │
│  │  │  │                                                              │  │  │
│  │  │  └── _get_top_blueprints(limit, time_range) -> List[Dict]       │  │  │
│  │  │      └── Most used blueprints                                   │  │  │
│  │  └─────────────────────────────────────────────────────────────────┘  │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                      │                                       │
│                                      │ uses                                  │
│                                      ▼                                       │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                    analytics/repository/base.py                       │  │
│  │  ┌─────────────────────────────────────────────────────────────────┐  │  │
│  │  │  class AnalyticsRepository (ABC)                                │  │  │
│  │  │  ├── count_runs(filter, time_range) -> int                      │  │  │
│  │  │  ├── get_distinct_users(filter, time_range) -> List[str]        │  │  │
│  │  │  ├── group_by(group_by, filter, time_range) -> List[GroupedCount]│ │  │
│  │  │  └── get_time_series(time_range) -> List[Dict]                  │  │  │
│  │  └─────────────────────────────────────────────────────────────────┘  │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                      ▲                                       │
│                                      │ implements                            │
│                                      │                                       │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │               analytics/repository/mongo_repository.py                │  │
│  │  ┌─────────────────────────────────────────────────────────────────┐  │  │
│  │  │  class MongoAnalyticsRepository(AnalyticsRepository)            │  │  │
│  │  │  ├── __init__(mongodb_port, mongodb_ip, db_name, collection)    │  │  │
│  │  │  ├── _ensure_indexes()                                          │  │  │
│  │  │  │   └── Creates indexes for analytics queries                  │  │  │
│  │  │  ├── _apply_time_range_filter(filter, time_range) -> Dict       │  │  │
│  │  │  │   └── Adds $gte filter on run_context.started_at             │  │  │
│  │  │  ├── count_runs(...) -> int                                     │  │  │
│  │  │  │   └── Uses count_documents()                                 │  │  │
│  │  │  ├── get_distinct_users(...) -> List[str]                       │  │  │
│  │  │  │   └── Uses distinct("user_id")                               │  │  │
│  │  │  ├── group_by(...) -> List[GroupedCount]                        │  │  │
│  │  │  │   └── Uses $group aggregation pipeline                       │  │  │
│  │  │  └── get_time_series(...) -> List[Dict]                         │  │  │
│  │  │      └── Uses $dateToString + $group pipeline                   │  │  │
│  │  └─────────────────────────────────────────────────────────────────┘  │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                              DATA MODELS                                     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                        analytics/models.py                            │  │
│  │  ┌─────────────────────────────────────────────────────────────────┐  │  │
│  │  │  class TotalStats(BaseModel)                                    │  │  │
│  │  │  ├── total_runs: int                                            │  │  │
│  │  │  ├── unique_users: int                                          │  │  │
│  │  │  └── avg_runs_per_user: float                                   │  │  │
│  │  └─────────────────────────────────────────────────────────────────┘  │  │
│  │  ┌─────────────────────────────────────────────────────────────────┐  │  │
│  │  │  class OverviewStatisticsResponse(BaseModel)                    │  │  │
│  │  │  ├── total_stats: TotalStats                                    │  │  │
│  │  │  ├── status_breakdown: Dict[str, int]                           │  │  │
│  │  │  ├── active_today: List[Dict[str, Any]]                         │  │  │
│  │  │  ├── active_7days: List[Dict[str, Any]]                         │  │  │
│  │  │  ├── active_30days: List[Dict[str, Any]]                        │  │  │
│  │  │  ├── top_users: List[Dict[str, Any]]                            │  │  │
│  │  │  ├── top_blueprints: List[Dict[str, Any]]                       │  │  │
│  │  │  ├── time_series: List[Dict[str, Any]]                          │  │  │
│  │  │  └── generated_at: str                                          │  │  │
│  │  └─────────────────────────────────────────────────────────────────┘  │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                           core/dto.py                                 │  │
│  │  ┌─────────────────────────────────────────────────────────────────┐  │  │
│  │  │  class GroupedCount(BaseModel)                                  │  │  │
│  │  │  ├── fields: Dict[str, Any]  # e.g., {"status": "COMPLETED"}    │  │  │
│  │  │  ├── count: int                                                 │  │  │
│  │  │  └── get(field, default) -> Any                                 │  │  │
│  │  └─────────────────────────────────────────────────────────────────┘  │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Access Control Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          ACCESS CONTROL ARCHITECTURE                         │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                    config/app_config.py                             │    │
│  │  ┌───────────────────────────────────────────────────────────────┐  │    │
│  │  │  class AppConfig(SharedConfig):                               │  │    │
│  │  │      admin_allowed_users: list = ["yhabushi"]                 │  │    │
│  │  │      # Populate with usernames to grant admin access          │  │    │
│  │  │      # Empty list = Analytics feature disabled                │  │    │
│  │  └───────────────────────────────────────────────────────────────┘  │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                      │                                       │
│                                      │ passed to                             │
│                                      ▼                                       │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                    api/flask/flask_app.py                           │    │
│  │  ┌───────────────────────────────────────────────────────────────┐  │    │
│  │  │  app.config["admin_allowed_users"] = config.admin_allowed_users│  │    │
│  │  └───────────────────────────────────────────────────────────────┘  │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                      │                                       │
│                                      │ accessed by                           │
│                                      ▼                                       │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                    api/flask/decorators.py                          │    │
│  │  ┌───────────────────────────────────────────────────────────────┐  │    │
│  │  │  @require_admin_access                                        │  │    │
│  │  │                                                               │  │    │
│  │  │  def decorated_function(*args, **kwargs):                     │  │    │
│  │  │      admin_list = current_app.config["admin_allowed_users"]   │  │    │
│  │  │                                                               │  │    │
│  │  │      if not admin_list:                                       │  │    │
│  │  │          return 403, "FEATURE_DISABLED"                       │  │    │
│  │  │                                                               │  │    │
│  │  │      user_id = get_user_id_from_request()                     │  │    │
│  │  │                                                               │  │    │
│  │  │      if not user_id:                                          │  │    │
│  │  │          return 401, "AUTHENTICATION_REQUIRED"                │  │    │
│  │  │                                                               │  │    │
│  │  │      if user_id not in admin_list:                            │  │    │
│  │  │          return 403, "ACCESS_DENIED"                          │  │    │
│  │  │                                                               │  │    │
│  │  │      return f(*args, **kwargs)  # Proceed                     │  │    │
│  │  └───────────────────────────────────────────────────────────────┘  │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                    FRONTEND (AuthContext.tsx)                       │    │
│  │  ┌───────────────────────────────────────────────────────────────┐  │    │
│  │  │  interface User {                                             │  │    │
│  │  │      username: string;                                        │  │    │
│  │  │      is_admin?: boolean;  // Set by SSO /api/auth/user        │  │    │
│  │  │  }                                                            │  │    │
│  │  │                                                               │  │    │
│  │  │  // Analytics.tsx uses:                                       │  │    │
│  │  │  const hasAccess = user?.is_admin || false;                   │  │    │
│  │  │                                                               │  │    │
│  │  │  // Shows AccessDenied component if !hasAccess                │  │    │
│  │  └───────────────────────────────────────────────────────────────┘  │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Time Range Filtering

The analytics module supports four time ranges:

| Time Range | Filter | Time Series Granularity |
|------------|--------|-------------------------|
| `today` | From midnight UTC today | Hourly (`%Y-%m-%d %H:00`) |
| `7days` | Last 7 days | Daily (`%Y-%m-%d`) |
| `30days` | Last 30 days | Daily (`%Y-%m-%d`) |
| `all` | Last 365 days (capped) | Daily (`%Y-%m-%d`) |

### Time Filter Implementation

```python
# analytics/utils.py

def get_cutoff_date(time_range: str) -> datetime:
    now = datetime.now(timezone.utc)
    
    if time_range == "today":
        return now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif time_range == "7days":
        return now - timedelta(days=7)
    elif time_range == "30days":
        return now - timedelta(days=30)
    else:  # "all"
        return now - timedelta(days=90)  # Default cap for non-time-series


def apply_time_range_filter(filter_dict, time_range):
    if time_range and time_range != "all":
        cutoff = get_cutoff_date(time_range)
        filter_dict["run_context.started_at"] = {"$gte": cutoff.isoformat()}
    return filter_dict
```

---

## API Response Format

### Endpoint: `GET /api2/statistics/analytics.overview.get`

**Query Parameters:**
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `time_range` | string | No | `all` | One of: `today`, `7days`, `30days`, `all` |
| `userId` | string | Yes | - | User ID for access control |

**Response: `OverviewStatisticsResponse`**

```json
{
  "total_stats": {
    "total_runs": 1234,
    "unique_users": 45,
    "avg_runs_per_user": 27.42
  },
  "status_breakdown": {
    "COMPLETED": 1000,
    "FAILED": 150,
    "RUNNING": 50,
    "PENDING": 34
  },
  "active_today": [
    {
      "user_id": "alice",
      "runs_today": 15,
      "unique_blueprints": 3,
      "status_breakdown": {"COMPLETED": 12, "FAILED": 3}
    }
  ],
  "active_7days": [
    {
      "user_id": "bob",
      "recent_runs": 45,
      "unique_blueprints": 5,
      "status_breakdown": {"COMPLETED": 40, "FAILED": 5}
    }
  ],
  "active_30days": [...],
  "top_users": [
    {
      "user_id": "alice",
      "total_runs": 500,
      "unique_blueprints": 12,
      "status_breakdown": {"COMPLETED": 450, "FAILED": 50}
    }
  ],
  "top_blueprints": [
    {
      "blueprint_id": "bp-123",
      "blueprint_name": "Code Review Assistant",
      "run_count": 200,
      "unique_users": 15
    }
  ],
  "time_series": [
    {"period": "2026-02-01", "count": 45},
    {"period": "2026-02-02", "count": 52}
  ],
  "generated_at": "2026-02-03T10:30:00Z"
}
```

---

## Frontend Components

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            UI COMPONENT HIERARCHY                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  pages/Analytics.tsx (Main Page)                                             │
│  ├── Sidebar                                                                 │
│  ├── Header                                                                  │
│  │                                                                           │
│  ├── [Access Check: user.is_admin]                                           │
│  │   ├── AccessDenied.tsx (if no access)                                     │
│  │   └── LoadingSkeleton.tsx (if loading)                                    │
│  │                                                                           │
│  ├── Time Range Buttons (today | 7days | 30days | all)                       │
│  │                                                                           │
│  ├── Overview Stats Cards (4x StatCard)                                      │
│  │   ├── Total Runs                                                          │
│  │   ├── Total Users                                                         │
│  │   ├── Success Rate                                                        │
│  │   └── Active Today                                                        │
│  │                                                                           │
│  └── Tabs                                                                    │
│      ├── Overview Tab                                                        │
│      │   ├── StatusBreakdownChart.tsx (Pie chart)                            │
│      │   ├── TopUsersChart.tsx (Bar chart)                                   │
│      │   ├── TopBlueprintsQuickView.tsx (List)                               │
│      │   └── WorkflowExecutionChart.tsx (Line chart)                         │
│      │                                                                       │
│      ├── Users Tab                                                           │
│      │   ├── ActiveTodayTable.tsx (Paginated table)                          │
│      │   └── AllUsersTable.tsx (Paginated table)                             │
│      │                                                                       │
│      └── Blueprints Tab                                                      │
│          └── BlueprintsTable.tsx (Full table)                                │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Database Schema

The analytics module queries the existing `workflow_sessions` collection:

```javascript
// Document structure in workflow_sessions collection
{
  "_id": ObjectId("..."),
  "user_id": "alice",
  "run_id": "run-abc123",
  "blueprint_id": "bp-xyz789",
  "status": "COMPLETED",  // PENDING, RUNNING, COMPLETED, FAILED
  "run_context": {
    "started_at": "2026-02-03T10:00:00Z",
    "finished_at": "2026-02-03T10:05:00Z",
    // ... other context
  },
  "graph_state": { ... },
  "metadata": { ... }
}

// Indexes created by MongoAnalyticsRepository
db.workflow_sessions.createIndex({ "run_context.started_at": 1 })
db.workflow_sessions.createIndex({ "status": 1 })
db.workflow_sessions.createIndex({ "blueprint_id": 1 })
db.workflow_sessions.createIndex({ "user_id": 1, "run_context.started_at": 1 })
```

---

## Usage Examples

### Backend: Adding a new metric

```python
# In analytics/service.py

def get_analytics(self, time_range: str = "all") -> OverviewStatisticsResponse:
    # ... existing code ...
    
    # Add new metric
    failed_runs = self._repo.count_runs(
        filter={"status": "FAILED"},
        time_range=time_range
    )
    
    # Include in response
    return OverviewStatisticsResponse(
        # ... existing fields ...
        failed_count=failed_runs,  # Add to model first
    )
```

### Backend: Custom grouping

```python
# Group by user and blueprint
user_blueprint_counts = self._repo.group_by(
    group_by=["user_id", "blueprint_id"],
    time_range="7days"
)
# Returns: [GroupedCount(fields={"user_id": "alice", "blueprint_id": "bp-1"}, count=10), ...]
```

### Frontend: Using analytics data

```typescript
// In any component
import { useQuery } from "@tanstack/react-query";
import { fetchAnalyticsOverview } from "@/api/analytics";

const { data: analytics } = useQuery({
  queryKey: ['analytics', timeRange, userId],
  queryFn: () => fetchAnalyticsOverview(timeRange, userId),
  enabled: hasAdminAccess,
});

// Access data
const totalRuns = analytics?.total_stats?.total_runs || 0;
const topUsers = analytics?.top_users || [];
```

---

## Configuration

### Enable Analytics Access

Edit `multi-agent/config/app_config.py`:

```python
class AppConfig(SharedConfig):
    # Add usernames that should have admin access
    admin_allowed_users: list = ["alice", "bob", "admin"]
```

### Disable Analytics

Set empty list to disable the feature entirely:

```python
admin_allowed_users: list = []  # Returns 403 FEATURE_DISABLED
```

---

## Performance Considerations

1. **Indexes**: The `MongoAnalyticsRepository` creates indexes on first initialization
2. **Time Caps**: "all" time range is capped at 365 days to prevent excessive queries
3. **Aggregation Limits**: Time series limited to 1000 data points
4. **Client-side Caching**: React Query caches results for 60 seconds (`staleTime`)
5. **Auto-refresh**: Dashboard auto-refreshes every 60 seconds (`refetchInterval`)

---

## $facet Aggregation

The `get_all_analytics_faceted()` method uses MongoDB's `$facet` stage to execute multiple aggregations in parallel within a single query.

### Facet Structure

```
┌─────────────────────────────────────────────────────────────────────────┐
│  get_all_analytics_faceted(time_range)                                   │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │                         $facet Stage                               │  │
│  │                                                                    │  │
│  │  Active Users (6 facets):                                          │  │
│  │  ├── today_status, week_status, month_status                      │  │
│  │  └── today_blueprints, week_blueprints, month_blueprints          │  │
│  │                                                                    │  │
│  │  Top Users (2 facets):                                             │  │
│  │  └── all_time_user_status, all_time_user_blueprints               │  │
│  │                                                                    │  │
│  │  Top Blueprints (1 facet):                                         │  │
│  │  └── top_blueprints_data                                           │  │
│  │                                                                    │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### Code Structure

```python
# In MongoAnalyticsRepository
def get_all_analytics_faceted(self, time_range: str) -> Dict[str, List[GroupedCount]]:
    pipeline = [
        {"$facet": {
            "today_status": [...], "week_status": [...], "month_status": [...],
            "today_blueprints": [...], "week_blueprints": [...], "month_blueprints": [...],
            "all_time_user_status": [...], "all_time_user_blueprints": [...],
            "top_blueprints_data": [...]
        }}
    ]
    return self._col.aggregate(pipeline)

# In AnalyticsService
def get_analytics(self, time_range: str) -> OverviewStatisticsResponse:
    faceted_data = self._repo.get_all_analytics_faceted(time_range)
    
    active_today = self._process_user_data(faceted_data["today_status"], ...)
    top_users = self._process_user_data(faceted_data["all_time_user_status"], ...)
    top_blueprints = self._process_blueprint_data(faceted_data["top_blueprints_data"], ...)

# Helper methods
def _process_user_data(status_counts, blueprint_counts, ...) -> List[Dict]:
    """Process user data from faceted results."""

def _add_blueprint_counts(user_data, blueprint_counts) -> None:
    """Add unique blueprint counts to user data."""

def _batch_get_blueprint_names(blueprint_ids) -> Dict[str, str]:
    """Get blueprint names for a list of IDs."""
```
