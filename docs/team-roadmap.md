# College Twin — Team Roadmap & Completion Checklist

**Planning snapshot:** 14 September 2026 · **Team:** 3 people · **Baseline:** 12 project weeks

**Goal:** Deliver a demonstrable college digital-twin prototype where a user explores the campus, selects a date, inspects operational problems, closes a room, compares a proposed reassignment, and reviews future attendance risk.

The campus represents the college approximately. Operational records are synthetic. A convincing finished project needs both a recognizable campus and verified behavior connected to its spaces.

## 1. Agree on responsibilities at the first meeting

| Role | Proposed owner | Main responsibility | Review partner |
| --- | --- | --- | --- |
| A — Campus & frontend | You: __________ | 3D accuracy, dashboard, navigation, frontend integration, demo | B reviews data connections |
| B — Backend & simulation | Teammate: __________ | PostgreSQL, APIs, dated state, conflict detection, room closure | C checks calculations |
| C — Data & ML | Teammate: __________ | Generator fixtures, attendance prediction, evaluation evidence | B checks temporal correctness |
| Shared | All three | Requirements, reviews, report sections, presentation, rehearsal | Another teammate signs off |

These are proposed assignments, not commitments already made by teammates. Every task has one accountable owner; reviewers help verify it.

- [ ] Agree on names for A, B and C.
- [ ] Record submission date: __________ and weekly availability: A ___ / B ___ / C ___ hours.
- [ ] Set weekly demo/review time: __________.
- [ ] Confirm the required submission format with the project guide: report, slides, video, source code, deployment.
- [ ] Confirm the core scope below; place additional requests in the parking lot.

**How to mark progress:** `[ ]` means unfinished; `[x]` means implemented AND reviewed against the phase's completion criterion. For ongoing work, append `IN PROGRESS — name`; for a blocker, append `BLOCKED — reason / person needed`. Attach a PR, screenshot, test output, or report link before marking a gate complete.

## 2. Where we are today

| Area | Current position | What still needs attention |
| --- | --- | --- |
| React + FastAPI + PostgreSQL foundation | Implemented | Repeat startup and login on the teammates' machines |
| Authentication and room/dataset reads | Implemented | PostgreSQL integration suite and final startup smoke test |
| Synthetic data generator | Implemented | Deliberate-conflict, sparse-data and shifted-data fixtures |
| 3D campus, floor selection, room panels, search | Implemented | Team validation of geometry and provisional spaces |
| IT/ECE, CSE, opposite ECE and lab buildings | Modeled | Confirm remaining room counts, room labels and facilities |
| Physical-room ↔ synthetic-room mapping | Interface exists; bindings empty | Explicit, edition-specific, reviewed mappings |
| Dated metrics and anomalies | Not implemented | Next core development milestone |
| Room-closure simulation | Not implemented | Depends on verified state/conflict logic |
| Future attendance-risk prediction | Not implemented | Depends on temporal data and evaluation fixtures |
| Final end-to-end demo, report and defense | Not complete | Integrate, measure, document and rehearse |

**Latest recorded checks from this task:** 13 frontend tests and the frontend build passed after the campus updates; 21 non-integration backend tests passed after local configuration changes. These are prior run results, not a fresh run for this document. Eight PostgreSQL integration tests remain unverified. Docker work remains deferred.

### Campus facts to take into the team discussion

| Building | Ground | First | Second | Location / caveat |
| --- | --- | --- | --- | --- |
| Original IT/ECE block | Two provisional labs | IT | ECE, from earlier confirmation | Girls left, boys right from garden |
| CSE | CSE second year | CSE third year | MCA | Right of IT; boys left, girls right |
| Separate ECE building | Provisional interior | Provisional ECE interior | Provisional ECE interior | Opposite IT; boys left, girls right |
| Lab building | Mechanical labs | CSE / MCA labs | IT / AI & DS labs | Opposite CSE; lab partitions provisional |

The separate ECE building does not yet establish that ECE moved out of the original block. Confirm that explicitly before changing either allocation. The new CSE ground-floor room count and G1–G7 labels are also provisional.

## 3. Delivery sequence

The original baseline reserves weeks 1–3 for design and foundation. The table below schedules the remaining work from **project week 4**, not a new twelve-week extension. These are effort-planning windows, not elapsed weeks or promised dates. Add calendar dates after the team confirms its deadline; if less time remains, remove optional work first.

| Window | Milestone | Lead | Tangible result |
| --- | --- | --- | --- |
| Start of week 4 | Close foundation gaps + campus/data agreement | All; B accountable | Reliable local startup, integration evidence, reviewed spatial mapping plan |
| Weeks 4–5 | M2 — State and anomalies | B, with A + C | Date-driven dashboard and verified conflict list |
| Weeks 6–7 | M3 — Room closure | B + A | Baseline/disruption/reassignment comparison |
| Weeks 6–8 | M4 — Attendance risk, alongside M3 | C + A | Evaluated future-risk model and results screen |
| Weeks 9–10 | M5 — Integration and stabilization | A, with B + C | Complete campus-to-decision demo |
| Week 11 | M6 — Evaluation, report, defense | All | Submission package and rehearsed demonstration |
| Week 12 | Contingency | All | Resolve failed gates; final submission check |

