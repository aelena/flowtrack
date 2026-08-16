# Security

## Threat model, stated plainly

FlowTrack is designed to run **on your own machine, for one user**. It is not hardened for the open internet and nothing here should be read as a claim that it is.

Concretely:

- **Authentication is a single static API key** in the `X-API-Key` header, shared by the browser client and the Chrome extension. There are no accounts, no sessions and no roles.
- **CORS defaults to `http://localhost:7027`** and the database port is published to the host for convenience.
- **The default key in `.env.example` is `ft_dev_key_change_me`.** If you expose this beyond localhost and leave that in place, you have published your project database.

If you do put it on a network, at minimum: change `API_KEY` and `POSTGRES_PASSWORD`, stop publishing port 7029, and put it behind something that terminates TLS and authenticates.

## What has been addressed

- **Path traversal on upload.** The destination folder is resolved and checked against the storage root, and the filename runs through `basename()`.
- **Upload size.** Enforced while streaming, not after buffering the whole file, so a large upload cannot exhaust the container before being rejected.
- **Secret redaction.** Provider API keys are redacted in every API response. Editing the config round-trips the placeholder rather than overwriting the stored value.
- **Markdown rendering.** `renderMarkdown()` HTML-escapes its input before applying its own tags. This matters more than it looks: the Chrome clipper stores snippets from arbitrary web pages, and that escaping is what stands between them and stored XSS. The two `{@html}` usages carry a comment saying so — please do not "simplify" it.

## Known limitations

- No rate limiting.
- No audit log.
- The API key is compared with `!=` rather than a constant-time comparison. Irrelevant over loopback, relevant if you expose it.
- Uploaded files are served back by path from the storage volume. The traversal guards are believed correct but have not been fuzzed.

## Reporting

Open a normal issue for anything low-impact given the threat model above.

For something you would rather not post publicly, use GitHub's **private vulnerability reporting** on this repository, or email the address on [aelena.com](https://aelena.com).

No bounty, no SLA, and I will not pretend otherwise — but I will read it and credit you.
