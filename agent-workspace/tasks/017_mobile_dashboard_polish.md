Feature request: Mobile dashboard polish and premium UX refinement.

Context:
BLE provisioning is working.
Camera upload/display is working.
GCP deployment is mostly working.
The core product flow now exists.

Goal:
Polish the PlantLab mobile dashboard so it feels cleaner, more premium, more scientific, and more product-ready.

This task is focused on UX/UI refinement, information clarity, visual consistency, and interaction polish.
Do not redesign backend architecture unless necessary.

Use workflow:
Planner → approval → Coder → Tester → Reviewer → Release Agent

Planner only:
- Study current mobile dashboard screens.
- Study current sensor cards, image cards, trend charts, device list, and settings UI.
- Study current design consistency.
- Do not implement yet.
- Create a plan only.

Primary UX goals:
- cleaner
- calmer
- more premium
- more scientific
- less cluttered
- more “smart device dashboard”
- smoother onboarding-to-dashboard transition
- stronger visual hierarchy
- better empty/loading/error states

Planner should review:

1. Dashboard layout
- information density
- spacing/padding consistency
- card hierarchy
- typography consistency
- section grouping
- scroll behavior
- responsiveness on smaller iPhones

2. Sensor visualization
- line chart redesign direction
- trend readability
- current/min/max presentation
- sensor card hierarchy
- scientific feel instead of blocky/bar-chart feel

3. Image experience
- latest image presentation
- image gallery feel
- image loading placeholders
- image failure fallback
- timestamp readability
- camera freshness indicators

4. Device status UX
- online/offline state
- heartbeat freshness
- syncing/upload indicators
- provisioning status
- clearer device health visibility

5. Navigation polish
- tab consistency
- header consistency
- transition smoothness
- loading state consistency
- error state consistency

6. Empty/loading/error states
- graceful loading skeletons
- no giant blank screens
- clear retry behavior
- useful but minimal error copy

7. Design system consistency
- color palette consistency
- chart style consistency
- button consistency
- spacing/radius consistency
- icon consistency
- dark mode readiness if appropriate

8. Mobile performance
- avoid heavy chart rendering
- avoid unnecessary rerenders
- smooth scrolling
- image memory handling

9. Product polish opportunities
Planner should identify:
- areas that still feel prototype-like
- UI friction
- confusing flows
- inconsistent visual language
- areas where “PlantLab personality” can appear subtly

Desired visual direction:
- clean
- minimal
- calm
- premium hardware companion app
- subtle sci-fi / scientific aesthetic
- modern Apple/HomeKit-like simplicity
- avoid overly colorful or gamer-like UI

Do NOT:
- redesign auth
- redesign provisioning architecture
- redesign backend APIs unnecessarily
- add giant feature scope creep
- add unnecessary animations

Tester should verify:
- dashboard renders correctly on iOS development build
- charts render correctly
- image loading works
- empty states do not crash
- no white screens
- navigation still works
- dark/light appearance does not break UI if supported
- performance remains smooth

Reviewer should block if:
- UI becomes visually cluttered
- unrelated backend/auth/provisioning behavior changes
- performance significantly worsens
- too many inconsistent styles are introduced
- implementation creates hard-to-maintain UI complexity

Release Agent should verify:
- mobile build still succeeds
- typecheck passes
- no accidental debug UI remains
- app icon/splash still valid
- no secrets/debug logs visible in production UI

Planner output format:
1. Current dashboard UX summary
2. Main UX/design problems
3. Recommended visual direction
4. Dashboard layout improvements
5. Sensor chart improvements
6. Image/gallery improvements
7. Device status improvements
8. Navigation/loading/error polish
9. Design system consistency recommendations
10. Performance considerations
11. Files likely to change
12. Implementation phases
13. Test plan
14. Risks and assumptions