**Dependencies:** Foundation → M2 → M3. Verified temporal data supports M4; M3 and M4 can run alongside each other. M2 + M3 + M4 feed M5, then M6. A builds reviewed mock screens during M2; frontend work must not wait until week 9. Save report evidence throughout every phase.

## 4. Markable implementation checklist

### Phase A — Reliable foundation and campus agreement

**Lead: B · Support: A/C · Target: start of week 4**

- [ ] **A1 · B:** Demonstrate clean startup, health check, login, logout and dataset selection using the saved local configuration; repeat on each teammate's machine.
- [ ] **A2 · B:** Run the eight pending integration tests against a separate PostgreSQL test database; save results and fix failures. Do not test destructively against the demo database.
- [ ] **A3 · A:** Walk through all four detailed buildings with the team; record confirmed facts versus approximations, including the ECE allocation question above.
- [ ] **A4 · A:** Confirm CSE ground-floor rooms, separate ECE interiors, lab partitions, restroom sides and floor naming; correct only facts the team can verify.
- [ ] **A5 · A/B:** List the physical spaces needed for the demo and match them explicitly to room IDs in a chosen synthetic edition; do not match by label alone.
- [ ] **A6 · C:** Check that the synthetic edition has the room types and capacities needed by the demo. If it does not, create a reproducible new edition rather than altering a frozen one.
- [ ] **A7 · A/B:** Connect reviewed mappings, verify cross-edition isolation, and show “No linked dataset record” for unmapped spaces.

**Gate A:** All teammates can start the app; integration checks have evidence; the campus has a reviewed uncertainty list; at least the selected demo rooms have correct mappings.

### Phase B — M2: Dated state and conflict detection

**Lead: B · A builds the UI at the same time · C supplies examples · Target: weeks 4–5**

- [ ] **B1 · All:** Agree on snapshot inputs/outputs: dataset, cutoff date/time, analysis window, room/attendance/workload metrics, provenance and error states.
- [ ] **B2 · C:** Create small hand-calculated clean and conflicting examples, plus empty, missing-attendance and cancelled-class cases.
- [ ] **B3 · B:** Implement dated snapshots that exclude records not known at the cutoff and expose the denominator behind each rate.
- [ ] **B4 · B:** Detect room overlaps, faculty overlaps, section overlaps, capacity violations and incompatible room/lab types.
- [ ] **B5 · A:** Build date selection, metric panels, conflict list and room details against the agreed mock responses.
- [ ] **B6 · A/B:** Replace mocks with real endpoints; selecting a mapped campus room filters the same snapshot and conflict data.
- [ ] **B7 · B/C:** Test known totals, interval boundaries, duplicate conflicts, missing observations and zero availability. Label scheduled utilization separately from measured occupancy.

**Gate B:** A selected synthetic date produces explainable metrics; every conflict rule matches the hand-checked examples; the 3D view and dashboard agree.

### Phase C — M3: Close a room and compare the outcome

**Lead: B · Support: A/C · Target: weeks 6–7 · Requires Gate B**

- [ ] **C1 · B:** Accept a baseline snapshot, room and closure interval; identify affected sessions without changing source data.
- [ ] **C2 · B:** Implement deterministic reassignment respecting capacity, room type, availability, and faculty/section constraints.
- [ ] **C3 · B:** Persist completed scenario results with provenance and replay protection; make unresolved sessions explicit.
- [ ] **C4 · A:** Add closure selection from a mapped room and compare baseline, disrupted and reassigned schedules; highlight affected spaces in the model.
- [ ] **C5 · C/B:** Verify successful reassignment, no available room, incompatible labs, multiple displaced classes, no affected classes, and unchanged baseline data.

**Gate C:** The same input reproduces the same result. A teammate can trace each moved class and see why any class remains unresolved.

### Phase D — M4: Future attendance-risk prediction

**Lead: C · Support: B/A · Target: weeks 6–8 · Runs alongside Phase C**

- [ ] **D1 · C/B:** Freeze the future target, prediction horizon, feature cutoff and minimum history; predicting today's threshold is not the ML task.
- [ ] **D2 · C:** Build temporal train/validation/test splits, with preprocessing fit on training data only and no future attendance leakage.
- [ ] **D3 · C:** Evaluate a simple rule/dummy baseline and logistic regression; choose thresholds using validation data only.
- [ ] **D4 · C:** Record precision, recall, F1, PR-AUC and confusion matrices where defined; include sparse-history, imbalance and shifted-seed limitations.
- [ ] **D5 · B/C:** Save trusted model artifacts and manifests; expose predictions with model version, data edition, cutoff and insufficient-data handling.
- [ ] **D6 · A:** Build the risk view with clear synthetic-data labeling and model provenance; never present predictions as confirmed future outcomes.

