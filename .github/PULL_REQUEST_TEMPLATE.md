## Summary

Describe the problem and the focused solution.

## Related Issue

Link the issue or explain why one is not needed.

## Validation

List the commands run and their results. Include screenshots for visible UI changes.

```text
make check
make build
```

## Security and Deployment Impact

Describe effects on authentication, authorization, proxy behavior, database compatibility, environment configuration, or deployment. Write "None" when not applicable.

## Checklist

- [ ] The change is focused and follows the repository conventions in `AGENTS.md`.
- [ ] Tests cover new or changed behavior.
- [ ] `make check` passes, or unavailable checks are explained above.
- [ ] Documentation and deployment examples are updated where needed.
- [ ] No secrets, credentials, private hosts, user mappings, or production data are included.
- [ ] Dependency changes include an updated `uv.lock`.
