"""
Queue Manager for Olifan Assistant
Handles concurrent user requests with proper queuing and error handling
"""

import asyncio
import uuid
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)

class RequestStatus(Enum):
    WAITING = "waiting"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"

@dataclass
class QueuedRequest:
    request_id: str
    user_id: str
    data: Dict[str, Any]
    status: RequestStatus
    created_at: float
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    error_message: Optional[str] = None

class QueueManager:
    def __init__(self, max_concurrent: int = 1, queue_timeout: int = 300):
        self.max_concurrent = max_concurrent  # Max simultaneous requests
        self.queue_timeout = queue_timeout    # Timeout in seconds
        self.active_requests: Dict[str, QueuedRequest] = {}
        self.waiting_queue: List[QueuedRequest] = []
        self.processing_count = 0
        self.lock = asyncio.Lock()
        
    async def add_request(self, user_id: str, request_data: Dict[str, Any]) -> str:
        """Add a new request to the queue"""
        request_id = str(uuid.uuid4())
        
        queued_request = QueuedRequest(
            request_id=request_id,
            user_id=user_id,
            data=request_data,
            status=RequestStatus.WAITING,
            created_at=time.time()
        )
        
        async with self.lock:
            # Check if we can process immediately
            if self.processing_count < self.max_concurrent:
                queued_request.status = RequestStatus.PROCESSING
                queued_request.started_at = time.time()
                self.processing_count += 1
                self.active_requests[request_id] = queued_request
                logger.info(f"Processing request {request_id} immediately for user {user_id}")
            else:
                # Add to waiting queue
                self.waiting_queue.append(queued_request)
                self.active_requests[request_id] = queued_request
                position = len(self.waiting_queue)
                logger.info(f"Queued request {request_id} for user {user_id} at position {position}")
        
        return request_id
    
    async def start_processing(self, request_id: str) -> bool:
        """Mark a request as started processing"""
        async with self.lock:
            if request_id in self.active_requests:
                request = self.active_requests[request_id]
                if request.status == RequestStatus.WAITING:
                    request.status = RequestStatus.PROCESSING
                    request.started_at = time.time()
                    self.processing_count += 1
                    logger.info(f"Started processing request {request_id}")
                    return True
        return False
    
    async def complete_request(self, request_id: str, success: bool = True, error_message: Optional[str] = None):
        """Mark a request as completed"""
        async with self.lock:
            if request_id in self.active_requests:
                request = self.active_requests[request_id]
                request.completed_at = time.time()
                
                if success:
                    request.status = RequestStatus.COMPLETED
                    logger.info(f"Completed request {request_id} successfully")
                else:
                    request.status = RequestStatus.FAILED
                    request.error_message = error_message
                    logger.error(f"Failed request {request_id}: {error_message}")
                
                self.processing_count -= 1
                
                # Process next waiting request if available
                await self._process_next_waiting()
    
    async def get_request_status(self, request_id: str) -> Optional[Dict[str, Any]]:
        """Get the status of a request"""
        async with self.lock:
            if request_id in self.active_requests:
                request = self.active_requests[request_id]
                return {
                    "request_id": request.request_id,
                    "status": request.status.value,
                    "created_at": request.created_at,
                    "started_at": request.started_at,
                    "completed_at": request.completed_at,
                    "error_message": request.error_message,
                    "queue_position": self._get_queue_position(request_id) if request.status == RequestStatus.WAITING else None
                }
        return None
    
    async def cancel_request(self, request_id: str) -> bool:
        """Cancel a request"""
        async with self.lock:
            if request_id in self.active_requests:
                request = self.active_requests[request_id]
                
                if request.status == RequestStatus.WAITING:
                    # Remove from waiting queue
                    self.waiting_queue = [r for r in self.waiting_queue if r.request_id != request_id]
                    del self.active_requests[request_id]
                    logger.info(f"Cancelled waiting request {request_id}")
                    return True
                elif request.status == RequestStatus.PROCESSING:
                    # Cannot cancel processing requests
                    logger.warning(f"Cannot cancel processing request {request_id}")
                    return False
        return False
    
    async def cleanup_expired_requests(self):
        """Remove expired requests from the system"""
        current_time = time.time()
        expired_requests = []
        
        async with self.lock:
            # Check waiting requests
            for request in self.waiting_queue[:]:
                if current_time - request.created_at > self.queue_timeout:
                    expired_requests.append(request.request_id)
                    self.waiting_queue.remove(request)
            
            # Check active requests
            for request_id, request in list(self.active_requests.items()):
                if (request.status in [RequestStatus.COMPLETED, RequestStatus.FAILED] and 
                    request.completed_at and 
                    current_time - request.completed_at > 300):  # Keep completed for 5 minutes
                    expired_requests.append(request_id)
            
            # Remove expired requests
            for request_id in expired_requests:
                if request_id in self.active_requests:
                    del self.active_requests[request_id]
        
        if expired_requests:
            logger.info(f"Cleaned up {len(expired_requests)} expired requests")
    
    async def get_queue_stats(self) -> Dict[str, Any]:
        """Get queue statistics"""
        async with self.lock:
            waiting_count = len(self.waiting_queue)
            processing_count = self.processing_count
            total_active = len(self.active_requests)
            
            return {
                "max_concurrent": self.max_concurrent,
                "currently_processing": processing_count,
                "waiting_in_queue": waiting_count,
                "total_active_requests": total_active
            }
    
    async def _process_next_waiting(self):
        """Process the next waiting request if capacity available"""
        if self.waiting_queue and self.processing_count < self.max_concurrent:
            next_request = self.waiting_queue.pop(0)
            next_request.status = RequestStatus.PROCESSING
            next_request.started_at = time.time()
            self.processing_count += 1
            logger.info(f"Processing queued request {next_request.request_id} for user {next_request.user_id}")
    
    def _get_queue_position(self, request_id: str) -> Optional[int]:
        """Get queue position for a waiting request"""
        for i, request in enumerate(self.waiting_queue):
            if request.request_id == request_id:
                return i + 1
        return None

# Global queue manager instance
queue_manager = QueueManager(max_concurrent=1, queue_timeout=300)

def get_queue_manager():
    """Get the global queue manager instance"""
    return queue_manager