"""
Fase 5: Latency Monitoring & Metrics

Track P50, P95, P99 latencies per stage.
Identify bottlenecks en hybrid retrieval.

Uso:
    monitor = LatencyMonitor()
    
    with monitor.measure_stage('bm25'):
        results = bm25.search(query)
    
    with monitor.measure_stage('dense'):
        results = dense.search(query)
    
    monitor.report()  # Print latency report
"""

import time
import logging
from typing import Dict, List
from contextlib import contextmanager

logger = logging.getLogger(__name__)


class LatencyMonitor:
    """
    Monitor latencies per retrieval stage.
    
    Stages:
    - bm25: BM25 keyword search
    - dense: Dense embedding search
    - fusion: RRF or score fusion
    - rerank: Cross-encoder reranking
    - total: Total query latency
    """
    
    def __init__(self):
        """Initialize latency monitor"""
        self.stage_latencies = {
            'bm25': [],
            'dense': [],
            'fusion': [],
            'rerank': [],
            'total': [],
        }
        
        self._measurement_stack = []  # For nested measurements
    
    @contextmanager
    def measure_stage(self, stage_name: str):
        """
        Context manager to measure stage latency.
        
        Usage:
            with monitor.measure_stage('bm25'):
                results = bm25.search(query)
        
        Args:
            stage_name: Name of the stage ('bm25', 'dense', etc.)
        """
        # Auto-initialize stage if not exists
        if stage_name not in self.stage_latencies:
            self.stage_latencies[stage_name] = []
        
        start = time.perf_counter()
        try:
            yield
        finally:
            elapsed_ms = (time.perf_counter() - start) * 1000
            self.stage_latencies[stage_name].append(elapsed_ms)
            logger.debug(f"{stage_name} latency: {elapsed_ms:.2f}ms")
    
    def record_latency(self, stage_name: str, latency_ms: float):
        """
        Manually record latency (if not using context manager).
        
        Args:
            stage_name: Stage name
            latency_ms: Latency in milliseconds
        """
        if stage_name not in self.stage_latencies:
            self.stage_latencies[stage_name] = []
        
        self.stage_latencies[stage_name].append(latency_ms)
    
    def get_percentile(self, stage_name: str, p: int) -> float:
        """
        Get latency percentile for a stage.
        
        Args:
            stage_name: Stage name
            p: Percentile (50, 95, 99)
        
        Returns:
            Latency at percentile (ms)
        """
        latencies = self.stage_latencies.get(stage_name, [])
        
        if not latencies:
            return 0.0
        
        # Simple percentile calculation
        sorted_latencies = sorted(latencies)
        index = max(0, int(len(sorted_latencies) * p / 100) - 1)
        return sorted_latencies[index]
    
    def get_stats(self, stage_name: str) -> Dict:
        """
        Get full statistics for a stage.
        
        Args:
            stage_name: Stage name
        
        Returns:
            Dict with min, max, mean, p50, p95, p99, count
        """
        latencies = self.stage_latencies.get(stage_name, [])
        
        if not latencies:
            return {
                'stage': stage_name,
                'count': 0,
                'min': 0,
                'max': 0,
                'mean': 0,
                'p50': 0,
                'p95': 0,
                'p99': 0,
            }
        
        sorted_latencies = sorted(latencies)
        
        return {
            'stage': stage_name,
            'count': len(latencies),
            'min': min(latencies),
            'max': max(latencies),
            'mean': sum(latencies) / len(latencies),
            'p50': self.get_percentile(stage_name, 50),
            'p95': self.get_percentile(stage_name, 95),
            'p99': self.get_percentile(stage_name, 99),
        }
    
    def get_all_stats(self) -> Dict:
        """Get stats for all stages"""
        return {
            stage: self.get_stats(stage)
            for stage in self.stage_latencies.keys()
        }
    
    def report(self, title: str = "LATENCY REPORT"):
        """
        Print latency report.
        
        Args:
            title: Report title
        """
        print("\n" + "="*80)
        print(f"{title} (milliseconds)")
        print("="*80)
        
        # Header
        print(f"\n{'Stage':<15} | {'Count':<6} | {'Min':<7} | {'Mean':<7} | "
              f"{'P50':<7} | {'P95':<7} | {'P99':<7} | {'Max':<7}")
        print("-"*80)
        
        # Rows
        for stage in ['bm25', 'dense', 'fusion', 'rerank', 'total']:
            stats = self.get_stats(stage)
            
            print(f"{stats['stage']:<15} | {stats['count']:<6} | "
                  f"{stats['min']:<7.1f} | {stats['mean']:<7.1f} | "
                  f"{stats['p50']:<7.1f} | {stats['p95']:<7.1f} | "
                  f"{stats['p99']:<7.1f} | {stats['max']:<7.1f}")
        
        print("="*80 + "\n")
    
    def get_summary(self) -> Dict:
        """Get summary of all stages"""
        all_stats = self.get_all_stats()
        
        # Identify bottleneck
        p95_times = {
            stage: stats['p95']
            for stage, stats in all_stats.items()
            if stats['count'] > 0
        }
        
        bottleneck = max(p95_times, key=p95_times.get) if p95_times else None
        
        return {
            'total_queries': self.stage_latencies['total'].__len__(),
            'all_stages': all_stats,
            'bottleneck_stage': bottleneck,
            'bottleneck_p95': p95_times.get(bottleneck, 0) if bottleneck else 0,
        }
    
    def reset(self):
        """Clear all measurements"""
        for stage in self.stage_latencies:
            self.stage_latencies[stage] = []
        logger.info("Latency monitor reset")
    
    def compare_stages(self, stage1: str, stage2: str) -> Dict:
        """
        Compare latencies between two stages.
        
        Args:
            stage1: First stage name
            stage2: Second stage name
        
        Returns:
            Dict with comparison metrics
        """
        stats1 = self.get_stats(stage1)
        stats2 = self.get_stats(stage2)
        
        if stats1['mean'] == 0 or stats2['mean'] == 0:
            return {'error': 'Insufficient data'}
        
        return {
            'stage1': stage1,
            'stage2': stage2,
            'mean_ratio': stats2['mean'] / stats1['mean'],
            'p95_ratio': stats2['p95'] / stats1['p95'],
            'mean_diff_ms': stats2['mean'] - stats1['mean'],
            'p95_diff_ms': stats2['p95'] - stats1['p95'],
        }


