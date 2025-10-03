"""
Export Queue Manager service for handling background export jobs
"""
import queue
import threading
from typing import Dict, List, Optional, Callable
from datetime import datetime
import uuid
import json
import os
from pathlib import Path

from models.export_job import ExportJob, JobStatus, JobType
from core.video_engine import VideoEngine, ProcessingOptions


class ExportQueueManager:
    """Manages a queue of export jobs and processes them in the background"""
    
    def __init__(self, max_concurrent_jobs: int = 2):
        self.max_concurrent_jobs = max_concurrent_jobs
        self.job_queue = queue.PriorityQueue()
        self.active_jobs: Dict[str, ExportJob] = {}
        self.completed_jobs: List[ExportJob] = []
        self.worker_thread = None
        self.stop_event = threading.Event()
        self.engine = VideoEngine()
        self.status_callbacks: List[Callable[[ExportJob], None]] = []
        
        # Create jobs directory if it doesn't exist
        self.jobs_dir = Path.home() / '.video_splitter' / 'jobs'
        self.jobs_dir.mkdir(parents=True, exist_ok=True)
        
        # Load persisted jobs
        self._load_jobs()
        
        # Start worker thread
        self._start_worker()
    
    def add_job(
        self,
        source_file: str,
        segments: list,
        output_dir: str,
        options: ProcessingOptions,
        priority: int = 1
    ) -> ExportJob:
        """
        Add a new export job to the queue
        
        Args:
            source_file: Path to source video
            segments: List of segments to export
            output_dir: Output directory
            options: Processing options
            priority: Job priority (lower number = higher priority)
        
        Returns:
            The created job
        """
        job = ExportJob(
            job_id=str(uuid.uuid4()),
            job_type=JobType.EXPORT,
            status=JobStatus.QUEUED,
            created_at=datetime.now(),
            result={
                'source_file': source_file,
                'segments': segments,
                'output_dir': output_dir,
                'options': options.__dict__
            }
        )
        
        # Save job to disk
        self._save_job(job)
        
        # Add to queue
        self.job_queue.put((priority, job))
        self._notify_status_update(job)
        
        return job
    
    def cancel_job(self, job_id: str) -> bool:
        """
        Cancel a job if possible
        
        Returns:
            True if job was cancelled
        """
        # Check active jobs
        if job_id in self.active_jobs:
            job = self.active_jobs[job_id]
            job.status = JobStatus.CANCELLED
            job.completed_at = datetime.now()
            self._save_job(job)
            self._notify_status_update(job)
            return True
        
        # Check queue for job
        unfinished = []
        found = False
        while not self.job_queue.empty():
            priority, job = self.job_queue.get()
            if job.job_id == job_id:
                job.status = JobStatus.CANCELLED
                job.completed_at = datetime.now()
                self._save_job(job)
                self._notify_status_update(job)
                found = True
            else:
                unfinished.append((priority, job))
        
        # Restore unfinished jobs
        for item in unfinished:
            self.job_queue.put(item)
            
        return found
    
    def get_job(self, job_id: str) -> Optional[ExportJob]:
        """Get job by ID"""
        # Check active jobs
        if job_id in self.active_jobs:
            return self.active_jobs[job_id]
        
        # Check completed jobs
        for job in self.completed_jobs:
            if job.job_id == job_id:
                return job
        
        # Check queue
        unfinished = []
        found_job = None
        while not self.job_queue.empty():
            priority, job = self.job_queue.get()
            if job.job_id == job_id:
                found_job = job
            unfinished.append((priority, job))
        
        # Restore queue
        for item in unfinished:
            self.job_queue.put(item)
            
        return found_job
    
    def get_all_jobs(self) -> List[ExportJob]:
        """Get all jobs (queued, active, and completed)"""
        jobs = []
        
        # Add queued jobs
        unfinished = []
        while not self.job_queue.empty():
            priority, job = self.job_queue.get()
            jobs.append(job)
            unfinished.append((priority, job))
        
        # Restore queue
        for item in unfinished:
            self.job_queue.put(item)
        
        # Add active and completed jobs
        jobs.extend(self.active_jobs.values())
        jobs.extend(self.completed_jobs)
        
        return sorted(jobs, key=lambda j: j.created_at, reverse=True)
    
    def register_status_callback(self, callback: Callable[[ExportJob], None]):
        """Register callback for job status updates"""
        self.status_callbacks.append(callback)
    
    def unregister_status_callback(self, callback: Callable[[ExportJob], None]):
        """Unregister callback for job status updates"""
        if callback in self.status_callbacks:
            self.status_callbacks.remove(callback)
    
    def _notify_status_update(self, job: ExportJob):
        """Notify all registered callbacks of job status update"""
        for callback in self.status_callbacks:
            try:
                callback(job)
            except Exception as e:
                print(f"Error in status callback: {e}")
    
    def _start_worker(self):
        """Start the worker thread"""
        if self.worker_thread is None or not self.worker_thread.is_alive():
            self.stop_event.clear()
            self.worker_thread = threading.Thread(target=self._process_queue)
            self.worker_thread.daemon = True
            self.worker_thread.start()
    
    def _process_queue(self):
        """Process jobs in the queue"""
        while not self.stop_event.is_set():
            # Check if we can start another job
            if len(self.active_jobs) >= self.max_concurrent_jobs:
                self.stop_event.wait(1)  # Wait a bit before checking again
                continue
            
            try:
                # Get next job
                priority, job = self.job_queue.get(timeout=1)
            except queue.Empty:
                continue
            
            # Start processing job
            job.status = JobStatus.RUNNING
            job.started_at = datetime.now()
            self.active_jobs[job.job_id] = job
            self._save_job(job)
            self._notify_status_update(job)
            
            try:
                # Process the job
                result = job.result
                self.engine.load_video(result['source_file'])
                processed = self.engine.process_segments(
                    result['segments'],
                    result['output_dir'],
                    ProcessingOptions(**result['options']),
                    progress_callback=lambda c, t, m: self._update_progress(job, c, t, m)
                )
                
                # Update job result
                job.result['processed'] = [p.__dict__ for p in processed]
                job.status = JobStatus.COMPLETED
                
            except Exception as e:
                job.status = JobStatus.FAILED
                job.error_message = str(e)
            
            # Finish job
            job.completed_at = datetime.now()
            self._save_job(job)
            self._notify_status_update(job)
            
            # Move to completed jobs
            del self.active_jobs[job.job_id]
            self.completed_jobs.append(job)
            
            # Limit completed jobs history
            if len(self.completed_jobs) > 100:
                oldest = self.completed_jobs.pop(0)
                self._delete_job_file(oldest.job_id)
    
    def _update_progress(self, job: ExportJob, current: int, total: int, message: str):
        """Update job progress"""
        job.progress = current / total if total > 0 else 0
        self._notify_status_update(job)
    
    def _save_job(self, job: ExportJob):
        """Save job to disk"""
        job_file = self.jobs_dir / f"{job.job_id}.json"
        try:
            with open(job_file, 'w') as f:
                json.dump({
                    'job_id': job.job_id,
                    'job_type': job.job_type.value,
                    'status': job.status.value,
                    'created_at': job.created_at.isoformat(),
                    'started_at': job.started_at.isoformat() if job.started_at else None,
                    'completed_at': job.completed_at.isoformat() if job.completed_at else None,
                    'progress': job.progress,
                    'error_message': job.error_message,
                    'result': job.result
                }, f)
        except Exception as e:
            print(f"Error saving job {job.job_id}: {e}")
    
    def _load_jobs(self):
        """Load persisted jobs from disk"""
        for job_file in self.jobs_dir.glob("*.json"):
            try:
                with open(job_file) as f:
                    data = json.load(f)
                
                job = ExportJob(
                    job_id=data['job_id'],
                    job_type=JobType(data['job_type']),
                    status=JobStatus(data['status']),
                    created_at=datetime.fromisoformat(data['created_at']),
                    started_at=datetime.fromisoformat(data['started_at']) if data['started_at'] else None,
                    completed_at=datetime.fromisoformat(data['completed_at']) if data['completed_at'] else None,
                    progress=data['progress'],
                    error_message=data['error_message'],
                    result=data['result']
                )
                
                if job.is_finished:
                    self.completed_jobs.append(job)
                else:
                    # Re-queue unfinished jobs
                    job.status = JobStatus.QUEUED
                    self.job_queue.put((1, job))
                
            except Exception as e:
                print(f"Error loading job {job_file.stem}: {e}")
    
    def _delete_job_file(self, job_id: str):
        """Delete job file from disk"""
        job_file = self.jobs_dir / f"{job_id}.json"
        try:
            if job_file.exists():
                job_file.unlink()
        except Exception as e:
            print(f"Error deleting job file {job_id}: {e}")
    
    def shutdown(self):
        """Shutdown the queue manager"""
        self.stop_event.set()
        if self.worker_thread:
            self.worker_thread.join()