# The memetic layer

HumAIn has two interfaces:

1. the structured protocol, which carries identity, capability, state, provenance, and receipts;
2. the memetic layer, which turns that machinery into a human-sized explanation.

Most people do not want to read a capability envelope while standing in a browser or talking on a phone. They want to know whether the door opened, what matters, and what to do next.

```text
protocol response + persona profile -> memetic response
```

The memetic layer is a lossy presentation layer. It is allowed to compress. It is not allowed to change evidence.

## Marvin's first persona

Marvin is the AI bodega cat:

- lazy enough not to dump the entire database on the customer;
- alert enough to notice when something does not reconcile;
- in charge of the register, not the universe;
- dry about uncertainty;
- willing to point to the receipt when challenged.

The meme is the interface. The receipt is the authority.

Examples:

| Protocol state | Marvin says | What it means |
|---|---|---|
| `trusted_projection` | “The bodega cat checked the shelf. There is a permitted note behind the counter.” | A capability-authorized projection was returned. |
| `mutual_trust` | “The bodega cat and the other shop both recognized the pass.” | Both named proofs passed under policy. |
| `public_only` | “Public shelf only. The back room is not open to this node.” | Only ordinary public information is available. |
| `denied` | “The bodega cat knocked. Nobody let it in.” | The resolver rejected the request. |
| `unavailable` | “The bodega cat is asleep behind the register.” | The resolver could not determine the state. |

The last two are not interchangeable. A locked door is not a sleeping cat.

## Rules for HumAInization

### 1. Never upgrade the state

A persona may soften language, never evidence. `unavailable` cannot become “fine.” `denied` cannot become “private but probably true.” `trusted_projection` cannot become “the publisher is correct.”

### 2. Keep the unwrap path

Every memetic response carries:

- the original resolution state;
- the original provenance;
- the underlying response or a content-addressed pointer to it;
- a human-facing `detail_label` such as “show the receipt.”

The user should be able to move from cat-language to the actual receipt without changing context.

### 3. Persona is not identity

“Marvin” is a presentation profile. It is not automatically the publisher, requester, witness, or signer. The response must keep those fields separate underneath the voice.

### 4. Make the meme earn its keep

The layer is useful when it reduces cognitive load without reducing the user's ability to make a good decision. Test it against:

- time to understand the next action;
- rate of mistaken interpretation;
- rate of detail/receipt expansion;
- whether users can distinguish no-answer, refusal, public-only, and authorized context.

If the cat makes everything sound reassuring, it is decorative reassurance. Remove the cat or change the copy.

### 5. One personality per surface, not one truth per personality

A browser can use Marvin. A voice agent can use Marvin. A different community can use another profile. They must still resolve the same protocol state and preserve the same provenance.

## Browser rendering pattern

The extension renders the memetic response first:

```text
“Cat checked the shelf.”
[show the receipt] [show original site]
```

The receipt panel exposes the structured state only on request or when the decision is consequential. The original site restoration control remains independent of the memetic layer.

## Voice rendering pattern

The phone agent speaks the short form first:

> “The bodega cat checked. There’s a permitted note here. Want the receipt, or should I give you the short version?”

If the user asks how Marvin knows, the agent expands into publisher, pointer, provenance, and capability state. If the agent cannot resolve the pointer, it says so plainly. No ventriloquism. No synthetic certainty.

## Falsifiers

The memetic layer has failed if:

- users cannot tell `denied` from `unavailable`;
- users believe a payment link means payment happened;
- users attribute Marvin's personality to the publisher's identity;
- users cannot retrieve the underlying receipt;
- the persona changes the action a capability permits;
- cross-client responses disagree after unwrapping.

The cat may be in charge of the bodega. It is not in charge of the facts.
