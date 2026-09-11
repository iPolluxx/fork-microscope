# Public-release readiness review — 2026-09-10

## Verdict

The application is a credible **research beta**, with a reproducible checkout/container path and a separately hostable dashboard. It is not yet a completed public release or a universal, one-click cloud product. The repository is still private; no commit, push, registry publication, visibility change, cloud deployment or GPU run was performed in this review. Existing Claude/user work was preserved.

The product direction remains: one shared static website, independently owned compute, and a workflow from prompts to scans, exact-trace refinement, comparison and portable evidence. Its contribution is the usable workflow around Goodfire's method, not a claim to have invented the estimator or demonstrated internal causality.

## Changes made in this review

- Preserved Claude's MIT license, product brief and screenshot. Reorganized the README around installation, the real workflow, research meaning and supported scope; moved detailed method/CLI material into `docs/REFERENCE.md`.
- Added contribution instructions, a worker security policy, a bug-report template and a pull-request template.
- Put Goodfire attribution on all principal pages, including the tested upstream revision and the recorded revision when viewing evidence.
- Included the project's MIT license, third-party notice and Plotly notice in the static archive. Archive members and hashes are explicitly listed. Builds reject stale/private files or symlinked output rather than silently incorporating them.
- Excluded host Git metadata, local agent/configuration files and common credential files from Docker. Containers fetch the public pinned upstream source and verify a SHA-256 snapshot after its Git metadata is removed.
- Made an explicitly configured worker token enforce authentication even on loopback. Added external Jinja chat-template files to local model content fingerprints.
- Updated CI to verify the static package and upload that artifact. The optional image workflow checks an existing private GHCR package before pushing; it does not create a public bundled image on a fork.
- Fixed Configure navigation wrapping on a narrow phone screen.

## Evidence

- Application suite: **153 Python tests passed**, locally and in a clean Docker build.
- JavaScript suite: **10 tests passed**, locally and in the container.
- Upstream checks: **76 tests passed locally**; all **203 released data files** matched their recorded hashes and a recorded outcome curve recomputed exactly. The container runs the same checks using the Git-free pinned snapshot.
- Browser checks: Workspace, Configure, saved-run Explore and Compare loaded without JavaScript errors. All four fit a 390px viewport. Recorded attribution, blank model defaults, reference preset and disabled generation without a matching model were checked. Non-public filesystem paths returned 404. See `browser-checks.json` and the reproducible `browser-qa.cjs`.
- Gitleaks v8.30.1 (download checksum verified) reported no matches in the repository's **13 Git commits** and its directory scan. This is a detector result, not a guarantee that every possible sensitive value is recognizable.
- The existing estimator integration audit is in [math-audit.md](../consumer-readiness/math-audit.md). No sampling estimator or smoothing mathematics was changed during this review.
- No GPU acceptance test was run for this release. Earlier Muse results are historical evidence, not certification of this build across model families.

The local build, startup and static-package records are in `container-checks.json`. The downloadable static artifact is generated under ignored `dist/fork-dashboard.zip`; it contains no personal results or upstream Python/data.

## Remaining release gates and limits

1. **Resolve upstream distribution rights.** The pinned Goodfire repository (`d32fed8d4162a4888291c4b3a38b059727c85a41`) has no LICENSE. Our MIT license does not relicense it. Keep a bundled public worker/image release on hold while permissions are clarified. The static-only build excludes that code and dataset. See [THIRD-PARTY.md](../../THIRD-PARTY.md) and [GitHub's licensing guidance](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/licensing-a-repository).
2. **Commit and run remote CI before publication.** Many current application files are uncommitted. An external user cannot clone a private repository without authorization. No remote CI result is claimed for this working tree.
3. **Perform a named GPU acceptance run on the release candidate.** Verify attachment, EOS/parser behavior, a short scan, saved-trace refinement, export/import and comparison on at least the supported Muse profile. Add specific model/hardware combinations to a tested matrix as they pass; metadata eligibility alone is not a test.
4. **Provider setup is still manual.** Users obtain their own VM, storage and credentials, then connect a worker. The app does not provision or terminate cloud hardware. A separately hosted HTTPS frontend needs a tested HTTPS/tunnel/local-network connection for the chosen deployment.
5. **Public beta boundaries:** one owner/trusted team per worker, no shared-worker tenant accounts, no GGUF/Ollama/ordinary chat-API adapter, no executed token edits or activation interventions, and no automatic continuation of interrupted partial sampling.
6. **Research interpretation:** curves are estimates; candidate changes are not statistical significance claims. Answer-text matching tracks mentions rather than semantic truth. The app uses S total mixture draws per checkpoint; the upstream branch-wise collection uses S per retained candidate. Finite larger references are not ground truth, and matched-accuracy cost savings have not been established.

These limits belong in the public README and release notes. They do not erase the implemented workflow; they keep the portfolio claims testable and useful to other researchers.
