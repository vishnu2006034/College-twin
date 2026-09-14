# Jeppiaar campus spatial model

## Architectural rendering update

The viewer now includes individual framed windows, sunshades, columns, corridor rails, entrance steps, parapets, stair-access structures and illustrative roof equipment. Rooms include illustrative desks, boards, office furniture, computer workstations or Mechanical-lab equipment. These visual assets do not establish actual furniture counts or building equipment inventories.

Campus landscaping includes textured paving, asphalt and lawns, hedge-lined garden beds, palms, broadleaf trees, benches, lamps, road markings, sports courts, an irregular pond and an illustrative entrance/parking area. Textures are generated locally and deterministically; there are no external model/texture requests. Repeated facade, furniture and tree elements use instanced rendering to limit draw calls. The scene still uses demand rendering and capped pixel ratio.

Perspective, top and low camera views and a label toggle support inspection. Floor selection still hides upper levels, and department assignments and physical-space identifiers are unchanged. This is a more detailed architectural interpretation of the supplied references, not a photorealistic scan or surveyed replica. Specific materials, furnishings, roof equipment, gate and landscape details remain illustrative until photographs or measurements establish them.

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

### CSE extension

The user confirmed CSE is immediately to the right of IT, viewed from the central garden, with the same arrangement except reversed restrooms. CSE now has the same three enclosed levels and terrace, two provisional ground-floor labs, and F1–F7 / S1–S7 on its upper floors (room 3 staff, room 4 HOD). Boys' restrooms are at the left ends and girls' at the right; stairs stay inward from each. Numbering remains left to right because only the restrooms were changed. Both upper floors are labeled CSE.

Each space now carries `buildingId`. CSE's spaces have separate `cse-` IDs; existing IT/ECE IDs and bindings remain unchanged. Floor controls, scene cutaways, search results, and inspectors use the selected building. Search results include the building so duplicate room labels such as F3 remain distinguishable. CSE data bindings remain empty until verified.

### Latest department corrections

These assignments supersede the initial CSE floor allocation above:

| Building | Ground | First | Second |
| --- | --- | --- | --- |
| CSE, right of IT | CSE second-year classrooms | CSE third-year classrooms | MCA |
| Lab building, opposite CSE | Mechanical labs | CSE and MCA labs | IT and AI & DS labs |

CSE's ground-floor partitions use five classrooms, a staff room and HOD room from the existing upper-floor template; G1–G7 and these placements are provisional. Its prior ground-floor lab spaces are replaced, and upper-floor IDs remain stable.

The ECE building is opposite IT. Its boys' restroom is on the left and girls' on the right when viewed from the garden, opposite to IT. ECE's remaining room details use an explicitly provisional template. The earlier user-confirmed ECE occupancy on IT's second floor remains intact; a separate ECE building does not establish that those rooms moved.

ECE and the lab building rotate by 180 degrees so their corridors and selection cameras face the central garden. Left/right is building-local as viewed from that garden, not a fixed world axis. The lab building uses two illustrative lab zones per floor to represent the named departments; exact counts, partitions, facilities and department ordering are provisional. Lab geometry is separate from academic classroom layouts. Existing schematic building IDs `north-west` and `mechanical` are retained for these identified buildings.

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
