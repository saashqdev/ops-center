"""
Budget Management Service for Epic 14: Cost Optimization Dashboard

This module provides comprehensive budget management capabilities including:
- Budget creation and lifecycle management
- Real-time spend tracking
- Multi-tier alerting (warning, critical, exceeded)
- Budget forecasting and exhaustion prediction
- Integration with Smart Alerts for notifications
"""

import asyncio
import asyncpg
from datetime import datetime, timedelta, date
from decimal import Decimal
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum
import logging
import json

logger = logging.getLogger(__name__)


class BudgetType(str, Enum):
    """Budget period types"""
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    ANNUAL = "annual"
    CUSTOM = "custom"


class AlertLevel(str, Enum):
    """Budget alert levels"""
    NONE = "none"
    WARNING = "warning"
    CRITICAL = "critical"
    EXCEEDED = "exceeded"


@dataclass
class BudgetConfig:
    """Budget configuration"""
    name: str
    description: Optional[str]
    budget_type: BudgetType
    total_limit: Decimal
    warning_threshold: Decimal  # 0.0 to 1.0
    critical_threshold: Decimal  # 0.0 to 1.0
    start_date: date
    end_date: date
    alert_enabled: bool = True
    alert_contacts: Optional[Dict[str, List[str]]] = None  # {emails: [], slack_channels: []}


@dataclass
class Budget:
    """Budget entity"""
    id: str
    organization_id: str
    name: str
    description: Optional[str]
    budget_type: BudgetType
    total_limit: Decimal
    warning_threshold: Decimal
    critical_threshold: Decimal
    start_date: date
    end_date: date
    current_spend: Decimal
    last_calculated_at: Optional[datetime]
    alert_enabled: bool
    alert_contacts: Optional[Dict]
    last_alert_sent: Optional[datetime]
    alert_level: AlertLevel
    is_active: bool
    created_by: Optional[str]
    created_at: datetime
    updated_at: datetime


@dataclass
class BudgetStatus:
    """Budget status and health metrics"""
    budget: Budget
    utilization_percentage: Decimal
    remaining_budget: Decimal
    days_remaining: int
    daily_burn_rate: Decimal
    projected_total: Decimal
    projected_exhaustion_date: Optional[date]
    status: str  # healthy, warning, critical, exceeded
    is_on_track: bool
    days_until_exhaustion: Optional[int]


@dataclass
class BudgetUtilization:
    """Budget utilization summary"""
    budget_id: str
    budget_name: str
    total_limit: Decimal
    current_spend: Decimal
    utilization_percentage: Decimal
    status: str
    alert_level: AlertLevel


