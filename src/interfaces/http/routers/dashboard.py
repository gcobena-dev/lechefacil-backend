from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Literal

from fastapi import APIRouter, Depends, Query

from src.infrastructure.auth.context import AuthContext
from src.interfaces.http.deps import get_auth_context, get_uow
from src.interfaces.http.schemas.dashboard import (
    AdminOverviewResponse,
    AlertsResponse,
    DailyKPIsResponse,
    DailyProgressResponse,
    TopProducersResponse,
    VetAlertsResponse,
    WorkerProgressResponse,
)

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/daily-kpis", response_model=DailyKPIsResponse)
async def get_daily_kpis(
    date_param: date = Query(alias="date", default_factory=lambda: datetime.now(timezone.utc).date()),
    context: AuthContext = Depends(get_auth_context),
    uow=Depends(get_uow),
) -> DailyKPIsResponse:
    # Get today's production data
    productions = await uow.milk_productions.list(
        context.tenant_id, 
        date_from=date_param, 
        date_to=date_param,
        animal_id=None  # All animals
    )

    # Calculate KPIs
    total_liters = sum(p.volume_l for p in productions)
    total_revenue = sum(p.amount for p in productions if p.amount) or Decimal("0")

    # Get active animals count
    active_animals_count = await uow.animals.count(context.tenant_id, is_active=True)

    average_per_animal = (
        (total_liters / active_animals_count) if active_animals_count > 0 else Decimal("0")
    )

    # Calculate trends (yesterday comparison)
    from datetime import timedelta
    yesterday = date_param - timedelta(days=1)
    yesterday_productions = await uow.milk_productions.list(
        context.tenant_id, 
        date_from=yesterday, 
        date_to=yesterday,
        animal_id=None  # All animals
    )

    yesterday_liters = sum(p.volume_l for p in yesterday_productions)
    yesterday_revenue = sum(p.amount for p in yesterday_productions if p.amount) or Decimal("0")
    yesterday_avg = (
        (yesterday_liters / active_animals_count) if active_animals_count > 0 else Decimal("0")
    )

    # Calculate percentage changes
    def calc_trend(current: Decimal, previous: Decimal) -> str:
        # Convert to Decimal to handle mixed types
        current = Decimal(str(current)) if current is not None else Decimal("0")
        previous = Decimal(str(previous)) if previous is not None else Decimal("0")

        if previous == 0:
            return "+100%" if current > 0 else "0%"
        change = ((current - previous) / previous) * 100
        return f"{'+' if change >= 0 else ''}{change:.1f}%"

    from src.interfaces.http.schemas.dashboard import DailyKPIsTrends
    trends = DailyKPIsTrends(
        liters_vs_yesterday=calc_trend(total_liters, yesterday_liters),
        revenue_vs_yesterday=calc_trend(total_revenue, yesterday_revenue),
        average_vs_yesterday=calc_trend(average_per_animal, yesterday_avg),
    )

    return DailyKPIsResponse(
        date=date_param,
        total_liters=total_liters,
        total_revenue=total_revenue or Decimal("0"),
        average_per_animal=average_per_animal,
        active_animals_count=active_animals_count,
        trends=trends,
    )


