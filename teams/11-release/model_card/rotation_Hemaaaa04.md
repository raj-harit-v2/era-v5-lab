# Model card rotation review for Monitoring

The [Monitoring outline row](model_card_outline.md#sections) describes how the lab watched the training run and kept a record of it. The row assigns the section to Monitoring and marks it empty. The [Monitoring lead confirmed the outline scope](https://github.com/theschoolofai/era-v5-lab/pull/281#issuecomment-6634309335). The section has no prose to review yet.

| Claim | Evidence | Verdict |
| --- | --- | --- |
| The lab recorded summary results for the dry run. | [TSAI's dry run summary](https://github.com/theschoolofai/era-v5-lab/pull/475#issuecomment-6909031441) reports completion and summarises the loss record. | Supported. |
| The lab published step-by-step metrics from the completed dry run. | The [Infrastructure evidence review](https://github.com/theschoolofai/era-v5-lab/blob/be8de205dcd692cc746a77211fbec535b4f01db0/teams/07-infrastructure/results/rotation_therahulbhati.md#logs-in-the-repo) identifies the checked-in metrics as smoke test output. It lists the completed run logs as pending. | No evidence. |
| The lab built a dashboard to display training and validation metrics. | The [merged dashboard PR](https://github.com/theschoolofai/era-v5-lab/pull/495) contains the charts. | Supported. |
| The lab watched the dry run live on the dashboard. | The run inventory in the [Monitoring report](https://github.com/theschoolofai/era-v5-lab/blob/be8de205dcd692cc746a77211fbec535b4f01db0/teams/08-monitoring/alarms_dryrun1.md) is pending. It gives no live ingestion, lag or step coverage results. | No evidence. |
| The lab recorded alarm activity during the dry run. | The [alarm test record](https://github.com/theschoolofai/era-v5-lab/blob/be8de205dcd692cc746a77211fbec535b4f01db0/teams/08-monitoring/docs/alert_tests.md) describes tests with simulated faults. The Monitoring report's dry run alarm log is empty. | No evidence. |
| The lab saved records for individual tokens during the dry run. | The [record writer PR](https://github.com/theschoolofai/era-v5-lab/pull/494) adds the writer. The Monitoring report lists no saved records from the dry run. | No evidence. |

The section can cite the dry run summary and the merged dashboard. It needs further evidence before it describes the completed run's step-by-step metrics, live dashboard use, alarm activity or records for individual tokens.
