# Third-party dependencies and notices

Reviewed 25 October 2026 for this source-only offline prototype. SYNTH_SHAI's own source is declared MIT in [LICENSE](LICENSE). Dependencies retain their own licenses.

## Runtime and test dependency set

`requirements.txt` includes the exact wheel versions and SHA-256 hashes in `requirements-lock.txt`. The lock targets CPython 3.11; it refuses source builds and accepts only wheel hashes reported by the versioned PyPI release records. Review and refresh the complete set deliberately. A version/hash lock is not a security certification.

| Component | Pinned version | Declared license | Primary evidence |
| --- | --- | --- | --- |
| cryptography | 50.0.2 | Apache-2.0 OR BSD-3-Clause | [Release metadata](https://pypi.org/pypi/cryptography/50.0.2/json), [license selection](https://github.com/pyca/cryptography/blob/50.0.2/LICENSE), [BSD terms](https://github.com/pyca/cryptography/blob/50.0.2/LICENSE.BSD), [Apache terms](https://github.com/pyca/cryptography/blob/50.0.2/LICENSE.APACHE) |
| cffi | 2.1.1 | MIT-0, except separately stated component terms | [Release metadata](https://pypi.org/pypi/cffi/2.1.1/json), [upstream license](https://github.com/python-cffi/cffi/blob/v2.1.1/LICENSE) |
| pycparser | 3.12 | BSD-3-Clause | [Versioned release metadata, including license expression and distribution hashes](https://pypi.org/pypi/pycparser/3.12/json), [upstream license](https://github.com/eliben/pycparser/blob/main/LICENSE) |

The baseline GitHub Actions run [40152624706](https://github.com/trimblemitch796-cell/SYNTH_SHAI/actions/runs/40152624706) installed cryptography 46.0.7, cffi 2.1.1 and pycparser 3.12. The former `cryptography>=43,<47` range is replaced because current PyPI advisory metadata reports issues affecting 46.0.7, including [GHSA-537c-gmf6-5ccf](https://osv.dev/vulnerability/GHSA-537c-gmf6-5ccf), [GHSA-m2h6-j472-rp4c](https://osv.dev/vulnerability/GHSA-m2h6-j472-rp4c), [GHSA-jwv3-5hgf-82ww](https://osv.dev/vulnerability/GHSA-jwv3-5hgf-82ww) and [GHSA-g6cj-pr64-35w5](https://osv.dev/vulnerability/GHSA-g6cj-pr64-35w5). Their upstream metadata identifies fixes by version 50.0.0. These are upstream library advisories; this repository uses Ed25519 and does not claim those other APIs are reachable in its offline path. No advisory is suppressed to obtain a passing result.

PyPI metadata for the three locked versions listed no active advisories when retrieved on 25 October 2026. This observation is not a completed `pip-audit` run, and new advisories may appear later. CI must install and retest this exact lock and run the configured advisory check before the release checklist records those checks as passed.

## Distribution obligations and limitations

This repository does not vendor the listed packages. When distributing an installed environment, wheel bundle, executable or container, preserve every included package's license and notice files. Cryptography wheels include native components, and cffi can include separately licensed material; the table is not a complete inventory of wheel-bundled native libraries or their notices. Review the exact release artifact, upstream wheel notices and redistribution obligations before distribution. Do not relicense dependencies under SYNTH_SHAI's MIT license.

The pycparser license expression is verified from its versioned PyPI metadata; the upstream license link points to the current source branch because a `v3.12` source tag was not available during review. Inspect the actual wheel's bundled `LICENSE` for any redistribution artifact. This document is a source inventory, not a legal opinion or proof of contribution ownership.

## CI-only tooling

These tools run in GitHub Actions and are not runtime dependencies of SYNTH_SHAI:

- Official `actions/checkout` and `actions/setup-python` revisions are pinned by commit and are [MIT licensed](https://github.com/actions/checkout/blob/11d5960a326750d5838078e36cf38b85af677262/LICENSE).
- The pinned [PyPA pip-audit action](https://github.com/pypa/gh-action-pip-audit/blob/fb241f581674a1bb995061d62504857a9ea4b69e/LICENSE) is Apache-2.0 licensed. Its own scanner environment is separate from the runtime lock and resolves the action's pip-audit requirements; the action source revision is pinned.
- [Gitleaks CLI 8.30.1](https://github.com/gitleaks/gitleaks/blob/v8.30.1/LICENSE) is MIT licensed. CI downloads the official Linux x64 release archive and verifies its pinned SHA-256 digest from the [official release asset metadata](https://api.github.com/repos/gitleaks/gitleaks/releases/tags/v8.30.1). The separately licensed commercial `gitleaks-action` is not used.

The history scan covers all fetched branch/tag history reachable by Git, not deleted remote refs, unavailable objects, private GitHub records or a proof that no sensitive material ever existed. Its findings are redacted, kept only in an ephemeral runner file and never uploaded as artifacts or copied into public comments.