class LatencyBudget:
    """
    Latency budget tracker for SLA compliance.
    
    SLA Example:
    - P95 latency: < 500ms
    - P99 latency: < 1000ms
    - Mean latency: < 100ms
    """
    
    def __init__(self, p50_ms=50, p95_ms=500, p99_ms=1000):
        """
        Initialize latency budget.
        
        Args:
            p50_ms: Target P50 latency
            p95_ms: Target P95 latency (most important)
            p99_ms: Target P99 latency
        """
        self.budget = {
            'p50': p50_ms,
            'p95': p95_ms,
            'p99': p99_ms,
        }
        self.monitor = LatencyMonitor()
    
    def check_sla(self, stage_name: str = 'total') -> Dict:
        """
        Check if SLA is met for a stage.
        
        Args:
            stage_name: Stage to check ('total' for overall)
        
        Returns:
            Dict with SLA status and violations
        """
        stats = self.monitor.get_stats(stage_name)
        
        violations = []
        
        if stats['p50'] > self.budget['p50']:
            violations.append(f"P50 {stats['p50']:.0f}ms > {self.budget['p50']}ms")
        
        if stats['p95'] > self.budget['p95']:
            violations.append(f"P95 {stats['p95']:.0f}ms > {self.budget['p95']}ms")
        
        if stats['p99'] > self.budget['p99']:
            violations.append(f"P99 {stats['p99']:.0f}ms > {self.budget['p99']}ms")
        
        return {
            'stage': stage_name,
            'sla_met': len(violations) == 0,
            'violations': violations,
            'current_stats': stats,
            'budget': self.budget,
        }


if __name__ == "__main__":
    # Test script
    import random
    
    print("\n" + "="*80)
    print("LATENCY MONITOR TEST")
    print("="*80)
    
    monitor = LatencyMonitor()
    
    # Simulate latencies
    for i in range(100):
        # BM25 latency: 10-50ms
        with monitor.measure_stage('bm25'):
            time.sleep(random.uniform(0.01, 0.05))
        
        # Dense latency: 50-200ms
        with monitor.measure_stage('dense'):
            time.sleep(random.uniform(0.05, 0.2))
        
        # Fusion latency: 5-10ms
        with monitor.measure_stage('fusion'):
            time.sleep(random.uniform(0.005, 0.01))
        
        # Total
        total_latency = (
            monitor.stage_latencies['bm25'][-1] +
            monitor.stage_latencies['dense'][-1] +
            monitor.stage_latencies['fusion'][-1]
        )
        monitor.record_latency('total', total_latency)
    
    # Report
    monitor.report()
    
    # Summary
    print("\nSUMMARY:")
    summary = monitor.get_summary()
    print(f"Total queries: {summary['total_queries']}")
    print(f"Bottleneck stage: {summary['bottleneck_stage']} "
          f"({summary['bottleneck_p95']:.1f}ms P95)")
    
    # SLA Check
    print("\nSLA CHECK:")
    budget = LatencyBudget(p50_ms=50, p95_ms=300, p99_ms=500)
    budget.monitor = monitor
    
    sla_check = budget.check_sla('total')
    print(f"SLA Met: {sla_check['sla_met']}")
    if sla_check['violations']:
        print("Violations:")
        for v in sla_check['violations']:
            print(f"  - {v}")
