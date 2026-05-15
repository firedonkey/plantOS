Feature request: Redesign mobile sensor trend visualization.

Problem:
Current sensor trend cards use vertical block/bar visualization. The UI feels heavy and does not represent continuous sensor data naturally.

Goal:
Redesign sensor history/trend visualization to use smooth continuous line charts similar to scientific sensor monitoring dashboards.

Reference direction:
Use a clean line-trend style similar to the attached reference image:
- thin continuous line
- subtle grid
- minimal visual noise
- smooth sensor trend feeling
- premium/scientific aesthetic

Use existing multi-agent workflow:
Planner → approval → Coder → Tester → Reviewer

Planner only:
- Study current mobile chart implementation.
- Study current chart library.
- Do not implement yet.
- Create a plan only.

Desired design direction:
- continuous line chart instead of bars
- optional smoothing/filtering
- subtle grid lines
- responsive mobile layout
- preserve min/max/current values
- support:
  - temperature
  - humidity
  - soil moisture
  - future sensor types

UI goals:
- cleaner
- more premium
- more technical/scientific
- less cluttered
- easier to visually detect trends

Planner should investigate:
1. Current chart library
2. Whether current library supports line charts cleanly
3. Whether a better lightweight chart library is needed
4. Data smoothing options
5. Performance on mobile
6. Dark mode compatibility
7. Future multi-day trend support
8. Touch interaction/tooltip needs
9. Sensor polling density handling

Desired chart characteristics:
- thin line
- smooth trend
- no giant bars
- subtle axes/grid
- optional filled background very lightly
- support low-data and high-data situations
- support missing data gracefully

Do not:
- redesign unrelated screens
- change backend API
- change sensor semantics

Tester should verify:
- charts render correctly on iOS development build
- no crash with empty data
- no crash with many points
- responsive layout
- dark/light theme compatibility if present
- trend updates work with real backend data

Reviewer should block if:
- charts become visually cluttered
- mobile performance becomes poor
- unrelated onboarding/auth/backend behavior changes
- chart library is overly heavy/unmaintainable

Planner output format:
1. Current chart implementation summary
2. Recommended chart approach
3. Chart library decision
4. UI design direction
5. Data smoothing strategy
6. Files likely to change
7. Implementation steps
8. Test plan
9. Risks and assumptions
