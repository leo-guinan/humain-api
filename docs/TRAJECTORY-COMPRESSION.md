# Trajectory compression

Status: proposed control-plane pattern, v0.1

## Thesis

HumAIn should treat movement over time as the primary security signal and raw data as temporary substrate.

```text
raw events
   ↓
local pattern
   ↓
compressed trajectory capsule
   ↓
measured drift / recurrence / anomaly
   ↓
expand only when needed
   ↓
new raw events
```

The system should continuously expand, compress, compare, and re-expand. It should not accumulate an ever-growing transcript and call that memory.

## The important distinction

Trajectory is a security signal, not a cryptographic credential.

Patterns can answer:

- does this request resemble the node's prior movement?
- did the node suddenly change route, timing, scope, or retry behavior?
- is this interaction a recurrence, a novel branch, or a replay-shaped imitation?
- should the resolver demand stronger proof or human review?

Patterns cannot, by themselves, answer:

- is this key controlled by the claimed identity?
- was this capability actually issued by the authority?
- did the claimed publisher tell the truth?
- did a payment settle?

Behavioral continuity can raise or lower scrutiny. Cryptographic capability still gates disclosure and action.

## What gets compressed

Do not make the default capsule a copy of the content. Preserve pattern features:

- ordered event types;
- pointer class, not necessarily the full pointer;
- requester/audience relationship class;
- state transitions;
- timing buckets and dwell ranges;
- retry and escalation shape;
- action scope changes;
- recurrence and novelty;
- path distance from prior accepted trajectories;
- compression ratio;
- uncertainty and missingness;
- provenance hashes for expansion.

Sensitive payloads should remain outside the capsule unless a declared retention policy permits them. A capsule should be useful for comparing movement without becoming a shadow transcript.

## Capsule lifecycle

### 1. Observe

Capture the minimum event needed to establish sequence and outcome. Each event receives an ID, timestamp, type, scope class, and provenance pointer.

### 2. Compress

At a bounded window, produce a capsule containing the trajectory shape and a hash-linked reference to the source event range.

### 3. Compare

Compare the current capsule against:

- the node's recent baseline;
- the node's long-term baseline;
- the pointer's normal movement;
- known failure/replay trajectories;
- matched control trajectories.

### 4. Decide scrutiny

Possible outputs:

- `continuation` — familiar movement, no extra friction;
- `novel_branch` — unfamiliar but permitted movement;
- `drift` — significant change, require a stronger proof or confirmation;
- `replay_suspect` — repeated prior trajectory or nonce-shaped repetition;
- `coercion_suspect` — movement changes under unusual timing/scope patterns;
- `insufficient_pattern` — not enough history to infer anything.

These are risk signals, not accusations.

### 5. Expand

Expand the capsule to source events only when:

- the pattern is anomalous;
- a user disputes a decision;
- a receipt needs audit;
- a capability is being escalated;
- a human explicitly requests detail;
- the model's confidence is low.

Expansion must be bounded by pointer, time window, requester, and purpose.

### 6. Close

Write a receipt containing the capsule hash, comparison baseline, decision, evidence window, and unresolved uncertainty. Do not mutate the prior capsule when a later observation changes the interpretation; append a correction or new capsule.

## Measurements

Minimum useful measurements:

```text
compression_ratio = source_event_bytes / capsule_bytes
transition_entropy = entropy(event_type transitions)
recurrence = similarity to accepted prior trajectories
novelty = distance from baseline capsule
path_variance = distance between ordered movement paths
expansion_rate = expanded_windows / total_windows
false_friction = challenged legitimate flows / total legitimate flows
missed_drift = compromised or abnormal flows not escalated
```

The last two are the important ones. A security system that detects everything by stopping everything has achieved a very expensive form of sleep.

Every metric must carry:

- coverage window;
- baseline definition;
- minimum sample count;
- missing-data note;
- falsifier;
- outcome state.

## Security policy

Trajectory signals may:

- request a fresh signature;
- require a narrower capability;
- reduce projection detail;
- require human confirmation;
- create an audit alert;
- trigger controlled expansion.

Trajectory signals may not, alone:

- grant a capability;
- reveal private content;
- approve an external action;
- assert identity;
- assert truth;
- imply payment or settlement.

## Privacy policy

Compression is not permission to retain everything forever.

Default policy:

- retain capsule and hashes;
- retain only bounded event metadata;
- delete or encrypt raw expansion material according to a declared retention window;
- separate identity mapping from trajectory comparison where possible;
- do not use behavioral capsules to infer sensitive traits;
- give the human a way to inspect, export, and delete their capsule where applicable;
- log every expansion request and its purpose.

## Failure modes

### Cold start

No history means `insufficient_pattern`, not “trusted by default.” Use cryptographic capability and public-only projection.

### Mimicry

An attacker can imitate a familiar movement pattern. Require fresh cryptographic proof and avoid treating similarity as authorization.

### Drift mistaken for compromise

People change behavior. Measure false friction and provide a bounded recovery path rather than permanently escalating.

### Compression loss

If a capsule cannot explain why a decision was made, its compression was too aggressive. Preserve enough provenance to expand and reproduce the decision.

### Pattern collapse

If every trajectory looks the same because the event vocabulary is too coarse, the measurement is ornamental. Increase event-type resolution or report `insufficient_pattern`.

### Model contamination

Do not let the compressor silently change the observed workflow. Record first; compress afterward. Otherwise the security metric measures the instrument's influence on the subject.

## HumAIn implementation sequence

1. Define a versioned event vocabulary for `RESOLVE`, `OBSERVE`, `ATTEST`, `CONNECT`, and future `ACT`.
2. Emit append-only event records from browser, voice, and resolver clients.
3. Build deterministic capsule generation with no LLM in the measurement path.
4. Compare ordered trajectories using simple baselines first: transition features, timing buckets, and path distance.
5. Add a replay/drift evaluation fixture with known normal, novel, replay, and abnormal paths.
6. Measure false friction and missed drift before using trajectory to change access behavior.
7. Add controlled expansion and receipts.
8. Only then use trajectory as an input to adaptive capability policy.

The pattern is the memory. The raw event is the witness. The receipt is what stops the compression from becoming mythology.

## First mixed-trajectory evaluation

The synthetic fixture `mixed-normal-novel-recovery-replay.v1` evaluates four paths against one baseline:

- continuation → `continuation`;
- novel branch → `drift`;
- recovery → `continuation`;
- deliberate replay → `replay_suspect`.

Observed in the first run:

```text
false_friction_rate: 0.0
missed_drift_rate: 0.0
expectation_misses: 0
```

This is calibration evidence only. It is not a production security result. The report is generated by `scripts/evaluate_trajectory.py` and written to `reports/trajectory-evaluation.json`.

## Adversarial movement matrix

The next matrix adds payload mutation, timing shift, partial replay, mimicry, explicit drift, recovery, exact replay, and cold start. The trajectory signal and policy response remain separate:

```text
mimicry        → continuation / crypto_recheck
partial replay → continuation / crypto_recheck
novel branch   → novel_branch / review
timing shift   → novel_branch / review
drift          → drift / review
replay         → replay_suspect / reject_or_reissue
cold start     → insufficient_pattern / public_only
```

The first synthetic run produced:

```text
false_friction_rate: 0.0
missed_drift_rate: 0.0
expectation_misses: 0
```

These results calibrate the fixture only. In particular, the `mimicry` result proves why trajectory similarity cannot grant access: a familiar path still receives `crypto_recheck`. The report is written to `reports/trajectory-adversarial-evaluation.json`.
