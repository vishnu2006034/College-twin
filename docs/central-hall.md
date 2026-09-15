# Central hall layout

The two user sketches combine into one first floor: auditorium at the garden/front, open courtyard behind it. They are not separate floors. Ground, first and terrace are available; no second-floor room arrangement is asserted.

## First floor

- Front: a clear corridor spans both front staircases. Boys stair at left, girls stair at right. Corridor width is approximate.
- Auditorium-side left wing: stairs, boys restroom, four classrooms, then staff room.
- Auditorium: front-center, with an entrance on the right and adjoining circulation.
- Rear courtyard: three classrooms on the left, two on the right. Principal at rear-left, HOD/staff in the middle, exam cell at rear-right.
- Courtyard sketch marker 7: stairs to terrace at the upper-left of the open yard. The earlier drawing uses 7 for the auditorium; marker numbers are local to each drawing.
- HOD/staff partition order and the right washroom position remain approximate.

## Ground and geometry

Ground retains four chambers, two on each side of the central entrance passage, plus the large left chamber, rear chamber and right library. The front passage connects to the courtyard. Ground restroom assignments remain provisional.

Logical plan coordinates span 65 by 65, with +Z toward the garden. The renderer scales depth to the existing 35 m campus footprint, preserving campus placement. Dimensions, wall heights, doors, furnishings and descriptive labels are illustrative. No synthetic records are bound to physical rooms.

Edit hallSpaces in frontend/src/campus.ts for room rectangles and assignments. HallBuilding.tsx defines wing slabs and corridors; CampusExplorer.tsx renders the matching selectable plan. Existing courtyard classroom and stair IDs retain their historical prefixes despite the corrected first-floor assignment. Duplicate office IDs from the superseded second-floor interpretation were removed; the original first-floor office IDs remain.
