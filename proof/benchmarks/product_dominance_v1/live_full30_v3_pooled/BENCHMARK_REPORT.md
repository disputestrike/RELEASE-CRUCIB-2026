# Product Dominance Benchmark Report

- Benchmark version: `2026-04-20.product_dominance.v1`
- Generated at: `2026-04-20T18:26:50.396101+00:00`
- Mode: `live`
- Total runs: `30`
- Success rate: `100.00%`
- Average score: `93.97`
- Average time (seconds): `6.73`

## Per-Run Output

### full_app_build-01-full_app_admin_dashboard
Test: Admin Dashboard Build
Success: Yes
Retries: 0
Time: 3.38 sec
Deploy: n/a
Score: 100.0%

### full_app_build-02-full_app_landing_backend
Test: Landing and Backend Integration
Success: Yes
Retries: 0
Time: 24.76 sec
Deploy: n/a
Score: 100.0%

### full_app_build-03-full_app_saas
Test: SaaS App Build
Success: Yes
Retries: 0
Time: 7.72 sec
Deploy: n/a
Score: 100.0%

### full_app_build-04-full_app_admin_dashboard
Test: Admin Dashboard Build
Success: Yes
Retries: 0
Time: 14.46 sec
Deploy: n/a
Score: 100.0%

### full_app_build-05-full_app_landing_backend
Test: Landing and Backend Integration
Success: Yes
Retries: 0
Time: 30.05 sec
Deploy: n/a
Score: 100.0%

### full_app_build-06-full_app_saas
Test: SaaS App Build
Success: Yes
Retries: 0
Time: 6.38 sec
Deploy: n/a
Score: 100.0%

### full_app_build-07-full_app_admin_dashboard
Test: Admin Dashboard Build
Success: Yes
Retries: 0
Time: 8.88 sec
Deploy: n/a
Score: 100.0%

### full_app_build-08-full_app_landing_backend
Test: Landing and Backend Integration
Success: Yes
Retries: 1
Time: 6.04 sec
Deploy: n/a
Score: 98.2%

### full_app_build-09-full_app_saas
Test: SaaS App Build
Success: Yes
Retries: 0
Time: 5.21 sec
Deploy: n/a
Score: 100.0%

### full_app_build-10-full_app_admin_dashboard
Test: Admin Dashboard Build
Success: Yes
Retries: 0
Time: 3.16 sec
Deploy: n/a
Score: 100.0%

### repair-01-repair_broken_app
Test: Broken App Repair
Success: Yes
Retries: 4
Time: 6.02 sec
Deploy: n/a
Score: 90.1%

### repair-02-repair_broken_app
Test: Broken App Repair
Success: Yes
Retries: 4
Time: 4.11 sec
Deploy: n/a
Score: 90.1%

### repair-03-repair_broken_app
Test: Broken App Repair
Success: Yes
Retries: 4
Time: 4.75 sec
Deploy: n/a
Score: 90.1%

### repair-04-repair_broken_app
Test: Broken App Repair
Success: Yes
Retries: 4
Time: 3.83 sec
Deploy: n/a
Score: 90.1%

### repair-05-repair_broken_app
Test: Broken App Repair
Success: Yes
Retries: 4
Time: 4.14 sec
Deploy: n/a
Score: 90.1%

### continuation-01-continuation_resume_build
Test: Resume Interrupted Build
Success: Yes
Retries: 0
Time: 8.24 sec
Deploy: n/a
Score: 100.0%

### continuation-02-continuation_resume_build
Test: Resume Interrupted Build
Success: Yes
Retries: 0
Time: 8.2 sec
Deploy: n/a
Score: 100.0%

### continuation-03-continuation_resume_build
Test: Resume Interrupted Build
Success: Yes
Retries: 0
Time: 9.52 sec
Deploy: n/a
Score: 100.0%

### continuation-04-continuation_resume_build
Test: Resume Interrupted Build
Success: Yes
Retries: 0
Time: 7.86 sec
Deploy: n/a
Score: 100.0%

### continuation-05-continuation_resume_build
Test: Resume Interrupted Build
Success: Yes
Retries: 0
Time: 9.66 sec
Deploy: n/a
Score: 100.0%

### what_if-01-decision_what_if_strategy
Test: What-if Strategy Comparison
Success: Yes
Retries: 0
Time: 0.0 sec
Deploy: n/a
Score: 83.97%

### what_if-02-decision_what_if_strategy
Test: What-if Strategy Comparison
Success: Yes
Retries: 0
Time: 0.0 sec
Deploy: n/a
Score: 83.97%

### what_if-03-decision_what_if_strategy
Test: What-if Strategy Comparison
Success: Yes
Retries: 0
Time: 0.0 sec
Deploy: n/a
Score: 83.97%

### what_if-04-decision_what_if_strategy
Test: What-if Strategy Comparison
Success: Yes
Retries: 0
Time: 0.0 sec
Deploy: n/a
Score: 83.97%

### what_if-05-decision_what_if_strategy
Test: What-if Strategy Comparison
Success: Yes
Retries: 0
Time: 0.0 sec
Deploy: n/a
Score: 83.97%

### deploy-01-deploy_flow_validation
Test: Deploy and Verify
Success: Yes
Retries: 4
Time: 4.58 sec
Deploy: success
Score: 90.1%

### deploy-02-deploy_flow_validation
Test: Deploy and Verify
Success: Yes
Retries: 4
Time: 3.33 sec
Deploy: success
Score: 90.1%

### deploy-03-deploy_flow_validation
Test: Deploy and Verify
Success: Yes
Retries: 4
Time: 7.21 sec
Deploy: success
Score: 90.1%

### deploy-04-deploy_flow_validation
Test: Deploy and Verify
Success: Yes
Retries: 4
Time: 4.17 sec
Deploy: success
Score: 90.1%

### deploy-05-deploy_flow_validation
Test: Deploy and Verify
Success: Yes
Retries: 4
Time: 6.33 sec
Deploy: success
Score: 90.1%

## Aggregate Results

Total Runs: 30
Success Rate: 100.00%
Avg Time: 6.73 sec
Avg Score: 93.97%

## Category Summary

| Category | Runs | Success Rate | Average Score | Target |
| --- | ---: | ---: | ---: | --- |
| full_app_build | 10 | 100.00% | 99.82% | 85-90 |
| repair | 5 | 100.00% | 90.10% | 80-85 |
| continuation | 5 | 100.00% | 100.00% | 90+ |
| what_if | 5 | 100.00% | 83.97% | 85+ |
| deploy | 5 | 100.00% | 90.10% | 85+ |

## Provider Pool

- Execution mode: `pooled`
- Pool size (configured keys): `5`
- Keys exercised: `5`
- Failover events: `0`
- Total LLM calls: `51`
- Note: Results produced using real pooled Cerebras provider execution (5 keys configured, 5 exercised, 0 failover events).


## Comparison Table

| System | Score | Success Rate |
| --- | ---: | ---: |
| CrucibAI | 93.97% | 100.00% |
| Others | estimate_pending | estimate_pending |

