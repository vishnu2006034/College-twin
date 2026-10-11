# College Twin — Team Roadmap & Completion Checklist

**Planning snapshot:** 22 September 2026 · **Team:** 3 people · **Baseline:** 12 project weeks

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
| React + FastAPI + PostgreSQL foundation | Implemented; one-command local launcher and real HTTP startup lifecycle verified | Repeat startup and login on the teammates' machines; see [M1 handoff](m1-verification.md) |
| Authentication and room/dataset reads | Implemented; PostgreSQL suite verified | Repeat startup on teammates' machines |
| Synthetic data generator | Implemented | Deliberate-conflict, sparse-data and shifted-data fixtures |
| 3D campus, floor selection, room panels, search | Implemented | Team validation of geometry and provisional spaces |
| IT/ECE, CSE, opposite ECE and lab buildings | Modeled | Confirm remaining room counts, room labels and facilities |
| Physical-room ↔ synthetic-room mapping | Review screen and persistence implemented; actual bindings intentionally empty | Team selects and approves exact edition-specific links |
| Dated metrics and anomalies | Implemented, filtered room views and local performance verified | Team domain acceptance |
| Room-closure simulation | Core allocation, immutable API and React comparison implemented; [103 backend / 38 frontend tests pass](m3-verification.md) | Performance and team acceptance remain pending |
| Future attendance-risk prediction | D1–D3 offline pipeline and baseline comparison implemented | D4 uncertainty/shift evaluation next; persistence, API and UI pending |
| Final end-to-end demo, report and defense | Not complete | Integrate, measure, document and rehearse |

**Latest recorded checks (2026-09-21):** 49 backend tests passed, including all 14 PostgreSQL integration tests with no skips; 28 frontend tests, build, Ruff and Python compilation passed. Browser snapshot creation/retrieval and a disposable reviewed link → room-state flow passed against real endpoints. One-day/seven-day warm API p95: 94.75/481.94 ms. See [verification](m2-verification.md) and [performance](m2-performance.md). Docker work remains deferred.

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

- [ ] **A1 · B:** Local launcher and real HTTP health/login/logout/dataset reads verified on 1 October; [evidence and teammate checklist](m1-verification.md). Independent teammate-machine/browser rehearsal remains pending.
- [x] **A2 · B:** Original eight database tests plus six snapshot/mapping integration tests passed in isolated schemas in `college_twin_test`; see the verification record.
- [ ] **A3 · A:** Walk through all four detailed buildings with the team; record confirmed facts versus approximations, including the ECE allocation question above.
- [ ] **A4 · A:** Confirm CSE ground-floor rooms, separate ECE interiors, lab partitions, restroom sides and floor naming; correct only facts the team can verify.
- [ ] **A5 · A/B:** List the physical spaces needed for the demo and match them explicitly to room IDs in a chosen synthetic edition; do not match by label alone.
- [ ] **A6 · C:** Check that the synthetic edition has the room types and capacities needed by the demo. If it does not, create a reproducible new edition rather than altering a frozen one.
- [ ] **A7 · A/B:** Connect reviewed mappings, verify cross-edition isolation, and show “No linked dataset record” for unmapped spaces.

**Gate A:** All teammates can start the app; integration checks have evidence; the campus has a reviewed uncertainty list; at least the selected demo rooms have correct mappings.

### Phase B — M2: Dated state and conflict detection

**Lead: B · A builds the UI at the same time · C supplies examples · Target: weeks 4–5**

- [ ] **B1 · All:** Contract implemented in [m2-contract.md](m2-contract.md) and typed models; team sign-off remains pending.
- [x] **B2 · C:** Hand-calculated clean/conflicting, empty, missing-attendance, future-status and cancelled-class fixtures implemented and passing.
- [x] **B3 · B:** Dated frozen snapshots exclude observations not known at cutoff and expose rate denominators; integration and arithmetic tests pass.
- [x] **B4 · B:** All five rules implemented with positive/negative fixtures, independent-resource and three-way pair checks.
- [x] **B5 · A:** Date selection, metrics, conflicts and mapped room details implemented and tested against mocks and real endpoints.
- [x] **B6 · A/B:** Real endpoints and campus-room filtering verified with a disposable reviewed binding. Actual mappings intentionally remain unconfirmed per user instruction; use the completed review screen when ready.
- [x] **B7 · B/C:** Totals, boundaries, deduplication, missing observations and zero availability verified; scheduled use is labelled explicitly.

**Gate B:** Software behavior and local performance pass; linked campus selection and the dashboard agree in disposable fixtures. Human acceptance of domain assumptions and actual demo mappings remain intentionally open. See [M2 review handoff](m2-review.md).

### Phase C — M3: Close a room and compare the outcome

**Lead: B · Support: A/C · Target: weeks 6–7 · Requires Gate B**

**Implementation progress (2026-09-29):** Core M3 is implemented and locally verified: 103 backend tests (zero skips), 38 frontend tests, build, Ruff and compilation. Real browser creation/comparison passed against a disposable PostgreSQL schema. See [verification](m3-verification.md) for precise coverage and remaining gate items.

- [x] **C1 · B:** Pure engine accepts a saved baseline, room and closure interval, verifies integrity/eligibility and identifies affected sessions without changing inputs. Authenticated API wiring is implemented.
- [x] **C2 · B:** Deterministic reassignment respects capacity, room type, availability, and faculty/section constraints; independent fixtures pass.
- [x] **C3 · B:** Persist completed scenario results with provenance and replay protection; make unresolved sessions explicit.
- [x] **C4 · A:** Reviewed mapped-room selection, three-stage comparison and closed/destination highlighting are implemented. Browser-verified with explicit disposable F1/F2 links in the directory, floor controls, inspector and 3D cutaway. Current mapping revision is shown separately from immutable run provenance. No actual campus links are inferred or approved.
- [x] **C5 · C/B:** Pure-engine fixtures verify successful reassignment, no available room, incompatible labs, multiple displaced classes, no affected classes, and unchanged baseline inputs. Database baseline/source preservation also passes.

**Gate C:** The same input reproduces the same result. A teammate can trace each moved class and see why any class remains unresolved.

**Gate status:** Core software verified, team gate open. Local sequential scenario API performance passed on 1 October. The 11 October [browser matrix](m3-browser-acceptance.md) verifies planner scenarios, saved-result recovery, keyboard table navigation and narrow layout. Remaining browser cases, quantitative browser responsiveness and teammate acceptance remain pending.

### Phase D — M4: Future attendance-risk prediction

**Lead: C · Support: B/A · Target: weeks 6–8 · Runs alongside Phase C**

- [ ] **D1 · C/B:** Software contract and pure temporal builder implemented with 19 passing fixtures; [target, cutoff, history and label semantics](m4-contract.md). Team contract sign-off remains open. Combined M4/state/simulation checks: 84 passed on 11 October.
- [x] **D2 · C:** Extraction/purged splits and training-only preprocessing verified; default dataset yields 4,320/2,160/2,160 examples. See [evidence](m4-contract.md) and [preprocessing checks](m4-evaluation.md).
- [x] **D3 · C:** Dummy prior, current-rate rule and logistic regression evaluated; threshold selected on validation only. [Results](m4-evaluation.md): logistic test F1 0.653 versus rule 0.634, with the precision/recall trade-off documented.
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
- [ ] **E5 · B/C:** Snapshot performance measured and recorded in [m2-performance.md](m2-performance.md); scenario and prediction measurements remain for M3/M4. In-process API timing excludes network/browser rendering and true cold starts.
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