@router.get("/top-producers", response_model=TopProducersResponse)
async def get_top_producers(
    date_param: date = Query(alias="date", default_factory=lambda: datetime.now(timezone.utc).date()),
    limit: int = Query(default=5, le=20),
    context: AuthContext = Depends(get_auth_context),
    uow=Depends(get_uow),
) -> TopProducersResponse:
    # Get today's production data grouped by animal
    productions = await uow.milk_productions.list(
        context.tenant_id, 
        date_from=date_param, 
        date_to=date_param,
        animal_id=None  # All animals
    )

    # Group by animal
    animal_production = {}
    for prod in productions:
        if prod.animal_id:
            if prod.animal_id not in animal_production:
                animal_production[prod.animal_id] = Decimal("0")
            animal_production[prod.animal_id] += prod.volume_l

    # Get yesterday's data for trends
    from datetime import timedelta
    yesterday = date_param - timedelta(days=1)
    yesterday_productions = await uow.milk_productions.list(
        context.tenant_id, 
        date_from=yesterday, 
        date_to=yesterday,
        animal_id=None  # All animals
    )

    yesterday_animal_production = {}
    for prod in yesterday_productions:
        if prod.animal_id:
            if prod.animal_id not in yesterday_animal_production:
                yesterday_animal_production[prod.animal_id] = Decimal("0")
            yesterday_animal_production[prod.animal_id] += prod.volume_l

    # Get animal details
    animals_data = await uow.animals.list(context.tenant_id)
    animals_dict = {animal.id: animal for animal in animals_data}

    # Create top producers list
    from src.interfaces.http.schemas.dashboard import TopProducer
    top_producers = []

    # Sort by production descending
    sorted_animals = sorted(animal_production.items(), key=lambda x: x[1], reverse=True)[:limit]

    for animal_id, today_liters in sorted_animals:
        animal = animals_dict.get(animal_id)
        if not animal:
            continue

        yesterday_liters = yesterday_animal_production.get(animal_id, Decimal("0"))

        # Calculate trend
        if yesterday_liters == 0:
            trend = "up" if today_liters > 0 else "stable"
            trend_percentage = "+100%" if today_liters > 0 else "0%"
        else:
            change = ((today_liters - yesterday_liters) / yesterday_liters) * 100
            if change > 2:
                trend = "up"
            elif change < -2:
                trend = "down"
            else:
                trend = "stable"
            trend_percentage = f"{'+' if change >= 0 else ''}{change:.1f}%"

        top_producers.append(TopProducer(
            animal_id=animal_id,
            name=animal.name,
            tag=animal.tag,
            today_liters=today_liters,
            trend=trend,
            trend_percentage=trend_percentage,
        ))

    return TopProducersResponse(top_producers=top_producers)


@router.get("/daily-progress", response_model=DailyProgressResponse)
async def get_daily_progress(
    date_param: date = Query(alias="date", default_factory=lambda: datetime.now(timezone.utc).date()),
    context: AuthContext = Depends(get_auth_context),
    uow=Depends(get_uow),
) -> DailyProgressResponse:
    # Get productions for the day
    productions = await uow.milk_productions.list(
        context.tenant_id, 
        date_from=date_param, 
        date_to=date_param, 
        animal_id=None  # All animals
    )

    # Separate by shifts (AM before 12:00, PM after 12:00)
    morning_liters = Decimal("0")
    evening_liters = Decimal("0")
    morning_completed_at = None
    evening_completed_at = None

    for prod in productions:
        if prod.date_time.hour < 12:
            morning_liters += prod.volume_l
            if not morning_completed_at or prod.date_time > morning_completed_at:
                morning_completed_at = prod.date_time
        else:
            evening_liters += prod.volume_l
            if not evening_completed_at or prod.date_time > evening_completed_at:
                evening_completed_at = prod.date_time

    from src.interfaces.http.schemas.dashboard import ShiftProgress

    # Determine shift status
    current_time = datetime.now(timezone.utc)
    morning_status = "completed" if morning_liters > 0 else "pending"
    evening_status = "completed" if evening_liters > 0 else (
        "in_progress" if current_time.hour >= 17 else "pending"
    )

    shifts = {
        "morning": ShiftProgress(
            status=morning_status,
            completed_at=morning_completed_at,
            scheduled_at=datetime.combine(date_param, datetime.min.time().replace(hour=6)).replace(tzinfo=timezone.utc),
            liters=morning_liters,
        ),
        "evening": ShiftProgress(
            status=evening_status,
            completed_at=evening_completed_at,
            scheduled_at=datetime.combine(date_param, datetime.min.time().replace(hour=18)).replace(tzinfo=timezone.utc),
            liters=evening_liters,
        ),
    }

    # Get tenant config for daily goal
    cfg = await uow.tenant_config.get(context.tenant_id)
    target_liters = Decimal("120")  # Default goal, could be configurable

    current_liters = morning_liters + evening_liters
    completion_percentage = (
        (current_liters / target_liters * 100) if target_liters > 0 else Decimal("0")
    )

    from src.interfaces.http.schemas.dashboard import DailyGoal
    daily_goal = DailyGoal(
        target_liters=target_liters,
        current_liters=current_liters,
        completion_percentage=completion_percentage,
    )

    return DailyProgressResponse(
        date=date_param,
        shifts=shifts,
        daily_goal=daily_goal,
    )


