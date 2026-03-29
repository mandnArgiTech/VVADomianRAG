# Multicast & streaming RFC corpus — relationships

This note ties together the RFCs in this folder for RAG retrieval. It is **not** a normative spec.

## IGMP / IPv4 group membership (obsolescence chain)

| Generation | Document | Role |
|------------|----------|------|
| Host multicast + IGMPv1 | RFC 1112 | Host extensions; first IGMP between host and router |
| IGMPv2 | RFC 2236 | Faster leave; general and group-specific queries (**updated** by RFC 9776) |
| IGMPv3 | RFC 3376 | Source filtering (include/exclude sources) — **obsolete**; retained for historical reference only |
| IGMPv3 (current) | **RFC 9776** | Revised IGMPv3; **obsoletes RFC 3376**; backward compatible with 3376; **updates RFC 2236** |

**Authoritative IGMPv3 text:** use **RFC 9776**, not RFC 3376, for new implementations.

## IPv6 symmetry — MLD

| IPv4 | IPv6 | Role |
|------|------|------|
| IGMPv2 / RFC 2236 | MLDv1 / **RFC 2710** | Basic listener reporting |
| IGMPv3 / RFC 9776 | MLDv2 / **RFC 3810** | Source filtering (SSM / ASM with filters) |

RFC 4604, RFC 5790, and RFC 9279 define behavior **jointly** for IGMPv3 and MLDv2 where noted.

## Source-specific multicast (SSM)

| Layer | Document |
|-------|----------|
| Service model & address allocation | **RFC 4607** |
| IGMPv3 / MLDv2 host–router behavior for SSM | RFC 4604 (**updates** IGMPv3 and MLDv2 specs) |
| Lightweight IGMPv3 / MLDv2 (simplified state) | RFC 5790 |
| TLV extensions on IGMPv3 / MLDv2 messages | RFC 9279 |

## Multicast routing (infrastructure)

- **RFC 7761** — PIM-SM (revised): sparse-mode multicast routing; RP trees, optional SPT switchover, registers. Complements last-hop **IGMP/MLD** (membership) with inter-router forwarding.

## Application streaming & transports (HTTP unicast)

These are **not** IP multicast delivery; they are the common Internet live/VOD stack:

- **RFC 8216** — HTTP Live Streaming (HLS): playlists, segments, encryption tags (Informational).
- **RFC 9110** — HTTP semantics (methods, caching, origins).
- **RFC 9293** — TCP (often under HTTPS for HLS).

## Layered picture

```text
Application:  HLS (RFC 8216)
Session/HTTP: HTTP (RFC 9110)
Transport:    TCP (RFC 9293)
Routing:      PIM-SM (RFC 7761)
Membership:   IGMPv3 (RFC 9776)  |  MLDv2 (RFC 3810)  ;  MLDv1 (RFC 2710) with older stacks
Extensions:   SSM framework (RFC 4607) ; SSM on GMP (RFC 4604) ; LW-GMP (RFC 5790) ; TLV ext (RFC 9279)
```

## Corpus note

RFC **3376** remains in this directory for diff/history; **RFC 9776** is the current IGMPv3 standard.
