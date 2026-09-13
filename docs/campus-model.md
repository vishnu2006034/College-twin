# Jeppiaar campus spatial model

The authenticated workspace opens an interactive campus model. Select a building in the scene or directory, select an IT/ECE floor, and select a room. Search supports labels such as F3, department names, and space functions. The existing synthetic dataset selector and inventory are under **Dataset workspace & room inventory**.

## Reference and confidence

The six user-supplied aerial screenshots guide the central gardens, paired academic blocks, courtyard complex, large hall, sports areas, paths and water. This is a schematic architectural reconstruction, not a survey, photogrammetry capture, or precise geographic model. Building heights, footprints, landscape shapes, room sizes, door placement, and stair geometry are approximate. Unidentified blocks have neutral labels; directional names describe the schematic, not verified compass bearings. Other campus interiors are not modeled.

The user identified the screenshot's EEE Block-3 as the IT/ECE building and confirmed:

| Level | Confirmed use |
| --- | --- |
| Ground | Labs; two are provisionally represented, exact count and division unconfirmed |
| First | IT: F1, F2, F5, F6, F7 classrooms; F3 staff; F4 HOD |
| Second | ECE: S1, S2, S5, S6, S7 classrooms; S3 staff; S4 HOD |
| Roof | Open terrace |

Viewed from the central garden, rooms increase left to right, starting at the girls' restroom end. Each enclosed level has the girls' restroom in the left corner and the boys' restroom in the right corner, with stairs immediately inward from each. One corridor faces the garden, with rooms behind it. Terrace access structures are illustrative.

## Editing and extension

- `frontend/src/campus.ts` owns stable building/space IDs, floor labels, room functions, reference confidence, positions, dimensions, colors, and explicit optional dataset bindings. Keep IDs unchanged when correcting display labels.
- Coordinates use +Y up. At the detailed block, +Z faces the garden and +X runs from girls to boys. Building coordinates are campus-relative; space X coordinates are building-relative. Units are approximate meters.
- `frontend/src/CampusScene.tsx` constructs native geometry, facade details, landscaping, cameras, and floor cutaways. The current architectural shell is 84 × 15 units with 4-unit levels; structural edits must keep shell slabs, room widths, end facilities, and roof in agreement. Editable room partitions live in the space configuration. No external texture or model download is required at runtime.
- `frontend/src/CampusExplorer.tsx` owns selection, search, floor controls, fallback, and detail panels. Selection is local to the current session. Switching floor clears room selection; reset returns to the campus and clears search. Camera changes are immediate and orbit damping is disabled, including for reduced-motion users.

To connect verified synthetic records, add a `RoomBinding` with `spaceId`, `editionId`, and `roomId` to `bindings`. The array intentionally starts empty. A binding resolves only when both the edition and returned record match. Never bind by visible room code, row index, or equal room counts. HOD, staff, stairs and restrooms are physical spaces independent of the current backend classroom/lab schema. Room API pagination is fully consumed; records from a previously selected edition are not passed to the inspector.

No backend endpoint or database migration is introduced. Live occupancy, timetables, anomalies and simulations are not implemented by this change. Future features can attach to stable spatial identities through explicit verified bindings.

## Rendering and verification

The scene is lazy-loaded separately from the app, uses demand rendering, and caps pixel ratio at 1.5. The renderer requires React 19.2; React and React DOM are kept on that supported minor version. A missing WebGL2 context, scene initialization error, or context loss leaves the searchable directory and floor controls usable. Narrow screens use a stacked layout and horizontally scrollable room strip.

Run `npm.cmd test --prefix frontend` and `npm.cmd run build --prefix frontend`. Tests cover confirmed layouts and functions, identity uniqueness, binding isolation, search, floor/room/terrace/reset navigation, WebGL fallback, login behavior, empty datasets, and room API failure. Browser QA uses a temporary isolated component preview without backend records; this does not replace an authenticated full-stack smoke test.

The production 3D chunk is larger than Vite's default 500 kB advisory threshold; it is loaded only when rendering is supported and the authenticated campus workspace is opened. Performance on the final presentation device should be checked before a live demo.
