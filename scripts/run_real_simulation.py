import sys
import time
from episwarm.service.jobs import JobManager
from episwarm.service.models import RunCreateRequest, JobStatus

def run_job(scenario_id: str = "targeted_containment", scale_agents: int = 50000, horizon_days: int = 60):
    jm = JobManager()
    req = RunCreateRequest(
        region_id="example_synthetic",
        disease_id="respiratory_generic",
        scenario_id=scenario_id,
        scale_agents=scale_agents,
        horizon_days=horizon_days,
        behavior_mode="rule",
        use_mock=False,
    )

    print(f"Submitting {scale_agents} agents, {horizon_days}-day simulation job (scenario: {scenario_id})...")
    start_time = time.time()
    job = jm.submit_job(req)
    job_id = job.job_id
    print(f"Job submitted: {job_id}. Waiting for execution to complete...")

    while True:
        record = jm.get_job(job_id)
        elapsed = time.time() - start_time
        print(f"[{elapsed:.1f}s] Status: {record.status.value}, Day: {record.current_day}/{record.total_days}, Progress: {record.progress*100:.1f}%")
        if record.status in (JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED):
            break
        time.sleep(1.5)

    if record.status == JobStatus.COMPLETED:
        ts = jm.get_timeseries(job_id)
        cap = jm.get_capacity(job_id)
        isymp = ts.daily_states.get('I_symp', [0])
        iasymp = ts.daily_states.get('I_asymp', [0])
        total_inf = [s + a for s, a in zip(isymp, iasymp)]
        print(f"\nSUCCESS! Simulation {job_id} completed cleanly!")
        print(f"Scenario: {scenario_id}")
        print(f"Peak infectious: {max(total_inf)}")
        print(f"Total deaths: {ts.daily_deaths[-1]}")
        print(f"Peak hospital demand: {max(cap.daily_hospital_demand)}")
        return job_id
    else:
        print("\nFAILED! Error:", getattr(record, 'error', None))
        return None

if __name__ == "__main__":
    scenario = sys.argv[1] if len(sys.argv) > 1 else "baseline"
    run_job(scenario)
