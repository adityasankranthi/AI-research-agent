from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from api.schemas import ResearchRequest
from api.stream import event_stream

router = APIRouter()


@router.post("/research")
async def research(req: ResearchRequest) -> StreamingResponse:
    return StreamingResponse(
        event_stream(req),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            # Disables buffering on Nginx-fronted deployments so SSE chunks flush
            # immediately instead of arriving in one batch at the end.
            "X-Accel-Buffering": "no",
        },
    )
