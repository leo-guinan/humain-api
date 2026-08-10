# Voice client contract

A voice client consumes the same structured response as the extension and agent clients.

Minimum voice behavior:

1. state the pointer being discussed;
2. distinguish public representation from trusted projection;
3. cite publisher/provenance when summarizing hidden context;
4. ask for explicit user authorization before an action;
5. create an action receipt only after an action is actually attempted;
6. never request or repeat private keys, seed phrases, or payment credentials.

The voice client is not implemented in v0. This document is the interoperability target.
