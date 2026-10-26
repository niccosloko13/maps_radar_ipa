# Sideloadly on Windows

1. Obtain Sideloadly only from its official site and install any Apple components it requests.
2. Connect your own iPhone by USB and accept **Trust** on the iPhone.
3. Download GitHub artifact `RELAS-sideload-build-<build_number>` after the manual CI job succeeds.
4. Extract it and drag `RELAS-unsigned.ipa` into Sideloadly.
5. Enter your free Apple ID only in Sideloadly, never RELAS, Codex, CI or Git.
6. Start sideload, then complete developer trust/Developer Mode prompts on the iPhone if shown.

The current pipeline has not run, so no IPA exists to drag yet.
