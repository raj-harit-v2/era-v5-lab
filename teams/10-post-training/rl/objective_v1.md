# RL objective v1

Session 18, for the small RL run. The code is `rl/objective_v1.py`. The tests are `rl/test_objective_v1.py`.

The trainer scores each completion with `reward(env_id, output)` and passes those scores in. This objective does not call the verifier, and it does not see expected answers.

v1 has three rules.

1. Group advantage is the reward minus the group mean. It is not divided by the standard deviation.
2. A group whose rewards are all equal is dropped. It is left out of the numerator and the denominator.
3. A trust-region mask zeroes any token whose importance ratio is outside `[1 - epsilon, 1 + epsilon]`. The v1 default is `epsilon = 0.2`. The bounds are inside the region.

## Formula

One group is G completions of one prompt. `r_i` is the verifier score of completion i. `log_pi_{i,t}` is the current-policy log probability of token t. `rho_{i,t}` is the importance ratio of that token, current policy over the sampling policy.

```
A_i = r_i - mean(r)                         when the rewards are not all equal
m_{i,t} = 1 when 1 - epsilon <= rho_{i,t} <= 1 + epsilon, else 0
L = - sum(m_{i,t} * A_i * log_pi_{i,t}) / T
```

`T` is the number of tokens in kept groups. A masked token adds 0 and still counts in `T`. A dropped group does not.

A group of one completion is dropped. Its reward equals itself, so the group advantage is zero.

Minimize `L`. When `groups_kept` is 0, or no kept completion has a token, `L` is 0 and the trainer skips the step.

## Call

```python
from objective_v1 import Rollout, objective_v1

result = objective_v1([
    [
        Rollout(reward=1.0, logprobs=(-0.2, -0.4), ratios=(1.0, 1.0)),
        Rollout(reward=0.0, logprobs=(-0.1,), ratios=(1.0,)),
    ],
])
```

`result.advantages` is one tuple per kept group, in the same order as the input. `result.loss` is `L`.

Rewards are the verifier scores (0 or 1) or the effort-shaped finite scores from `rl/effort_reward.py` (`shape_reward`). Both are passed through unchanged; when effort shaping is enabled, log the raw verifier success rate beside the shaped reward. A non-finite reward, a negative ratio, or a log-probability list that differs in length from its ratio list raises `ValueError`.

## Checked by the tests

- Rewards `[0, 1]` give advantages `[-0.5, 0.5]`. Dividing by the standard deviation would give a different pair, and the test rejects that pair.
- Rewards `[1, 1, 1]` drop the group.
- A tied group next to a useful group does not change the loss.
- A ratio of `1.3` or `0.7` at `epsilon = 0.2` contributes 0. Ratios `0.8` and `1.2` stay in.
- A batch of only tied groups has loss 0.

```bash
python -m pytest teams/10-post-training/rl/test_objective_v1.py -q -p no:cacheprovider
```
