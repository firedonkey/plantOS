# PlantLab Demo Launch Checklist

Use this checklist before publishing the public `/demo` page beyond internal or
preview use.

## Images

- [ ] Growth sequence uses realistic same-plant imagery.
- [ ] Latest capture is visibly different from the first capture.
- [ ] Images are approved for public marketing use.
- [ ] Image alt text is meaningful.
- [ ] No broken image requests in desktop or mobile QA.

## Copy

- [ ] Demo disclosure is visible but subtle.
- [ ] No placeholder text remains.
- [ ] Copy explains user benefits before technical details.
- [ ] Activity events read like product events, not backend logs.

## Links

- [ ] Homepage primary CTA opens `/demo`.
- [ ] Demo `Home` link opens `/`.
- [ ] Demo `Sign in` or `Dashboard` link follows the current auth state.
- [ ] Direct refresh on `/demo` works in the target hosting environment.

## Responsive QA

- [ ] Desktop viewport has no horizontal page overflow.
- [ ] Tablet viewport keeps hero and image sections readable.
- [ ] Mobile viewport keeps the growth filmstrip usable.
- [ ] CTA buttons remain reachable on mobile.

## SEO

- [ ] Page title describes the demo.
- [ ] Meta description describes growth history and device health.
- [ ] OpenGraph title and description are set.

## Future Replacement

- [ ] Replace current mockup frames with final PlantLab same-plant photos.
- [ ] Capture final images from the intended PlantLab camera angle.
- [ ] Re-check image compression before launch.
- [ ] Re-run web typecheck, build, and browser QA after asset replacement.
