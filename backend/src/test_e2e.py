import sys
import io
import redis
from fastapi.testclient import TestClient

sys.path.insert(0, "src")
from app import app
from jobs.manager import JobManager
from workers.tasks import process_job_task

def run_all_e2e_tests():
    print("=" * 70)
    print("RUNNING END-TO-END INTEGRATION TEST SUITE")
    print("=" * 70)

    client = TestClient(app)

    # 1. Health check
    res = client.get("/health")
    assert res.status_code == 200, f"Health check failed: {res.text}"
    print("✓ Health check passed")

    # 2. Upload CSV & Create Job
    sample_csv = 'Mfg_Part_Num,Part_Desc,E1_Brand,Unilog_Brand,DIB_Brand,Part_Manuf\nDCB518ASTS06G,"DCB518ASTS06G Diablo 1/2""x18"" - Sanding Belt 6pc",-- Unbranded --,-- No Unilog Brand --,-- No DIB Brand --,Freud Inc (2435)\n'
    files = {"file": ("e2e_sample.csv", io.BytesIO(sample_csv.encode("utf-8")), "text/csv")}
    post_res = client.post("/api/jobs", files=files)
    assert post_res.status_code == 200, f"Create job failed: {post_res.text}"
    job_data = post_res.json()
    job_id = job_data["job_id"]
    assert job_data["status"] == "queued"
    assert job_data["total"] == 1
    print(f"✓ Job created successfully: ID = {job_id}")

    # 3. Synchronous Celery Task Execution for E2E validation
    manager = JobManager()
    job = manager.get_job(job_id)
    assert job is not None
    input_file_path = f"uploads/{job_id}_e2e_sample.csv"
    output_path = job.output_path or f"outputs/{job_id}_enriched.csv"
    task_res = process_job_task(job_id, input_file_path, output_path, limit=1)
    assert task_res["job_id"] == job_id
    print("DEBUG task_res:", task_res)
    assert task_res["processed"] == 1
    print(f"✓ Celery task completed job {job_id}: {task_res}")

    # 4. Check Redis Job Status Update
    updated_job = client.get(f"/api/jobs/{job_id}").json()
    assert updated_job["status"] == "completed"
    assert updated_job["completed"] == 1
    print(f"✓ Redis job state verified: status={updated_job['status']}, completed={updated_job['completed']}")

    # 5. Check Redis Stream Events
    r = redis.Redis(host="localhost", port=6380, db=0, decode_responses=True)
    events = r.xrange(f"job:{job_id}:events")
    assert len(events) >= 3, f"Expected events in stream, got {len(events)}"
    import json
    event_types = [json.loads(edata["data"])["type"] for _, edata in events]
    assert "job.started" in event_types
    assert "product.started" in event_types
    assert "job.completed" in event_types
    print(f"✓ Redis event stream verified ({len(events)} events): {event_types}")

    # 6. Check Product Detail Endpoint
    prod_res = client.get(f"/api/jobs/{job_id}/products/0")
    assert prod_res.status_code == 200, f"Product detail failed: {prod_res.text}"
    prod_data = prod_res.json()
    assert prod_data["index"] == 0
    assert prod_data["mpn"] == "DCB518ASTS06G"
    print(f"✓ Product detail endpoint verified: MPN={prod_data['mpn']}, Manufacturer={prod_data['manufacturer']}")

    # 7. Check CSV Download Endpoint
    download_res = client.get(f"/api/jobs/{job_id}/download")
    assert download_res.status_code == 200, f"Download failed: {download_res.text}"
    assert "text/csv" in download_res.headers["content-type"]
    print("✓ CSV download endpoint verified")

    print("=" * 70)
    print("ALL 7 END-TO-END INTEGRATION TESTS PASSED SUCCESSFULLY!")
    print("=" * 70)

if __name__ == "__main__":
    run_all_e2e_tests()