**Gate D:** Evaluation is reproducible on untouched test data. Report the actual comparison, even if the model does not beat the baseline.

### Phase E — M5: Integrate and stabilize

**Lead: A · Support: B/C · Target: weeks 9–10**

- [ ] **E1 · A/B:** Complete one flow: login → campus room → dated state → conflict → closure → comparison → attendance-risk view.
- [ ] **E2 · A:** Verify keyboard navigation, narrow-screen layout, search, floor changes, loading/empty/error states and WebGL fallback.
- [ ] **E3 · B:** Check viewer/planner permissions, origin/CSRF protection, session expiry, invalid inputs and dataset/model mismatches.
- [ ] **E4 · All:** Run the required frontend, backend, PostgreSQL integration and end-to-end checks; save outputs tied to the tested revision.
- [ ] **E5 · B/C:** Measure snapshot, scenario and prediction response times on the demo machine. Record hardware, dataset size, repetitions and cold/warm conditions; compare with the blueprint's targets.
- [ ] **E6 · A:** Measure campus interaction smoothness on the presentation laptop and reduce rendering cost if necessary.
- [ ] **E7 · All:** Freeze a known-working demo edition and revision; rehearse database restore/startup and test a presentation backup video.

**Gate E:** Another teammate completes the entire demo without developer intervention. No required feature uses fabricated metrics or hidden mock results.

### Phase F — M6: Report, presentation and submission

**Lead: All · Target: week 11; week 12 protects the deadline**

- [ ] **F1 · A:** Write campus/UI design, reference sources, confirmed versus provisional geometry, navigation and integration sections.
- [ ] **F2 · B:** Write architecture, database, APIs, state calculations, conflict rules and simulation sections.
- [ ] **F3 · C:** Write data generation, future-risk methodology, experimental setup, results and limitations sections.
- [ ] **F4 · All:** Merge the report, verify references and screenshots, and distinguish implemented, optional and future features.
- [ ] **F5 · All:** Prepare slides covering the problem, architecture, demo, measured results, limitations and individual contributions.
- [ ] **F6 · All:** Rehearse a 5–7 minute demo and viva answers: Why a twin? Why synthetic data? How is leakage avoided? How do you verify a reassignment?
- [ ] **F7 · All:** Package source, dependency files, setup guide, reproducible dataset/model instructions, evaluation outputs, report, slides and video. Exclude passwords and local secrets.
- [ ] **F8 · Reviewer:** Start from the documented setup, complete the demo, check every submission requirement, and sign off: __________ / date __________.

**Gate F:** The submission is reproducible, understandable, backed by actual results, and ready before the deadline.

## 5. Weekly team discussion template

Use a 30-minute meeting: 5 minutes progress, 10 minutes working demo, 10 minutes blockers/review, 5 minutes next commitments. Demonstrate working behavior rather than only reporting code written.

**Meeting date:** __________ · **Current phase:** __________

| Person | Completed task IDs + evidence | Next task IDs | Blocker / help needed | Due date |
| --- | --- | --- | --- | --- |
| A | | | | |
| B | | | | |
| C | | | | |

- [ ] Review last meeting's commitments and task evidence.
- [ ] Check the current phase's gate; name the exact unmet condition.
- [ ] Agree on API/data changes before parallel implementation.
- [ ] Assign a reviewer and realistic date to each next task.
- [ ] Update this checklist and capture report evidence.

**Decision log**

| Date | Decision / reason | Owner | Affected tasks |
| --- | --- | --- | --- |
| | | | |

## 6. Scope protection and final definition of done

**Required:** Reliable startup, synthetic data, reviewed campus spaces, explicit room mappings, dated metrics, conflict detection, one verified room-closure scenario, evaluated future attendance risk, integrated demo and academic deliverables.

**Parking lot — only after required gates pass:** More building detail, photorealism, additional scenarios, chatbot/RAG, optional LLM explanations, live sensors, real-time synchronization, and cloud hosting. Docker remains deferred unless the team or submission rules require it; the local run must still be reproducible. Do not delay metrics and simulation to perfect every campus building.

- [ ] All required phase gates are signed off with evidence.
- [ ] Every shown number has an identified source, time window and meaning.
- [ ] Approximate geometry and synthetic data are visibly distinguished from verified real-world facts.
- [ ] The demo works without an LLM key or external AI service.
- [ ] Known limitations and unresolved optional work are recorded honestly.
- [ ] The report, slides, video and tested code describe the same final system.

**Primary working references:** [Technical blueprint](blueprint.md) · [Campus model and corrections](campus-model.md) · [Setup instructions](../README.md)
