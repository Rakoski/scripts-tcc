# Methodological Timeline

This file documents the chronology of methodological decisions for the dataset,
preserved here for auditability under double-blind review. The anonymization
service used to host this repository does not preserve Git tags, so each marker
below corresponds to a dated tag in the source repository. The ordering reflects
the sequence in which each decision was registered relative to the data it
applies to.

| Marker (Git tag) | Date | Decision |
|---|---|---|
| `coleta-oficial-v1.5` | 2026-05-17 | Official collection of the initial 34 projects under the stable release-tag criterion (tag prior to 2026-01-01). |
| `ampliacao-v1.6-predeclarada` | 2026-05-22 | Sample expansion registered after a post-hoc power analysis on N=34; 30 additional projects predeclared before any new collection. |
| `relaxamento-v1.7-predeclarada` | 2026-05-23 | Temporal criterion relaxed to a HEAD-of-main snapshot for the 30 new projects, after an empirical tag inventory (`git ls-remote --tags`) showed the release-tag rule was infeasible for them. |
| `substituicao-v1.8-predeclarada` | 2026-05-26 | Seven of the 30 new projects replaced after a mechanical re-check flagged objective inclusion-criteria violations (Java share, NCLOC, age, contributors). Substitutes chosen by the same predeclared rule (top by stars among approved candidates). |
| `cascata-v1.9-predeclarada` | 2026-05-28 | Cascade substitution (one decentralized project replaced) after its post-collection SonarQube NCLOC fell below the floor; replaced by the next eligible candidate. |
| (final state) | 2026-05-29 | Four projects deferred for build incompatibilities (technical, not substantive). The primary analysis was closed at the effective sample of N=60 (34 first-wave + 26 second-wave). |

The second-wave collection (the 26 projects that survived the substitutions
above) was executed on the HEAD-of-main snapshot dated 2026-05-24.

All methodological decisions were registered via dated commits before the data
collection they apply to. The decision rule for the primary hypothesis was fixed
in the v1.5 protocol and left unchanged across every subsequent amendment; the
expansion and the complementary log-density analysis were declared explicitly as
post-observation additions and do not alter that pre-registered rule.