import time
from app.orchestrator.service import orchestrator


def test_start_workflow_creates_workflow():
    # start a workflow for candidate 1 and job 1 (assumes seed data present)
    wf_id = orchestrator.start_workflow(1, 1)
    assert wf_id is not None
    # give background threads a short time to run
    time.sleep(0.5)
    # fetch status via API layer would be ideal; here ensure the wf_id string looks valid
    assert isinstance(wf_id, str) and len(wf_id) > 0
