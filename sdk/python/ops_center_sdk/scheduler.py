"""
Task scheduler for plugins
"""

import asyncio
from datetime import datetime, timedelta
from typing import Callable, Dict, Any, Optional
from uuid import uuid4


class Scheduler:
    """
    Task scheduler for background jobs
    
    Example:
        ```python
        scheduler = plugin.scheduler
        
        # Schedule one-time task
        await scheduler.run_at(
            datetime.now() + timedelta(hours=1),
            "cleanup_old_data",
            task_id="data-123"
        )
        
        # Schedule recurring task (cron-like)
        await scheduler.schedule(
            cron="0 0 * * *",  # Daily at midnight
            task_name="daily_sync",
            handler=sync_external_data
        )
        
        # Cancel task
        await scheduler.cancel("task-id")
        ```
    """
    
    def __init__(self, plugin_id: str):
        self.plugin_id = plugin_id
        self._tasks: Dict[str, asyncio.Task] = {}
        self._scheduled_jobs: Dict[str, Dict[str, Any]] = {}
    
    async def run_at(
        self,
        run_time: datetime,
        handler: Callable,
        task_id: Optional[str] = None,
        **kwargs
    ) -> str:
        """
        Schedule task to run at specific time
        
        Args:
            run_time: When to run the task
            handler: Async function to run
            task_id: Optional task ID (auto-generated if not provided)
            **kwargs: Arguments to pass to handler
        
        Returns:
            Task ID
        """
        if task_id is None:
            task_id = str(uuid4())
        
        delay = (run_time - datetime.now()).total_seconds()
        
        if delay < 0:
            raise ValueError("run_time must be in the future")
        
        async def delayed_task():
            await asyncio.sleep(delay)
            await handler(**kwargs)
        
        task = asyncio.create_task(delayed_task())
        self._tasks[task_id] = task
        
        return task_id
    
    async def run_in(
        self,
        delay: timedelta,
        handler: Callable,
        task_id: Optional[str] = None,
        **kwargs
    ) -> str:
        """
        Schedule task to run after delay
        
        Args:
            delay: How long to wait before running
            handler: Async function to run
            task_id: Optional task ID
            **kwargs: Arguments to pass to handler
        
        Returns:
            Task ID
        """
        run_time = datetime.now() + delay
        return await self.run_at(run_time, handler, task_id, **kwargs)
    
    async def schedule(
        self,
        cron: str,
        task_name: str,
        handler: Callable,
        **kwargs
    ) -> str:
        """
        Schedule recurring task (cron-style)
        
        Args:
            cron: Cron expression (e.g., "0 0 * * *" for daily at midnight)
            task_name: Name for the scheduled job
            handler: Async function to run
            **kwargs: Arguments to pass to handler
        
        Returns:
            Job ID
        """
        job_id = f"{self.plugin_id}:{task_name}"
        
        # Store job definition
        self._scheduled_jobs[job_id] = {
            "cron": cron,
            "handler": handler,
            "kwargs": kwargs,
            "active": True
        }
        
        # TODO: Implement actual cron scheduling
        # For now, this is a placeholder
        
        return job_id
    
    async def cancel(self, task_id: str):
        """
        Cancel scheduled task
        
        Args:
            task_id: Task ID to cancel
        """
        if task_id in self._tasks:
            task = self._tasks[task_id]
            task.cancel()
            del self._tasks[task_id]
        
        if task_id in self._scheduled_jobs:
            del self._scheduled_jobs[task_id]
    
    async def cancel_all(self):
        """Cancel all scheduled tasks"""
        for task in self._tasks.values():
            task.cancel()
        
        self._tasks.clear()
        self._scheduled_jobs.clear()
    
    def get_tasks(self) -> Dict[str, Dict[str, Any]]:
        """
        Get information about scheduled tasks
        
        Returns:
            Dictionary of task information
        """
        return {
            "one_time_tasks": list(self._tasks.keys()),
            "scheduled_jobs": {
                job_id: {
                    "cron": job["cron"],
                    "active": job["active"]
                }
                for job_id, job in self._scheduled_jobs.items()
            }
        }
