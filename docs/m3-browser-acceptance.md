# M3 browser acceptance — 11 October 2026

## Scope and environment

Executed against the current local working tree using the real FastAPI/PostgreSQL API and Vite development frontend. The existing `scripts/preview_m2.py` generated one week of seed-42 synthetic data with two students per section in the random `college_twin_test` schema `preview_4285e7de29d54697bcbf0f44bd372d2e`. Backend port 8137, frontend port 5174. No application mappings were approved.

Browser: Codex in-app browser. Viewport measurements below are actual CSS dimensions read from the page; the browser's requested viewport dimensions differed from CSS dimensions. This is a functional browser pass, not a production-build performance benchmark or complete accessibility certification.

## Executed matrix

| Check | Result | Observed evidence |
| --- | --- | --- |
| Planner login | PASS | Disposable `m2-preview` account opens authenticated workspace |
| Ineligible baseline | PASS | 17:00 snapshot displays planning-cutoff guidance and no closure-create form |
| Keyboard planning cutoff and submit | PASS | Native keyboard entry of 00:00 and Enter create an eligible saved baseline |
| Unconfirmed mapping state | PASS | Zero approved mappings; reviewed-room selector disabled; synthetic-room selection available |
| Successful reassignment | PASS | ROOM-02, 5 January 09:00–10:00 IST: one affected, one reassigned, zero unresolved; assigned counts 32/31/32 and booked/available minutes 1920/5760, 1860/5700, 1920/5700 |
| No affected sessions | PASS | LAB-11, 5 January 09:00–10:00: zero affected; assigned counts remain 32; closure reduces availability to 5700 minutes |
| Multiple unresolved sessions | PASS | LAB-11, 9 January 09:00–17:00: four affected, zero reassigned, four unresolved; eight distinct affected students; assigned counts 32/28/28; booked/available minutes 1920/5760, 1680/5280, 1680/5280 |
| Unresolved explanation | PASS | Each lab row displays `no_feasible_candidate`, 10 rejected types, one closed room, one occupied room, zero feasible rooms |
| Baseline attendance presentation | PASS | Planning-cutoff attendance remains 0 present / 0 recorded and is explicitly labelled unchanged; this is UI evidence, not a new database immutability test |
| Reopen saved result | PASS | Classroom run reopens while Friday snapshot is selected; saved run retains its Monday baseline ID and original comparison |
| Invalid saved ID and recovery | PASS | `not-a-uuid` displays `Invalid request`; valid saved ID then restores comparison |
| Keyboard comparison navigation | PASS | Tab from Open saved simulation reaches Stage comparison; next Tab reaches Affected session assignments |
| Narrow layout and table scrolling | PASS at 392 CSS px | Document scroll width 384; comparison container 319 px with 720 px content; ArrowRight moves scrollLeft to 40.20 px while table region retains focus |
| Desktop document fit | PASS at 1286 CSS px | Document scroll width 1279 |
| Campus rendering | PASS, limited | Initial accessibility state reported 3D unavailable; subsequent desktop screenshot showed the rendered 3D campus. No stable WebGL failure or frame-rate conclusion inferred |

Saved fixture identifiers (for this execution only): Monday baseline `759f0966-b3cc-4387-8368-5cd1ade9b69c`, successful run `b0379635-1a7f-4138-8aa0-ea2038a809dc`; Friday baseline `c2286e8e-8b40-428b-9b63-ef878c0a0789`, unresolved run `1b344e6f-385b-406b-89bc-c20d6c10e46b`. These are disposable records, not permanent demo links.

## Limits and remaining acceptance

- NOT TESTED in this pass: viewer browser retrieval, network-failure/retry behavior, multi-page browser navigation, reviewed-map revision changes, screen-reader speech, other browser engines, cold-load timing, quantitative input latency and 3D frame rate. Earlier automated/C4 evidence remains separate in [M3 verification](m3-verification.md).
- At an exploratory 196 CSS-pixel viewport the page overflowed by 16 px. The supported-width check above was 392 px; no claim is made for 196 px.
- Browser automation's direct fill for native date/time controls did not reliably commit React state. Native keyboard events committed values and were used for the successful scenarios. This alone does not establish a product defect.
- Initial Vite launch required approved execution outside the sandbox because esbuild failed with EPERM. Port 8001 was occupied; that process was left alone and the fixture moved to 8137.
- Cleanup verified: both owned preview processes stopped, the browser viewport override was reset and test tab closed. The failed first preview schema was already absent; the second schema required explicit removal after process interruption and was removed from `college_twin_test`.
- Team review, actual room-link approval and independent teammate-machine acceptance remain open. This report advances the M3 browser gate but does not close the full gate.

## Reproduce

From the repository root, after local dependencies and the dedicated test database are configured, start separate terminals:

```powershell
.\.venv\Scripts\python.exe scripts/preview_m2.py --port 8137 --origin http://localhost:5174
```

```powershell
$env:TWIN_API_TARGET='http://127.0.0.1:8137'
npm.cmd run dev --prefix frontend -- --port 5174
```

Open `http://localhost:5174`, use the disposable credentials documented in `preview_m2.py`, and repeat the matrix. Stop both owned processes with Ctrl+C; the preview script removes its random schema in `finally`. Keep real campus mappings unconfirmed.