class BudgetManager:
    """
    Budget management service.
    
    Features:
    - CRUD operations for budgets
    - Real-time spend tracking
    - Threshold monitoring
    - Alert generation
    - Utilization reporting
    """
    
    def __init__(self, db_pool: asyncpg.Pool):
        self.db = db_pool
        logger.info("Budget Manager initialized")
    
    async def create_budget(
        self,
        organization_id: str,
        config: BudgetConfig,
        created_by: Optional[str] = None
    ) -> Budget:
        """
        Create a new budget.
        
        Args:
            organization_id: Organization ID
            config: Budget configuration
            created_by: User ID who created the budget
            
        Returns:
            Created Budget
        """
        # Validate thresholds
        if config.warning_threshold >= config.critical_threshold:
            raise ValueError("Warning threshold must be less than critical threshold")
        
        if config.critical_threshold > 1.0:
            raise ValueError("Critical threshold cannot exceed 100%")
        
        # Validate dates
        if config.end_date <= config.start_date:
            raise ValueError("End date must be after start date")
        
        # Insert budget
        query = """
            INSERT INTO budgets (
                organization_id, name, description, budget_type,
                total_limit, warning_threshold, critical_threshold,
                start_date, end_date, alert_enabled, alert_contacts,
                created_by, alert_level
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
            RETURNING *
        """
        
        alert_contacts_json = (
            json.dumps(config.alert_contacts) 
            if config.alert_contacts else None
        )
        
        row = await self.db.fetchrow(
            query,
            organization_id,
            config.name,
            config.description,
            config.budget_type.value,
            config.total_limit,
            config.warning_threshold,
            config.critical_threshold,
            config.start_date,
            config.end_date,
            config.alert_enabled,
            alert_contacts_json,
            created_by,
            AlertLevel.NONE.value
        )
        
        logger.info(f"Created budget {row['id']} for organization {organization_id}")
        
        return self._row_to_budget(row)
    
    async def update_budget(
        self,
        budget_id: str,
        updates: Dict[str, Any]
    ) -> Budget:
        """
        Update budget configuration.
        
        Args:
            budget_id: Budget ID to update
            updates: Dictionary of fields to update
            
        Returns:
            Updated Budget
        """
        allowed_fields = {
            'name', 'description', 'total_limit', 'warning_threshold',
            'critical_threshold', 'end_date', 'alert_enabled', 
            'alert_contacts', 'is_active'
        }
        
        # Filter to allowed fields
        updates = {k: v for k, v in updates.items() if k in allowed_fields}
        
        if not updates:
            # Nothing to update, return current
            return await self.get_budget(budget_id)
        
        # Build update query
        set_clauses = []
        params = []
        param_count = 1
        
        for field, value in updates.items():
            if field == 'alert_contacts' and isinstance(value, dict):
                value = json.dumps(value)
            
            set_clauses.append(f"{field} = ${param_count}")
            params.append(value)
            param_count += 1
        
        params.append(budget_id)
        
        query = f"""
            UPDATE budgets
            SET {', '.join(set_clauses)}, updated_at = NOW()
            WHERE id = ${param_count}
            RETURNING *
        """
        
        row = await self.db.fetchrow(query, *params)
        
        if not row:
            raise ValueError(f"Budget {budget_id} not found")
        
        logger.info(f"Updated budget {budget_id}")
        
        return self._row_to_budget(row)
    
    async def get_budget(self, budget_id: str) -> Budget:
        """Get budget by ID"""
        row = await self.db.fetchrow(
            "SELECT * FROM budgets WHERE id = $1",
            budget_id
        )
        
        if not row:
            raise ValueError(f"Budget {budget_id} not found")
        
        return self._row_to_budget(row)
    
    async def list_budgets(
        self,
        organization_id: str,
        is_active: Optional[bool] = None,
        budget_type: Optional[BudgetType] = None
    ) -> List[Budget]:
        """
        List budgets for an organization.
        
        Args:
            organization_id: Organization ID
            is_active: Filter by active status
            budget_type: Filter by budget type
            
        Returns:
            List of budgets
        """
        query = "SELECT * FROM budgets WHERE organization_id = $1"
        params = [organization_id]
        param_count = 2
        
        if is_active is not None:
            query += f" AND is_active = ${param_count}"
            params.append(is_active)
            param_count += 1
        
        if budget_type:
            query += f" AND budget_type = ${param_count}"
            params.append(budget_type.value)
            param_count += 1
        
        query += " ORDER BY created_at DESC"
        
        rows = await self.db.fetch(query, *params)
        
        return [self._row_to_budget(row) for row in rows]
    
    async def delete_budget(self, budget_id: str) -> bool:
        """
        Delete a budget.
        
        Args:
            budget_id: Budget ID to delete
            
        Returns:
            True if deleted, False if not found
        """
        result = await self.db.execute(
            "DELETE FROM budgets WHERE id = $1",
            budget_id
        )
        
        deleted = result.endswith("1")
        
        if deleted:
            logger.info(f"Deleted budget {budget_id}")
        
        return deleted
    
    async def update_budget_spend(
        self,
        budget_id: str,
        additional_cost: Decimal
    ) -> Budget:
        """
        Add cost to budget's current spend.
        
        Args:
            budget_id: Budget ID
            additional_cost: Cost to add
            
        Returns:
            Updated Budget
        """
        query = """
            UPDATE budgets
            SET current_spend = current_spend + $1,
                last_calculated_at = NOW(),
                updated_at = NOW()
            WHERE id = $2
            RETURNING *
        """
        
        row = await self.db.fetchrow(query, additional_cost, budget_id)
        
        if not row:
            raise ValueError(f"Budget {budget_id} not found")
        
        budget = self._row_to_budget(row)
        
        # Check if alert level changed
        await self._update_alert_level(budget)
        
        return budget
    
    async def recalculate_budget_spend(
        self,
        budget_id: str,
        force: bool = False
    ) -> Budget:
        """
        Recalculate budget spend from cost_analysis table.
        
        Args:
            budget_id: Budget ID
            force: Force recalculation even if recently calculated
            
        Returns:
            Updated Budget
        """
        budget = await self.get_budget(budget_id)
        
        # Skip if recently calculated (unless forced)
        if not force and budget.last_calculated_at:
            time_since_calc = datetime.now() - budget.last_calculated_at
            if time_since_calc < timedelta(minutes=15):
                return budget  # Calculated less than 15 min ago
        
        # Sum costs from cost_analysis
        query = """
            SELECT COALESCE(SUM(total_cost), 0) as total
            FROM cost_analysis
            WHERE organization_id = $1
              AND period_start >= $2
              AND period_end <= $3
        """
        
        row = await self.db.fetchrow(
            query,
            budget.organization_id,
            datetime.combine(budget.start_date, datetime.min.time()),
            datetime.combine(budget.end_date, datetime.max.time())
        )
        
        current_spend = row["total"]
        
        # Update budget
        update_query = """
            UPDATE budgets
            SET current_spend = $1,
                last_calculated_at = NOW(),
                updated_at = NOW()
            WHERE id = $2
            RETURNING *
        """
        
        updated_row = await self.db.fetchrow(update_query, current_spend, budget_id)
        updated_budget = self._row_to_budget(updated_row)
        
        # Check alert level
        await self._update_alert_level(updated_budget)
        
        logger.info(
            f"Recalculated budget {budget_id} spend: ${current_spend:.2f}"
        )
        
        return updated_budget
    
    async def check_budget_status(
        self,
        budget_id: str
    ) -> BudgetStatus:
        """
        Get comprehensive budget status.
        
        Returns:
            BudgetStatus with health metrics and projections
        """
        budget = await self.get_budget(budget_id)
        
        # Calculate utilization
        utilization_pct = (
            (budget.current_spend / budget.total_limit) * 100
            if budget.total_limit > 0 else Decimal("0")
        )
        
        remaining_budget = budget.total_limit - budget.current_spend
        
        # Calculate days remaining
        today = date.today()
        days_remaining = (budget.end_date - today).days
        
        # Calculate burn rate (cost per day)
        period_days = (budget.end_date - budget.start_date).days
        days_elapsed = (today - budget.start_date).days
        
        if days_elapsed > 0:
            daily_burn_rate = budget.current_spend / days_elapsed
        else:
            daily_burn_rate = Decimal("0")
        
        # Project total spend
        if days_remaining > 0 and daily_burn_rate > 0:
            projected_total = budget.current_spend + (daily_burn_rate * days_remaining)
        else:
            projected_total = budget.current_spend
        
        # Calculate exhaustion date
        projected_exhaustion_date = None
        days_until_exhaustion = None
        
        if daily_burn_rate > 0 and remaining_budget > 0:
            days_until_exhaustion = int(remaining_budget / daily_burn_rate)
            projected_exhaustion_date = today + timedelta(days=days_until_exhaustion)
        elif remaining_budget <= 0:
            projected_exhaustion_date = today
            days_until_exhaustion = 0
        
        # Determine status
        if utilization_pct >= 100:
            status = "exceeded"
            is_on_track = False
        elif utilization_pct >= budget.critical_threshold * 100:
            status = "critical"
            is_on_track = False
        elif utilization_pct >= budget.warning_threshold * 100:
            status = "warning"
            is_on_track = projected_total <= budget.total_limit
        else:
            status = "healthy"
            is_on_track = True
        
        return BudgetStatus(
            budget=budget,
            utilization_percentage=utilization_pct,
            remaining_budget=remaining_budget,
            days_remaining=days_remaining,
            daily_burn_rate=daily_burn_rate,
            projected_total=projected_total,
            projected_exhaustion_date=projected_exhaustion_date,
            status=status,
            is_on_track=is_on_track,
            days_until_exhaustion=days_until_exhaustion
        )
    
    async def get_budget_utilization(
        self,
        organization_id: str
    ) -> List[BudgetUtilization]:
        """
        Get utilization summary for all active budgets.
        
        Args:
            organization_id: Organization ID
            
        Returns:
            List of BudgetUtilization summaries
        """
        rows = await self.db.fetch(
            "SELECT * FROM v_active_budget_status WHERE organization_id = $1",
            organization_id
        )
        
        return [
            BudgetUtilization(
                budget_id=row["budget_id"],
                budget_name=row["name"],
                total_limit=row["total_limit"],
                current_spend=row["current_spend"],
                utilization_percentage=row["utilization_percentage"],
                status=row["status"],
                alert_level=AlertLevel(row["alert_level"])
            )
            for row in rows
        ]
    
    async def trigger_budget_alerts(
        self,
        budget_id: str,
        force: bool = False
    ) -> Optional[Dict]:
        """
        Check if budget alert should be triggered.
        
        Args:
            budget_id: Budget ID to check
            force: Force alert even if recently sent
            
        Returns:
            Alert data if triggered, None otherwise
        """
        budget = await self.get_budget(budget_id)
        
        if not budget.alert_enabled:
            return None
        
        # Calculate current utilization
        utilization = (
            (budget.current_spend / budget.total_limit)
            if budget.total_limit > 0 else Decimal("0")
        )
        
        # Determine required alert level
        if utilization >= 1.0:
            required_level = AlertLevel.EXCEEDED
        elif utilization >= budget.critical_threshold:
            required_level = AlertLevel.CRITICAL
        elif utilization >= budget.warning_threshold:
            required_level = AlertLevel.WARNING
        else:
            required_level = AlertLevel.NONE
        
        # Check if already alerted at this level
        if not force and budget.alert_level == required_level:
            # Already alerted at this level
            return None
        
        if required_level == AlertLevel.NONE:
            return None
        
        # Check cooldown (don't spam alerts)
        if not force and budget.last_alert_sent:
            time_since_alert = datetime.now() - budget.last_alert_sent
            if time_since_alert < timedelta(hours=1):
                return None  # Wait at least 1 hour between alerts
        
        # Get budget status for context
        status = await self.check_budget_status(budget_id)
        
        # Create alert data
        alert_data = {
            "budget_id": budget.id,
            "budget_name": budget.name,
            "alert_level": required_level.value,
            "utilization_percentage": float(utilization * 100),
            "current_spend": float(budget.current_spend),
            "total_limit": float(budget.total_limit),
            "remaining_budget": float(status.remaining_budget),
            "days_remaining": status.days_remaining,
            "daily_burn_rate": float(status.daily_burn_rate),
            "projected_total": float(status.projected_total),
            "projected_exhaustion_date": (
                status.projected_exhaustion_date.isoformat()
                if status.projected_exhaustion_date else None
            ),
            "alert_contacts": budget.alert_contacts
        }
        
        # Update alert tracking
        await self.db.execute(
            """
            UPDATE budgets
            SET alert_level = $1,
                last_alert_sent = NOW(),
                updated_at = NOW()
            WHERE id = $2
            """,
            required_level.value,
            budget_id
        )
        
        logger.warning(
            f"Budget alert triggered: {budget.name} ({required_level.value}) "
            f"- {utilization*100:.1f}% utilized"
        )
        
        # TODO: Integrate with Smart Alerts system
        # await create_smart_alert(
        #     alert_type="budget_threshold",
        #     severity=required_level.value,
        #     data=alert_data
        # )
        
        return alert_data
    
    async def get_budget_history(
        self,
        budget_id: str,
        days: int = 30
    ) -> List[Dict]:
        """
        Get historical spend data for a budget.
        
        Args:
            budget_id: Budget ID
            days: Number of days of history
            
        Returns:
            List of daily spend records
        """
        budget = await self.get_budget(budget_id)
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        query = """
            SELECT 
                DATE(period_start) as date,
                SUM(total_cost) as daily_cost,
                SUM(total_requests) as daily_requests
            FROM cost_analysis
            WHERE organization_id = $1
              AND period_start >= $2
              AND period_start <= $3
            GROUP BY DATE(period_start)
            ORDER BY date ASC
        """
        
        rows = await self.db.fetch(
            query,
            budget.organization_id,
            start_date,
            end_date
        )
        
        # Calculate running total
        running_total = Decimal("0")
        history = []
        
        for row in rows:
            running_total += row["daily_cost"]
            history.append({
                "date": row["date"].isoformat(),
                "daily_cost": float(row["daily_cost"]),
                "daily_requests": row["daily_requests"],
                "cumulative_cost": float(running_total),
                "utilization_percentage": float(
                    (running_total / budget.total_limit) * 100
                ) if budget.total_limit > 0 else 0.0
            })
        
        return history
    
    async def _update_alert_level(self, budget: Budget) -> None:
        """
        Update budget's alert level based on current spend.
        Internal method called after spend updates.
        """
        utilization = (
            (budget.current_spend / budget.total_limit)
            if budget.total_limit > 0 else Decimal("0")
        )
        
        if utilization >= 1.0:
            new_level = AlertLevel.EXCEEDED
        elif utilization >= budget.critical_threshold:
            new_level = AlertLevel.CRITICAL
        elif utilization >= budget.warning_threshold:
            new_level = AlertLevel.WARNING
        else:
            new_level = AlertLevel.NONE
        
        if new_level != budget.alert_level:
            await self.db.execute(
                "UPDATE budgets SET alert_level = $1 WHERE id = $2",
                new_level.value,
                budget.id
            )
    
    def _row_to_budget(self, row: asyncpg.Record) -> Budget:
        """Convert database row to Budget object"""
        alert_contacts = None
        if row["alert_contacts"]:
            if isinstance(row["alert_contacts"], str):
                alert_contacts = json.loads(row["alert_contacts"])
            else:
                alert_contacts = row["alert_contacts"]
        
        return Budget(
            id=row["id"],
            organization_id=row["organization_id"],
            name=row["name"],
            description=row["description"],
            budget_type=BudgetType(row["budget_type"]),
            total_limit=row["total_limit"],
            warning_threshold=row["warning_threshold"],
            critical_threshold=row["critical_threshold"],
            start_date=row["start_date"],
            end_date=row["end_date"],
            current_spend=row["current_spend"],
            last_calculated_at=row["last_calculated_at"],
            alert_enabled=row["alert_enabled"],
            alert_contacts=alert_contacts,
            last_alert_sent=row["last_alert_sent"],
            alert_level=AlertLevel(row["alert_level"]),
            is_active=row["is_active"],
            created_by=row["created_by"],
            created_at=row["created_at"],
            updated_at=row["updated_at"]
        )


# Singleton instance
_budget_manager: Optional[BudgetManager] = None


async def get_budget_manager(db_pool: asyncpg.Pool) -> BudgetManager:
    """Get or create the Budget Manager singleton"""
    global _budget_manager
    
    if _budget_manager is None:
        _budget_manager = BudgetManager(db_pool)
    
    return _budget_manager
