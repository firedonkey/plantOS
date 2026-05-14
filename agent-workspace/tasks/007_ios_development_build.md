Feature request: Set up native iOS development build for the PlantLab mobile app.

Problem:
The mobile app is currently being tested mainly with Expo Go. This is useful for quick UI development, but we now need a real iOS development build so we can test native capabilities, app permissions, device behavior, and move closer to a production iOS app.

Goal:
Set up the PlantLab mobile app so it can run as a native iOS development build on a real iPhone, not only inside Expo Go.

Use existing multi-agent workflow:
Planner → approval (skip the approval check this time) → Coder → Tester → Reviewer

Planner only:
- Study the current mobile app setup.
- Determine whether the app is Expo managed, Expo prebuild, or bare React Native.
- Review package.json, app.json/app.config, eas.json, iOS config if present, and current build scripts.
- Do not implement yet.
- Create a plan only.

Planner should investigate:
1. Current Expo/React Native project structure.
2. Whether expo-dev-client is needed.
3. Whether EAS Build should be used.
4. Whether local iOS builds are possible.
5. Required Apple Developer / iOS setup.
6. Required app identifiers, bundle ID, signing, provisioning profile, and development device setup.
7. Required native permissions for current and near-term app features.
8. Whether current app dependencies are compatible with a native development build.
9. Whether any current Expo Go assumptions should be removed.
10. How to keep the developer workflow simple.

Native capability validation:
- The plan should include a checklist to verify native features needed by the app.
- BLE provisioning should be included as one validation item, but this task is not only about BLE.
- Also check auth/session behavior, API environment config, camera/image features if used, secure storage if used, and general app startup/navigation.

Expected implementation direction after approval:
- Add or update development build configuration.
- Add expo-dev-client if appropriate.
- Add or update eas.json development profile.
- Add/update iOS bundle identifier.
- Add/update iOS permission descriptions.
- Add scripts or docs for building and installing the dev build.
- Add docs for running the app after installation.
- Preserve existing Expo Go workflow if useful for UI-only development.

Tester should verify:
- Typecheck passes.
- App can start in development-build workflow.
- Required config files are valid.
- Environment variables/API base URL behavior is documented.
- Native capability checklist exists.
- BLE can be tested in native build, but BLE implementation should not be redesigned in this task.

Reviewer should block if:
- The setup is still Expo Go-only.
- iOS signing/build steps are unclear.
- Bundle ID or app config is missing/ambiguous.
- Native permissions are missing for known app features.
- Production auth/backend behavior is changed unnecessarily.
- The task becomes a BLE redesign instead of native iOS app setup.

Planner output format:
1. Current mobile app setup summary
2. Why native iOS development build is needed
3. Recommended development build approach
4. Required package/config changes
5. Apple/iOS signing requirements
6. iOS permissions plan
7. Environment/API config plan
8. Native capability validation checklist
9. Build and run workflow
10. Files likely to change
11. Implementation steps
12. Test plan
13. Risks and assumptions

Stop after writing the plan.
Do not implement until I approve.