# Agent client contract

An agent calls `/v1/resolve` directly. It should not use a browser or infer hidden context from DOM changes.

The agent must preserve:

- pointer;
- publisher;
- resolution state;
- provenance;
- permission scope;
- unresolved/error state.

An agent response is not evidence that the publisher claim is true. It is evidence that the resolver returned a particular signed response under a particular capability decision.
