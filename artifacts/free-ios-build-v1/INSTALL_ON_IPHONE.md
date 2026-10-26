# Install on your iPhone without paying

## Path A — Xcode + free Apple ID

On your own/borrowed Mac, install Xcode from Apple, generate/open `apps/ios/RelasBeta.xcodeproj`, sign in to Xcode with your free Apple ID, select the Personal Team interactively, connect your own iPhone, select it as the run destination, and Run. Do not put Apple credentials in scripts or CI. Xcode handles the development provisioning; availability/limits are Apple-controlled.

## Path B — CI build + signing available

Use the CI artifact only when you already have a valid Apple signing/provisioning setup owned by you. Configure it outside Git, then export through the supplied script. This mission does not create it.

## Path C — compiled but signing blocked

An unsigned simulator `.app`, device build or xcarchive is evidence of compilation, not installable on iPhone. Use Path A for the zero-cost practical installation route.
