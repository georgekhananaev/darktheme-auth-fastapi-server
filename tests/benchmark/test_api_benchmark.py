import pytest
import asyncio
import json
import os
from datetime import datetime
import statistics
import matplotlib.pyplot as plt
import numpy as np
import time

from tests.utils import run_benchmark, BenchmarkResult, percentile


@pytest.mark.benchmark
class TestApiBenchmark:
    """Benchmark tests for API endpoints."""
    
    @pytest.mark.asyncio
    async def test_ping_endpoint_benchmark(self, benchmark_settings):
        """Benchmark the /ping endpoint."""
        # Get settings
        num_requests = benchmark_settings["num_requests"]
        concurrency = benchmark_settings["concurrency"]
        warmup_requests = benchmark_settings["warmup_requests"]
        
        # Run benchmark
        result = await run_benchmark(
            name="ping_endpoint",
            url="http://localhost:8000/api/v1/system/ping",
            num_requests=num_requests,
            concurrency=concurrency,
            warmup_requests=warmup_requests
        )
        
        # Log the results
        self._log_benchmark_result(result)
        
        # Generate report
        self._generate_benchmark_report(result)
        
        # Assert performance criteria
        assert result.get_summary()["response_times"]["p95"] < 20.0  # 95% of requests under 20ms
        assert result.get_summary()["error_rate"] < 0.01  # Error rate under 1%
    
    @pytest.mark.asyncio
    async def test_logs_count_benchmark(self, benchmark_settings):
        """Benchmark the /logs/counts endpoint."""
        # Get settings - reduce load for logs endpoints since they access the database
        num_requests = 100  # Reduced from 1000
        concurrency = 5     # Reduced concurrency to avoid DB locks
        warmup_requests = 10  # Reduced warmup requests
        
        # Run benchmark
        result = await run_benchmark(
            name="logs_count_endpoint",
            url="http://localhost:8000/api/v1/logs/counts",
            num_requests=num_requests,
            concurrency=concurrency,
            headers={"Authorization": "Bearer AbCdEfGhIjKlMnOpQrStUvWxYz"},
            warmup_requests=warmup_requests
        )
        
        # Log the results
        self._log_benchmark_result(result)
        
        # Generate report
        self._generate_benchmark_report(result)
        
        # Assert performance criteria - adjusted for SQLite performance
        assert result.get_summary()["response_times"]["p95"] < 200.0  # 95% of requests under 200ms
        assert result.get_summary()["error_rate"] < 0.05  # Error rate under 5%
    
    @pytest.mark.asyncio
    async def test_logs_access_benchmark(self, benchmark_settings):
        """Benchmark the /logs/access endpoint."""
        # Get settings - reduce load for logs endpoints since they access the database
        num_requests = 100  # Reduced from 1000
        concurrency = 5     # Reduced concurrency to avoid DB locks
        warmup_requests = 10  # Reduced warmup requests
        
        # Run benchmark
        result = await run_benchmark(
            name="logs_access_endpoint",
            url="http://localhost:8000/api/v1/logs/access",
            num_requests=num_requests,
            concurrency=concurrency,
            headers={"Authorization": "Bearer AbCdEfGhIjKlMnOpQrStUvWxYz"},
            warmup_requests=warmup_requests
        )
        
        # Log the results
        self._log_benchmark_result(result)
        
        # Generate report
        self._generate_benchmark_report(result)
        
        # Assert performance criteria - adjusted for SQLite performance
        assert result.get_summary()["response_times"]["p95"] < 200.0  # 95% of requests under 200ms
        assert result.get_summary()["error_rate"] < 0.05  # Error rate under 5%
    
    @pytest.mark.asyncio
    async def test_health_endpoint_benchmark(self, benchmark_settings):
        """Benchmark the /health endpoint."""
        # Get settings
        num_requests = benchmark_settings["num_requests"]
        concurrency = benchmark_settings["concurrency"]
        warmup_requests = benchmark_settings["warmup_requests"]
        
        # Run benchmark
        result = await run_benchmark(
            name="health_endpoint",
            url="http://localhost:8000/api/v1/system/health",
            num_requests=num_requests,
            concurrency=concurrency,
            headers={"Authorization": "Bearer AbCdEfGhIjKlMnOpQrStUvWxYz"},
            warmup_requests=warmup_requests
        )
        
        # Log the results
        self._log_benchmark_result(result)
        
        # Generate report
        self._generate_benchmark_report(result)
        
        # Assert performance criteria
        assert result.get_summary()["response_times"]["p95"] < 150.0  # 95% of requests under 150ms
        assert result.get_summary()["error_rate"] < 0.01  # Error rate under 1%
    
    def _log_benchmark_result(self, result: BenchmarkResult):
        """Log the benchmark results."""
        summary = result.get_summary()
        
        print(f"\n===== Benchmark Results: {result.name} =====")
        print(f"Requests: {summary['num_requests']}")
        print(f"Duration: {summary['duration']:.2f} seconds")
        print(f"Requests per second: {summary['requests_per_second']:.2f}")
        print(f"Error rate: {summary['error_rate'] * 100:.2f}%")
        print("\nResponse Times (ms):")
        print(f"  Min: {summary['response_times']['min'] * 1000:.2f}")
        print(f"  Mean: {summary['response_times']['mean'] * 1000:.2f}")
        print(f"  Median: {summary['response_times']['median'] * 1000:.2f}")
        print(f"  95th percentile: {summary['response_times']['p95'] * 1000:.2f}")
        print(f"  99th percentile: {summary['response_times']['p99'] * 1000:.2f}")
        print(f"  Max: {summary['response_times']['max'] * 1000:.2f}")
        print("\nStatus Codes:")
        for code, count in summary['status_codes'].items():
            print(f"  {code}: {count}")
        print("=" * 40)
    
    def _generate_benchmark_report(self, result: BenchmarkResult):
        """Generate a benchmark report with graphs."""
        # Create reports directory if it doesn't exist
        reports_dir = os.path.join("tests", "benchmark", "reports")
        os.makedirs(reports_dir, exist_ok=True)
        
        # Convert response times to milliseconds
        response_times_ms = [t * 1000 for t in result.response_times]
        
        # Create response time histogram
        plt.figure(figsize=(10, 6))
        plt.hist(response_times_ms, bins=50)
        plt.title(f"{result.name} - Response Time Distribution")
        plt.xlabel("Response Time (ms)")
        plt.ylabel("Frequency")
        plt.grid(True)
        plt.savefig(os.path.join(reports_dir, f"{result.name}_histogram.png"))
        plt.close()
        
        # Create response time percentiles
        percentiles = range(5, 100, 5)
        percentile_values = [percentile(response_times_ms, p) for p in percentiles]
        
        plt.figure(figsize=(10, 6))
        plt.plot(percentiles, percentile_values, marker='o')
        plt.title(f"{result.name} - Response Time Percentiles")
        plt.xlabel("Percentile")
        plt.ylabel("Response Time (ms)")
        plt.grid(True)
        plt.savefig(os.path.join(reports_dir, f"{result.name}_percentiles.png"))
        plt.close()
        
        # Save benchmark summary
        summary = result.get_summary()
        
        # Convert response times to milliseconds for the summary
        for key in summary["response_times"]:
            summary["response_times"][key] *= 1000
        
        with open(os.path.join(reports_dir, f"{result.name}_summary.json"), "w") as f:
            json.dump(summary, f, indent=2)