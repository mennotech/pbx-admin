# Release Workflow

This project uses Semantic Versioning for Git tags, GitHub releases, and container tags. Python package metadata uses the equivalent PEP 440 version.

## Version Convention

Public release identifiers use:

```text
vMAJOR.MINOR.PATCH
vMAJOR.MINOR.PATCH-alphaN
vMAJOR.MINOR.PATCH-betaN
vMAJOR.MINOR.PATCH-rcN
```

Examples:

| Release stage | Git tag | Python version | Container tag |
| --- | --- | --- | --- |
| Alpha 1 | `v1.0.0-alpha1` | `1.0.0a1` | `1.0.0-alpha1` |
| Beta 1 | `v1.0.0-beta1` | `1.0.0b1` | `1.0.0-beta1` |
| Release candidate 1 | `v1.0.0-rc1` | `1.0.0rc1` | `1.0.0-rc1` |
| Stable | `v1.0.0` | `1.0.0` | `1.0.0` |

Increment prerelease numbers without changing the target stable version. For example, `v1.0.0-alpha1` is followed by `v1.0.0-alpha2`, then `v1.0.0-beta1` when the release reaches beta quality.

Use version components as follows:

- `MAJOR`: incompatible configuration, data, deployment, or behavior changes.
- `MINOR`: backward-compatible features.
- `PATCH`: backward-compatible fixes, including security fixes where disclosure permits.
- `alphaN`: early testing; behavior and configuration may still change.
- `betaN`: feature-complete testing; fixes and compatibility work remain.
- `rcN`: release candidate; only release-blocking fixes should be added.

The leading `v` belongs only to Git tags and GitHub release names. Do not put it in `pyproject.toml` or container tags.

## Development Cycle

1. Create a focused branch from the current `main` branch.
2. Develop locally and run the narrowest useful tests with `make test`.
3. Run `make check` before pushing.
4. Open a pull request using the repository template.
5. GitHub Actions runs two independent required checks:
	- `Python tests` synchronizes locked dependencies and runs the test suite.
	- `Container build` verifies the production container builds with Docker on
	  the hosted runner.
6. Resolve review comments and merge only after required checks pass.
7. Delete the merged feature branch. The `main` branch remains releasable, but
	a merge does not automatically create a release or deploy the app.

Local development and CI intentionally use the same Make targets. Podman is
the local default; GitHub-hosted runners select Docker explicitly.

For normal feature work, use squash merging to keep `main` readable. Preserve
separate commits only when their history is independently useful.

Dependabot opens grouped weekly pull requests for uv dependencies and pinned
GitHub Actions. Review and merge those pull requests like any other change;
they do not bypass CI or create releases automatically.

## Release Automation

A release starts with a release-preparation pull request, not with a tag:

1. Update `pyproject.toml` to the PEP 440 version.
2. Run `make lock` and commit `uv.lock`.
3. Create the matching dated section in `CHANGELOG.md`.
4. Run `make release-check RELEASE_TAG=<tag>` and review the versioned image
	from `make release-build RELEASE_TAG=<tag>`.
5. Merge the release-preparation pull request after CI and review pass.
6. Create and push an annotated tag on that exact commit.

Pushing a matching `v*` tag starts `.github/workflows/release.yml`. The workflow:

1. verifies that the tag is annotated and its commit is contained in `main`;
2. verifies tag syntax, Python metadata, the changelog, locked dependencies,
	and tests;
3. builds the production image using the Docker-compatible Make path;
4. publishes `ghcr.io/mennotech/pbx-admin:<version>` and an immutable
	`sha-<commit>` tag;
5. publishes `latest` only for stable versions;
6. creates a GitHub prerelease for alpha, beta, and release-candidate tags, or
	a normal GitHub release for stable tags;
7. uses the matching changelog section as the release notes.

The workflow uses the repository `GITHUB_TOKEN`; no registry password or
personal access token is required. It never invokes `make deploy`.

## Prepare a Release

For `v1.0.0-alpha1`:

1. Set `project.version = "1.0.0a1"` in `pyproject.toml`.
2. Run `make lock` and commit the updated `uv.lock`.
3. Move completed entries from `Unreleased` into a dated `1.0.0-alpha1` section in `CHANGELOG.md`.
4. Update documentation and deployment examples for user-visible changes.
5. Run the release checks and build the production image:

```bash
make release-check RELEASE_TAG=v1.0.0-alpha1
make release-build RELEASE_TAG=v1.0.0-alpha1
```

`release-check` verifies tag syntax, the SemVer-to-PEP-440 mapping, the
changelog entry, locked dependencies, and tests. `release-build` also builds
the production image as `pbx-admin:1.0.0-alpha1` using the configured container
engine.

Inspect the image before tagging:

```bash
podman image inspect pbx-admin:1.0.0-alpha1
```

Docker users can set `CONTAINER_ENGINE=docker` on the `make release-build`
command and use `docker image inspect` instead.

## Tag and Publish

Start from a clean, reviewed default branch. Confirm the release commit is the commit intended for publication, then create an annotated tag:

```bash
git tag -a v1.0.0-alpha1 -m "PBX Admin v1.0.0-alpha1"
git push origin v1.0.0-alpha1
```

Create a GitHub prerelease from that tag. Use the matching `CHANGELOG.md`
section as the release notes. GitHub generates source archives for the tag;
this application does not publish a standalone Python package.

Build the container from the tagged commit and apply both an immutable release tag and, when useful, a commit-SHA tag. Do not publish prereleases as `latest`.

Deployment is a separate operator decision. Creating a release must not automatically deploy production infrastructure or mutate Fly.io secrets.

## Stable Release

When promoting a prerelease to stable:

1. Change the Python version from, for example, `1.0.0rc1` to `1.0.0`.
2. Run `make lock`.
3. Create a dated `1.0.0` changelog section containing the complete stable release notes.
4. Run `make release-check RELEASE_TAG=v1.0.0` and `make release-build RELEASE_TAG=v1.0.0`.
5. Tag and publish only after the stable artifacts pass review.

After publication, leave an empty `Unreleased` section at the top of `CHANGELOG.md` for the next development cycle.

## Correcting a Release

Do not move or overwrite a published tag. Fix the problem and publish a new version. If a release contains a severe defect or sensitive material, mark it appropriately on GitHub and follow `SECURITY.md` for coordinated handling.

## GitHub Repository Settings

Configure these settings after the workflows are committed:

- Add a branch ruleset for `main` that requires pull requests, successful
	`Python tests` and `Container build` checks, resolved conversations, and a
	linear history. Block force pushes and branch deletion.
- Require one approving review when more than one maintainer is available.
	A solo-maintainer repository may omit that requirement to avoid lockout.
- Add a tag ruleset for `v*` that restricts tag creation, updates, and deletion
	to maintainers. Published tags are immutable and must never be moved.
- Keep default workflow token permissions read-only. The release workflow
	requests only `contents: write` and `packages: write` for its job.
- Set the `ghcr.io/mennotech/pbx-admin` package visibility to public after its
	first publication, if GitHub does not inherit public visibility.
- Enable private vulnerability reporting under repository security settings.
- Enable immutable GitHub releases if that option is available for the
	repository.
- Protect any future deployment job with a GitHub Environment requiring manual
	approval. Release publication and Fly.io deployment should remain separate.
