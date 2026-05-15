Feature request: PlantLab device reliability soak test and recovery hardening.

Context:
BLE provisioning is working. Camera capture and image visibility are working. GCP deployment is working.

Goal:
Run and improve long-duration reliability for the full PlantLab stack.

Planner only:
- Study current master firmware, camera firmware, backend heartbeat/image/readings APIs, and mobile refresh behavior.
- Create a soak test plan.
- Do not implement yet.

Focus areas:
1. Master heartbeat reliability
2. Camera heartbeat reliability
3. Sensor reading upload reliability
4. Scheduled capture reliability
5. Image upload retry behavior
6. Device reboot recovery
7. Wi-Fi reconnect behavior
8. Backend command lifecycle
9. Mobile data refresh behavior
10. Cloud Run/GCS log visibility

Desired validation:
- 1 hour test 
- record failures clearly
- identify retry/backoff gaps
- avoid duplicate images/readings if retry happens
- make device status understandable in mobile app

Planner output:
1. Current reliability flow summary
2. Soak test plan
3. Metrics/logs to collect
4. Failure scenarios
5. Firmware improvements if needed
6. Backend improvements if needed
7. Mobile visibility improvements if needed
8. Test checklist
9. Release readiness checklist
10. Risks and assumptions