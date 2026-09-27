class TaskForgeError(Exception):
    pass


class TaskNotFoundError(TaskForgeError):
    def __init__(self, task_name: str):
        super().__init__(f"Task '{task_name}' is not registered in TaskRegistry")
        self.task_name = task_name


class TaskExecutionError(TaskForgeError):
    def __init__(self, message: str, original_exception: Exception | None = None):
        super().__init__(message)
        self.original_exception = original_exception


class JobNotFoundError(TaskForgeError):
    def __init__(self, job_id: str):
        super().__init__(f"Job with ID '{job_id}' not found")
        self.job_id = job_id


class JobAlreadyCancelledError(TaskForgeError):
    def __init__(self, job_id: str):
        super().__init__(f"Job '{job_id}' has already been cancelled")
        self.job_id = job_id


class InvalidJobStateError(TaskForgeError):
    def __init__(self, job_id: str, current_state: str, action: str):
        super().__init__(f"Cannot {action} job '{job_id}' in state '{current_state}'")
        self.job_id = job_id
        self.current_state = current_state
        self.action = action


class TaskTimeoutError(TaskForgeError):
    def __init__(self, job_id: str, timeout_seconds: float):
        super().__init__(f"Job '{job_id}' timed out after {timeout_seconds} seconds")
        self.job_id = job_id
        self.timeout_seconds = timeout_seconds


class ScheduleNotFoundError(TaskForgeError):
    def __init__(self, schedule_id: str):
        super().__init__(f"Schedule '{schedule_id}' not found")
        self.schedule_id = schedule_id
