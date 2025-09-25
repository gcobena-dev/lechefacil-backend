from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel


class DailyKPIsTrends(BaseModel):
    liters_vs_yesterday: str
    revenue_vs_yesterday: str
    average_vs_yesterday: str


class DailyKPIsResponse(BaseModel):
    date: date
    total_liters: Decimal
    total_revenue: Decimal
    average_per_animal: Decimal
    active_animals_count: int
    trends: DailyKPIsTrends


class TopProducer(BaseModel):
    animal_id: UUID
    name: str
    tag: str
    today_liters: Decimal
    trend: Literal["up", "down", "stable"]
    trend_percentage: str


class TopProducersResponse(BaseModel):
    top_producers: list[TopProducer]


class DashboardAlert(BaseModel):
    id: str
    type: Literal["health", "production", "price"]
    message: str
    priority: Literal["high", "medium", "low"]
    animal_id: UUID | None = None
    created_at: datetime


class AlertsResponse(BaseModel):
    alerts: list[DashboardAlert]


class ShiftProgress(BaseModel):
    status: Literal["completed", "in_progress", "pending"]
    completed_at: datetime | None = None
    scheduled_at: datetime | None = None
    liters: Decimal


class DailyGoal(BaseModel):
    target_liters: Decimal
    current_liters: Decimal
    completion_percentage: Decimal


class DailyProgressResponse(BaseModel):
    date: date
    shifts: dict[str, ShiftProgress]  # "morning", "evening"
    daily_goal: DailyGoal


class WorkerProgress(BaseModel):
    animals_milked: int
    total_animals_assigned: int
    liters_recorded: Decimal
    current_shift: Literal["AM", "PM"]
    shift_start_time: datetime


class WorkerProgressResponse(BaseModel):
    today_progress: WorkerProgress


class VetHealthSummary(BaseModel):
    animals_in_treatment: int
    active_milk_withdrawals: int
    upcoming_vaccinations: int


class VetUrgentAlert(BaseModel):
    animal_id: UUID
    animal_name: str
    animal_tag: str
    alert_type: str
    message: str
    details: str
    priority: Literal["high", "medium", "low"]


class VetAlertsResponse(BaseModel):
    health_summary: VetHealthSummary
    urgent_alerts: list[VetUrgentAlert]


class AdminManagementOverview(BaseModel):
    monthly_profitability: str
    production_vs_goal: str
    pending_alerts: int
    upcoming_tasks: int


class AdminOverviewResponse(BaseModel):
    management_overview: AdminManagementOverview
