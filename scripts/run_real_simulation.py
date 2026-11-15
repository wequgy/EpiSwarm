import time
from episwarm.service.jobs import JobManager
from episwarm.service.models import RunCreateRequest, JobStatus

jm = JobManager()
req = RunCreateRequest(
    region_id="example_synthetic",
    disease_id="respiratory_generic",
    scenario_id="targeted_containment",
    scale_agents=50000,
    horizon_days=60,
    behavior_mode="rule",
    use_mock=False,
)

print("Submitting 50,000 agents, 60-day simulation job to backend engine...")
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
    sp = jm.get_spatial(job_id)
    print("\nSUCCESS! Simulation completed cleanly!")
    print(f"Total days: {ts.horizon_days}")
    print(f"Peak infectious: {max(ts.daily_states.get('I', [0]))}")
    print(f"Total deaths: {ts.daily_deaths[-1]}")
    print(f"Peak hospital demand: {max(cap.daily_hospital_demand)}")
    print(f"Monitored spatial areas: {len(sp.areas)}")
else:
    print("\nFAILED! Error:", getattr(record, 'error', None))
