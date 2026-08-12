# Boot Sequence Baseline

A deliberately boring cloud-side Skill used to isolate OpenHome trigger routing and Live Editor logging.

Trigger: `baseline ping`

Expected Live Editor entries:

```text
[boot-sequence-baseline] call entered
[boot-sequence-baseline] run started
[boot-sequence-baseline] run completed
[boot-sequence-baseline] resuming normal flow
```

Expected spoken response:

```text
Baseline capability reached.
```

The artifact optionally posts redacted lifecycle receipts to the HumAIn relay
using the existing `humain_rendezvous_url` and
`humain_rendezvous_auth_token` API keys. It never sends speech text or raw
exceptions. If the keys are absent, it still speaks the baseline response and
the Live Editor is the only remaining observation surface.
