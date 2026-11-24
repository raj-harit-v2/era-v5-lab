# Public dashboard text

One plain sentence for each panel on the public dashboard. The panel names match the public panel list from the Monitoring team. The words follow the public glossary in `glossary.md`.

| Panel | Sentence |
|---|---|
| Training Loss (Next-Token) | This panel shows the next-token loss on training text at each training step, where a lower value means better predictions on that text. |
| Training Loss (Step-Bucket Mean) | This panel shows the next-token training loss averaged over groups of consecutive training steps, so the trend is easier to see. |
| Held-Out Validation Loss | This panel shows the next-token loss on held-out text, which is set aside from training, next to the training loss. |
| Held-Out Validation Bits per Byte | This panel shows held-out loss in bits per byte of text, so readers can compare runs with different tokenizers on the same validation text. |
| Learning Rate Schedule | This panel shows how the learning rate, which helps set the size of each model update, changes from one training step to the next. |
| Tokens per Byte (All Text & by Language) | This panel shows how many tokens the tokenizer makes from each byte of text, for all text together and for each language. |
| Mixture-of-Experts Load Balance | This panel shows how evenly the model spreads tokens across its routed experts, comparing the busiest expert with the average in the least balanced layer. |
| Training Pace: Tokens per Second | This panel shows how many tokens the run processes each second. |
| Training Pace: Step Time | This panel shows how long each training step takes. |
