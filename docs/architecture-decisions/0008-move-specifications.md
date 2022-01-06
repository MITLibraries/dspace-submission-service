# 8. Move specifications

Date: 2021-12-09

## Status

Accepted

Supercedes [3. Submission message spec](0003-submission-message-spec.md)

Supercedes [4. Metadata json spec](0004-metadata-json-spec.md)

Supercedes [6. Submission message spec](0006-submission-message-spec.md)

Supercedes [7. Result message spec](0007-result-message-spec.md)

## Context

The message and metadata JSON specifications sometimes need to change, and having
information about those specs logged in multiple ADR files with multiple decisions over
time is confusing. Instead of recording specs in ADRs, it may be simpler to record each
spec in its own spec file for easy reference.

## Decision

We will record each specification in its own spec file in the 'docs/specifications'
folder in this repo. All previous versions of the spec will be retained
because these files will be checked into version control. The files will still only be
changed through our usual process requiring a PR and review before merging into the
main branch of the repository, and the reason for those changes will be documented in the commit message(s).

## Consequences

There will be a single place to look for the current version of each message
specification.

Changes to any of the message specifications should still be tagged for review by
maintainers of each application that submits items to DSS, so they will be informed/
approve of the changes and update those applications as needed.
