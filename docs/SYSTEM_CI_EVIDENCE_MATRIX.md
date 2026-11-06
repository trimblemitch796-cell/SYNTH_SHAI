# Full-system GitHub evidence pipeline

The workflow .github/workflows/system-coverage.yml runs on pushes to main/review branches, pull requests, and manual workflow dispatch. It uses read-only GitHub Actions credentials and SHA-pinned actions. This is full *CI coverage* of available project modules, not unrestricted GitHub account access.

Jobs provide:
1. A machine-readable source inventory, including an explicit dedicated-AI-SHM absence warning when no known implementation path exists.
2. Full Python unittest discovery on versions 3.11 and 3.13, including the 3.13 ResourceWarning leak guard.
3. Named offline test jobs for USHAI CATHARSIS, MANIAC simulation and monitoring, SHM-related MANIAC sensor checks, AAA Doctor and authorization boundary regressions.
4. A Linux JVM terminal SHAI build and Android debug APK build from the same source commit, with downloadable artifacts and SHA-256 checksums.
5. A fail-closed GitHub Actions job summary. Failure, cancellation or skipped required checks produce a red summary job.

The legacy release-security and Android emulator workflow checks remain independent. The summary does NOT turn their unknown result into a pass. Physical phone installation, API integration, external services, independent review, real hardware access and full filesystem/network isolation are outside this workflow.

The dedicated AI SHM system is NOT shown implemented by these test results; MANIAC tests only cover synthetic sensor/fault monitoring. No executable action, merge or live deployment is authorized. 144 HOLD remains.

This workflow is proposed on a stacked review branch based on PR #86, which itself builds upon PR #85; it is not automatically merged to main.
