import time
import asyncio
import aiohttp
from datetime import datetime
import statistics
from typing import Dict, List, Optional, Callable, Any, Tuple

class BenchmarkResult:
    """Class to hold benchmark results."""
    
    def __init__(self, name: str):
        self.name = name
        self.response_times = []
        self.status_codes = []
        self.errors = []
        self.start_time = time.time()
        self.end_time = None
    
    def add_result(self, response_time: float, status_code: int, error: Optional[str] = None):
        """Add a benchmark result."""
        self.response_times.append(response_time)
        self.status_codes.append(status_code)
        if error:
            self.errors.append(error)
    
    def finish(self):
        """Mark the benchmark as finished."""
        self.end_time = time.time()
    
    def get_summary(self) -> Dict:
        """Get a summary of the benchmark results."""
        if not self.response_times:
            return {
                "name": self.name,
                "num_requests": 0,
                "num_errors": len(self.errors),
                "error_rate": 1.0 if self.errors else 0.0,
                "duration": 0,
                "requests_per_second": 0
            }
            
        num_requests = len(self.response_times)
        num_errors = len(self.errors)
        error_rate = num_errors / num_requests if num_requests > 0 else 0
        duration = self.end_time - self.start_time if self.end_time else time.time() - self.start_time
        rps = num_requests / duration if duration > 0 else 0
        
        percentiles = {
            "min": min(self.response_times),
            "mean": statistics.mean(self.response_times),
            "median": statistics.median(self.response_times),
            "p95": percentile(self.response_times, 95),
            "p99": percentile(self.response_times, 99),
            "max": max(self.response_times)
        }
        
        status_counts = {}
        for code in self.status_codes:
            if code not in status_counts:
                status_counts[code] = 0
            status_counts[code] += 1
        
        return {
            "name": self.name,
            "num_requests": num_requests,
            "num_errors": num_errors,
            "error_rate": error_rate,
            "duration": duration,
            "requests_per_second": rps,
            "response_times": percentiles,
            "status_codes": status_counts
        }


def percentile(data: List[float], percentile: int) -> float:
    """Calculate the given percentile of a list of numbers."""
    if not data:
        return 0
    
    sorted_data = sorted(data)
    index = (len(sorted_data) - 1) * percentile / 100
    floor = int(index)
    ceil = min(floor + 1, len(sorted_data) - 1)
    
    if floor == ceil:
        return sorted_data[floor]
    
    return sorted_data[floor] * (ceil - index) + sorted_data[ceil] * (index - floor)


async def run_benchmark(
    name: str,
    url: str,
    num_requests: int,
    concurrency: int,
    headers: Optional[Dict] = None,
    json_data: Optional[Dict] = None,
    method: str = "GET",
    warmup_requests: int = 0
) -> BenchmarkResult:
    """Run a benchmark for the given URL."""
    
    # Run warmup requests if needed
    if warmup_requests > 0:
        try:
            warmup_result = await run_benchmark(
                f"{name}_warmup",
                url,
                warmup_requests,
                min(concurrency, warmup_requests),
                headers,
                json_data,
                method,
                0
            )
        except Exception as e:
            print(f"Warning: Warmup failed for {name}: {e}")
            # Continue even if warmup fails
    
    result = BenchmarkResult(name)
    
    async def make_request(session, semaphore):
        """Make a request and record the result."""
        try:
            async with semaphore:
                start_time = time.time()
                error = None
                
                try:
                    if method == "GET":
                        async with session.get(url, headers=headers, timeout=10) as response:
                            await response.text()
                            status_code = response.status
                    elif method == "POST":
                        async with session.post(url, headers=headers, json=json_data, timeout=10) as response:
                            await response.text()
                            status_code = response.status
                    else:
                        raise ValueError(f"Unsupported method: {method}")
                except asyncio.TimeoutError:
                    error = "Request timed out after 10 seconds"
                    status_code = 0
                except asyncio.CancelledError:
                    # Let cancellation propagate
                    raise
                except Exception as e:
                    error = str(e)
                    status_code = 0
                
                response_time = time.time() - start_time
                # Check if the loop is still running before adding the result
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        result.add_result(response_time, status_code, error)
                except RuntimeError:
                    # If there's an event loop issue, just silently exit
                    pass
        except asyncio.CancelledError:
            # Let cancellation propagate
            raise
        except Exception as e:
            # Catch any other exceptions to prevent task cancellation
            print(f"Error in benchmark request: {e}")
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    result.add_result(0, 0, f"Critical error: {str(e)}")
            except RuntimeError:
                # If there's an event loop issue, just silently exit
                pass
    
    try:
        # Use a timeout for the entire benchmark to prevent hanging
        async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(limit=concurrency)) as session:
            semaphore = asyncio.Semaphore(concurrency)
            tasks = [make_request(session, semaphore) for _ in range(num_requests)]
            
            # Use a timeout to prevent hanging
            await asyncio.wait_for(asyncio.gather(*tasks), timeout=120)
    except asyncio.TimeoutError:
        print(f"Benchmark {name} timed out after 120 seconds")
        # Add timeout results for any missing requests
        completed_requests = len(result.response_times)
        for _ in range(num_requests - completed_requests):
            result.add_result(0, 0, "Benchmark timeout")
    except Exception as e:
        print(f"Benchmark {name} failed: {e}")
        # Add error results for any missing requests
        completed_requests = len(result.response_times)
        for _ in range(num_requests - completed_requests):
            result.add_result(0, 0, f"Benchmark error: {str(e)}")
    
    result.finish()
    return result