@router.get("/alerts", response_model=AlertsResponse)
async def get_alerts(
    priority: Literal["all", "high", "medium", "low"] = Query(default="all"),
    context: AuthContext = Depends(get_auth_context),
    uow=Depends(get_uow),
) -> AlertsResponse:
    # TODO: Implement alerts system with dedicated table
    # For now, return mock alerts
    from src.interfaces.http.schemas.dashboard import DashboardAlert

    mock_alerts = [
        DashboardAlert(
            id="1",
            type="health",
            message="Bonita - Retiro de leche hasta 15/09",
            priority="high",
            animal_id=None,  # Would need to lookup animal by name
            created_at=datetime.now(timezone.utc),
        )
    ]

    if priority != "all":
        mock_alerts = [alert for alert in mock_alerts if alert.priority == priority]

    return AlertsResponse(alerts=mock_alerts)


@router.get("/worker-progress", response_model=WorkerProgressResponse)
async def get_worker_progress(
    user_id: str,
    date_param: date = Query(alias="date", default_factory=lambda: datetime.now(timezone.utc).date()),
    context: AuthContext = Depends(get_auth_context),
    uow=Depends(get_uow),
) -> WorkerProgressResponse:
    # Get productions by this worker for the day
    # TODO: Add worker tracking to productions
    productions = await uow.milk_productions.list(
        context.tenant_id, 
        date_from=date_param, 
        date_to=date_param, 
        animal_id=None,
    )

    # Calculate worker stats
    animals_milked = len(set(p.animal_id for p in productions if p.animal_id))
    total_animals_assigned = await uow.animals.count(context.tenant_id, is_active=True)
    liters_recorded = sum(p.volume_l for p in productions)

    current_time = datetime.now(timezone.utc)
    current_shift = "AM" if current_time.hour < 12 else "PM"
    shift_start = datetime.combine(
        date_param,
        datetime.min.time().replace(hour=6 if current_shift == "AM" else 18)
    ).replace(tzinfo=timezone.utc)

    from src.interfaces.http.schemas.dashboard import WorkerProgress
    today_progress = WorkerProgress(
        animals_milked=animals_milked,
        total_animals_assigned=total_animals_assigned,
        liters_recorded=liters_recorded,
        current_shift=current_shift,
        shift_start_time=shift_start,
    )

    return WorkerProgressResponse(today_progress=today_progress)


@router.get("/vet-alerts", response_model=VetAlertsResponse)
async def get_vet_alerts(
    date_param: date = Query(alias="date", default_factory=lambda: datetime.now(timezone.utc).date()),
    context: AuthContext = Depends(get_auth_context),
    uow=Depends(get_uow),
) -> VetAlertsResponse:
    # TODO: Implement health tracking system
    from src.interfaces.http.schemas.dashboard import VetHealthSummary, VetUrgentAlert

    # Mock data for now
    health_summary = VetHealthSummary(
        animals_in_treatment=3,
        active_milk_withdrawals=1,
        upcoming_vaccinations=5,
    )

    urgent_alerts = [
        VetUrgentAlert(
            animal_id=context.tenant_id,  # Mock UUID
            animal_name="Bonita",
            animal_tag="A002",
            alert_type="milk_withdrawal",
            message="Retiro de leche",
            details="Hasta 15/09 - Tratamiento antibiótico",
            priority="high",
        )
    ]

    return VetAlertsResponse(
        health_summary=health_summary,
        urgent_alerts=urgent_alerts,
    )


@router.get("/admin-overview", response_model=AdminOverviewResponse)
async def get_admin_overview(
    date_param: date = Query(alias="date", default_factory=lambda: datetime.now(timezone.utc).date()),
    context: AuthContext = Depends(get_auth_context),
    uow=Depends(get_uow),
) -> AdminOverviewResponse:
    # TODO: Calculate real metrics
    from src.interfaces.http.schemas.dashboard import AdminManagementOverview

    management_overview = AdminManagementOverview(
        monthly_profitability="+15.2%",
        production_vs_goal="102%",
        pending_alerts=3,
        upcoming_tasks=7,
    )

    return AdminOverviewResponse(management_overview=management_overview)