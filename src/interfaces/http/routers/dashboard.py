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
    date_param: date = Query(
        alias="date", default_factory=lambda: datetime.now(timezone.utc).date()
    ),
    context: AuthContext = Depends(get_auth_context),
    uow=Depends(get_uow),
) -> DailyKPIsResponse:
    # Get today's production data
    productions = await uow.milk_productions.list(
        context.tenant_id,
        date_from=date_param,
        date_to=date_param,
        animal_id=None,  # All animals
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
        animal_id=None,  # All animals
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
    date_param: date = Query(
        alias="date", default_factory=lambda: datetime.now(timezone.utc).date()
    ),
    limit: int = Query(default=5, le=20),
    context: AuthContext = Depends(get_auth_context),
    uow=Depends(get_uow),
) -> TopProducersResponse:
    # Get today's production data grouped by animal
    productions = await uow.milk_productions.list(
        context.tenant_id,
        date_from=date_param,
        date_to=date_param,
        animal_id=None,  # All animals
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
        animal_id=None,  # All animals
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

        top_producers.append(
            TopProducer(
                animal_id=animal_id,
                name=animal.name,
                tag=animal.tag,
                today_liters=today_liters,
                trend=trend,
                trend_percentage=trend_percentage,
            )
        )

    return TopProducersResponse(top_producers=top_producers)


@router.get("/daily-progress", response_model=DailyProgressResponse)
async def get_daily_progress(
    date_param: date = Query(
        alias="date", default_factory=lambda: datetime.now(timezone.utc).date()
    ),
    context: AuthContext = Depends(get_auth_context),
    uow=Depends(get_uow),
) -> DailyProgressResponse:
    # Get productions for the day
    productions = await uow.milk_productions.list(
        context.tenant_id,
        date_from=date_param,
        date_to=date_param,
        animal_id=None,  # All animals
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
    evening_status = (
        "completed"
        if evening_liters > 0
        else ("in_progress" if current_time.hour >= 17 else "pending")
    )

    shifts = {
        "morning": ShiftProgress(
            status=morning_status,
            completed_at=morning_completed_at,
            scheduled_at=datetime.combine(date_param, datetime.min.time().replace(hour=6)).replace(
                tzinfo=timezone.utc
            ),
            liters=morning_liters,
        ),
        "evening": ShiftProgress(
            status=evening_status,
            completed_at=evening_completed_at,
            scheduled_at=datetime.combine(date_param, datetime.min.time().replace(hour=18)).replace(
                tzinfo=timezone.utc
            ),
            liters=evening_liters,
        ),
    }

    # Compute dynamic daily goal from last 30 days average
    from datetime import timedelta

    window_days = 30
    window_start = date_param - timedelta(days=window_days)
    recent_productions = await uow.milk_productions.list(
        context.tenant_id,
        date_from=window_start,
        date_to=date_param,
        animal_id=None,
    )
    total_recent = sum(p.volume_l for p in recent_productions)
    # Include days without data by dividing by fixed window size
    target_liters = (total_recent / Decimal(window_days)) if window_days > 0 else Decimal("0")

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
    date_param: date = Query(
        alias="date", default_factory=lambda: datetime.now(timezone.utc).date()
    ),
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
        date_param, datetime.min.time().replace(hour=6 if current_shift == "AM" else 18)
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
    date_param: date = Query(
        alias="date", default_factory=lambda: datetime.now(timezone.utc).date()
    ),
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
    date_param: date = Query(
        alias="date", default_factory=lambda: datetime.now(timezone.utc).date()
    ),
    context: AuthContext = Depends(get_auth_context),
    uow=Depends(get_uow),
) -> AdminOverviewResponse:
    from datetime import timedelta
    from decimal import Decimal

    from src.interfaces.http.schemas.dashboard import AdminManagementOverview

    # Periods
    start_of_month = date_param.replace(day=1)
    days_elapsed = date_param.day

    # Previous month same elapsed days window
    prev_month_end = start_of_month - timedelta(days=1)
    prev_month_start = prev_month_end.replace(day=1)
    prev_window_end = prev_month_start + timedelta(days=days_elapsed - 1)

    # 1) Production vs goal (Month-to-date) using last-30-days average as daily goal
    productions_mtd = await uow.milk_productions.list(
        context.tenant_id,
        date_from=start_of_month,
        date_to=date_param,
        animal_id=None,
    )
    produced_liters_mtd: Decimal = sum(p.volume_l for p in productions_mtd)

    # Compute daily goal from last 30 days average (include zero-production days)
    window_days = 30
    window_start = date_param - timedelta(days=window_days)
    recent_productions = await uow.milk_productions.list(
        context.tenant_id,
        date_from=window_start,
        date_to=date_param,
        animal_id=None,
    )
    total_recent = sum(p.volume_l for p in recent_productions)
    daily_goal_liters = (total_recent / Decimal(window_days)) if window_days > 0 else Decimal("0")
    monthly_goal_to_date = daily_goal_liters * Decimal(days_elapsed)
    production_vs_goal_pct = (
        (produced_liters_mtd / monthly_goal_to_date * Decimal("100"))
        if monthly_goal_to_date > 0
        else Decimal("0")
    )

    # 2) "Monthly profitability" proxy: revenue growth vs previous month window
    # Use deliveries amounts as gross revenue proxy
    deliveries_mtd = await uow.milk_deliveries.list(
        context.tenant_id,
        date_from=start_of_month,
        date_to=date_param,
        buyer_id=None,
    )
    revenue_mtd: Decimal = sum((d.amount or Decimal("0")) for d in deliveries_mtd)

    deliveries_prev = await uow.milk_deliveries.list(
        context.tenant_id,
        date_from=prev_month_start,
        date_to=prev_window_end,
        buyer_id=None,
    )
    revenue_prev: Decimal = sum((d.amount or Decimal("0")) for d in deliveries_prev)

    if revenue_prev == 0:
        profitability_change = Decimal("100") if revenue_mtd > 0 else Decimal("0")
    else:
        profitability_change = (revenue_mtd - revenue_prev) / revenue_prev * Decimal("100")

    # 3) Pending alerts and upcoming tasks (real data from health records)
    # Pending alerts: count of active milk withdrawals
    active_withdrawals = await uow.health_records.get_active_withdrawals(context.tenant_id)
    pending_alerts = len(active_withdrawals)

    # Upcoming tasks: vaccinations due in the next 7 days
    upcoming_vaccinations = await uow.health_records.get_upcoming_vaccinations(
        context.tenant_id, days_ahead=7
    )
    upcoming_tasks = len(upcoming_vaccinations)

    management_overview = AdminManagementOverview(
        monthly_profitability=(
            f"+{profitability_change:.1f}%"
            if profitability_change >= 0
            else f"{profitability_change:.1f}%"
        ),
        production_vs_goal=f"{production_vs_goal_pct:.0f}%",
        pending_alerts=pending_alerts,
        upcoming_tasks=upcoming_tasks,
    )

    return AdminOverviewResponse(management_overview=management_overview)
