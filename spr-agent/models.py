# spr-agent/models.py
#
# Single source of truth: re-export everything from shared/schemas/spr_schedule.py.
# main.py imports: SPRScheduleRequest, SPRScheduleResponse, DailySchedule
# All of those are now defined in the shared schema.
from shared.schemas.spr_schedule import (
    SPRScheduleRequest,
    SPRScheduleResponse,
    DailySchedule,
)

__all__ = [
    "SPRScheduleRequest",
    "SPRScheduleResponse",
    "DailySchedule",
]
