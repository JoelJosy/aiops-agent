import argparse
import time
from app_outage_experiment import run_outage_experiment
from downstream_latency_experiment import run_downstream_latency_experiment
from redis_latency_experiment import run_latency_experiment
from redis_outage_experiment import run_redis_outage_experiment
from downstream_failure_experiment import run_downstream_failure_experiment


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AIOps Chaos Experiment Runner")
    parser.add_argument(
        "--fault",
        type=str,
        required=True,
        choices=["redis_latency", "app_outage", "redis_outage", 
                 "downstream_latency", "downstream_failure", 
                 "cpu_spike", "memory_leak"
                ],
        help="The type of fault to inject into the system"
    )
    parser.add_argument(
        "--target",
        type=str,
        default="aiops-app",
        help="Target container/service (default: aiops-app)"
    )
    parser.add_argument(
        "--baseline-seconds", 
        type=int, 
        default=30, 
        help="Normal runtime duration before injection (default: 30)"
    )
    parser.add_argument(
        "--duration-seconds", 
        type=int, 
        default=60, 
        help="Active duration of the injected fault"
    )
    parser.add_argument(
        "--delay-ms", 
        type=int, 
        default=500, 
        help="Millisecond delay (only used for redis_latency)"
    )
    parser.add_argument(
        "--failure-rate",
        type=float,
        default=1.0,
        help="Rate of downstream errors (from 0.0 to 1.0)"
    )
    
    args = parser.parse_args()
    
    print(f"Starting Chaos Experiment Runner")
    print(f"=========================================")
    print(f"Phase 1: Baseline Period ({args.baseline_seconds} seconds)")
    print(f"   Waiting for system to gather normal metric traffic...")
    time.sleep(args.baseline_seconds)
    
    if args.fault == "redis_latency":
        run_latency_experiment(args.duration_seconds, args.delay_ms)
    elif args.fault == "app_outage":
        run_outage_experiment(args.duration_seconds, args.target)
    elif args.fault == "redis_outage":
        run_redis_outage_experiment(args.duration_seconds)
    elif args.fault == "downstream_latency":
        run_downstream_latency_experiment(args.duration_seconds, args.delay_ms)
    elif args.fault == "downstream_failure":
        run_downstream_failure_experiment(args.duration_seconds, args.failure_rate)
        
    print(f"=========================================")