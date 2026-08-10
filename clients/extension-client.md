# Extension client contract

The BIPU browser extension is a presentation client, not a trust authority.

Request:

```http
POST /v1/resolve
Content-Type: application/json
```

The body is `humain.resolve.request.v1`. The extension supplies the public pointer, its requester identity, a nonce, and a narrowly scoped capability. It must render only the response state allowed by the resolver.

For `denied` or `unavailable`, it must not display a trusted projection. It may show the public page or a clear unavailable state. A replacement view must retain a visible original-page restoration control.
