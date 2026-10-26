# Sideload entitlements

| capability | classification | status |
|---|---|---|
| location when in use | REQUIRED | usage description present |
| active-navigation background location | OPTIONAL | no background entitlement enabled; physical test required |
| push notifications | NOT_COMPATIBLE_WITH_FREE_SIDELOAD | not enabled |
| associated domains | NOT_COMPATIBLE_WITH_FREE_SIDELOAD | not enabled |
| keychain groups | UNKNOWN | no explicit group; default Keychain item only |
| app groups / iCloud | NOT_COMPATIBLE_WITH_FREE_SIDELOAD | not enabled |
| Sign in with Apple | UNKNOWN | external backend/config required; not enabled |
| CarPlay | NOT_COMPATIBLE_WITH_FREE_SIDELOAD | not enabled |

No entitlement was silently removed. Sideloadly may rewrite the signing/bundle identity; app logic must not use the bundle ID as business identity.