async def run_stability_test(
    name: str,
    url: str,
    duration_seconds: int,
    requests_per_second: int,
    ramp_up_seconds: int = 0,
    headers: Optional[Dict] = None,
    json_data: Optional[Dict] = None,
    method: str = "GET"
) -> BenchmarkResult:
    """Run a stability test for the given URL."""
    
    result = BenchmarkResult(name)
    
    # Calculate the delay between requests to achieve the desired RPS
    delay = 1.0 / requests_per_second if requests_per_second > 0 else 1.0
    
    # Use a task set to track all requests for proper cleanup
    task_set = set()
    
    async def make_request(session, idx):
        """Make a request and record the result."""
        current_task = asyncio.current_task()
        try:
            if ramp_up_seconds > 0:
                # Calculate the current RPS based on ramp up
                current_time = time.time() - result.start_time
                if current_time < ramp_up_seconds:
                    current_rps = max(1, (current_time / ramp_up_seconds) * requests_per_second)
                    current_delay = 1.0 / current_rps
                    await asyncio.sleep(current_delay)
            
            start_time = time.time()
            error = None
            
            try:
                if method == "GET":
                    async with session.get(url, headers=headers, timeout=10) as response:
                        await response.text()
                        status_code = response.status
                elif method == "POST":
                    async with session.post(url, headers=headers, json=json_data, timeout=10) as response:
                        await response.text()
                        status_code = response.status
                else:
                    raise ValueError(f"Unsupported method: {method}")
            except asyncio.TimeoutError:
                error = "Request timed out after 10 seconds"
                status_code = 0
            except asyncio.CancelledError:
                # Let cancellation propagate
                raise
            except Exception as e:
                error = str(e)
                status_code = 0
            
            response_time = time.time() - start_time
            # Check if the loop is still running before adding the result
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    result.add_result(response_time, status_code, error)
            except RuntimeError:
                # If there's an event loop issue, just silently exit
                pass
        except asyncio.CancelledError:
            # Let cancellation propagate but clean up task reference
            raise
        except Exception as e:
            # Catch any other exceptions to prevent task cancellation
            print(f"Error in stability test request: {e}")
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    result.add_result(0, 0, f"Critical error: {str(e)}")
            except RuntimeError:
                # If there's an event loop issue, just silently exit
                pass
        finally:
            # Remove this task from the set when done, safely
            try:
                if current_task in task_set:
                    task_set.discard(current_task)
            except RuntimeError:
                # Ignore runtime errors about event loop
                pass
    
    try:
        # Set a timeout slightly longer than the requested duration to allow proper cleanup
        timeout = duration_seconds + ramp_up_seconds + 5
        
        async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(limit=20)) as session:
            end_time = time.time() + duration_seconds
            request_idx = 0
            
            async def run_test():
                nonlocal request_idx
                while time.time() < end_time:
                    # Start a new request
                    task = asyncio.create_task(make_request(session, request_idx))
                    task_set.add(task)
                    request_idx += 1
                    
                    # Wait for the appropriate delay to maintain the desired RPS
                    await asyncio.sleep(delay)
            
            # Run the test with a timeout
            await asyncio.wait_for(run_test(), timeout=timeout)
            
            # Wait for outstanding requests to complete or timeout
            if task_set:
                print(f"Waiting for {len(task_set)} outstanding requests to complete...")
                try:
                    # Use a shorter timeout to avoid event loop issues
                    done, pending = await asyncio.wait(task_set, timeout=3)
                    
                    # Cancel any remaining pending tasks
                    for task in pending:
                        try:
                            task.cancel()
                        except Exception:
                            # Task might already be cancelled/done
                            pass
                    
                    # Clear the task set
                    task_set.clear()
                    
                    # Wait a moment for cancellations to process
                    await asyncio.sleep(0.2)
                except Exception as e:
                    print(f"Error while cleaning up tasks: {e}")
                    # Force clear the task set
                    task_set.clear()
    except asyncio.TimeoutError:
        print(f"Stability test {name} timed out after {timeout} seconds")
    except Exception as e:
        print(f"Stability test {name} failed: {e}")
    
    result.finish()
    return result